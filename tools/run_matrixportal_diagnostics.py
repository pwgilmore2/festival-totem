#!/usr/bin/env python3
"""Deploy a one-shot performance tour and collect its serial log on macOS.

Uses the board's existing private Wi-Fi password; never prints or stores it
on the host. No third-party Python packages or screen session are needed.
"""

import argparse
import ast
import datetime
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import struct
import sys
import termios
import time
import tty


ROOT = Path(__file__).resolve().parents[1]
PASSWORD_LINE = re.compile(r'^WIFI_PASSWORD\s*=\s*(.*)$', re.MULTILINE)


def private_program(template, deployed):
    match = PASSWORD_LINE.search(deployed)
    if match is None:
        raise ValueError("The current CIRCUITPY/code.py has no WIFI_PASSWORD; set it first")
    try:
        password = ast.literal_eval(ast.parse(match.group(1).strip(), mode="eval").body)
    except (ValueError, SyntaxError) as exc:
        raise ValueError("Existing WIFI_PASSWORD must be a quoted string") from exc
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Set WIFI_PASSWORD in CIRCUITPY/code.py to at least 8 characters")
    replacement = 'WIFI_PASSWORD = ' + repr(password)
    if not PASSWORD_LINE.search(template):
        raise ValueError("The project code.py is missing WIFI_PASSWORD")
    return PASSWORD_LINE.sub(lambda _match: replacement, template, count=1)


def checked_write(destination, content):
    with open(destination, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    if hashlib.sha256(Path(destination).read_bytes()).digest() != hashlib.sha256(content).digest():
        raise OSError("Board copy verification failed: " + str(destination))


def deploy(target):
    if not target.is_dir() or not os.path.ismount(target):
        raise ValueError("Mount CIRCUITPY first: " + str(target))
    deployed = target / "code.py"
    if not deployed.is_file():
        raise ValueError("Existing CIRCUITPY/code.py is required to preserve your private password")
    program = private_program((ROOT / "code.py").read_text(), deployed.read_text())
    module = (ROOT / "matrixportal_diagnostics.py").read_bytes()
    if shutil.disk_usage(target).free < len(program.encode()) + len(module) + 32768:
        raise ValueError("CIRCUITPY needs at least 32 KiB plus the two files")
    print("Installing diagnostic module and trigger; copying code.py last.", flush=True)
    checked_write(target / "matrixportal_diagnostics.py", module)
    checked_write(target / "totem_diagnostics.flag", b"one-shot serial diagnostic\n")
    checked_write(deployed, program.encode())  # CircuitPython auto-reloads here.
    os.sync()


def port_candidates(preferred):
    if preferred:
        return [preferred]
    return sorted(glob.glob("/dev/cu.usbmodem*"))


def open_serial(preferred_port):
    for port in port_candidates(preferred_port):
        try:
            fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            tty.setraw(fd)
            attributes = termios.tcgetattr(fd)
            attributes[4] = attributes[5] = termios.B115200
            for flag in ('CRTSCTS', 'CCTS_OFLOW', 'CRTS_IFLOW'):
                attributes[2] &= ~getattr(termios, flag, 0)
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
            # CircuitPython regards USB CDC as connected only while the host
            # asserts DTR. os.open + termios does not guarantee that state;
            # pyserial and screen assert it when they connect.
            fcntl.ioctl(fd, termios.TIOCMBIS,
                        struct.pack('I', termios.TIOCM_DTR))
            print("Reading serial from", port, '(DTR enabled)', flush=True)
            return fd
        except OSError:
            if 'fd' in locals():
                os.close(fd)
                del fd
    return None


def collect(log_path, preferred_port, timeout, initial_fd=None, idle_timeout=60):
    deadline = time.monotonic() + timeout
    fd = initial_fd
    buffer = b""
    stage_count = 0
    captured_done = False
    last_bytes_at = time.monotonic()
    last_notice_at = last_bytes_at
    with log_path.open("w", encoding="utf-8") as log:
        log.write("# MatrixPortal serial capture started; waiting for board output\n")
        log.flush()
        while time.monotonic() < deadline and not captured_done:
            idle = time.monotonic() - last_bytes_at
            if idle >= idle_timeout:
                message = "No board serial output for %d seconds; keeping partial log" % idle_timeout
                print(message, flush=True)
                log.write("# " + message + "\n")
                break
            if idle >= 15 and time.monotonic() - last_notice_at >= 15:
                print("Waiting for board serial output (%d seconds)..." % int(idle), flush=True)
                last_notice_at = time.monotonic()
            if fd is None:
                fd = open_serial(preferred_port)
                if fd is None:
                    time.sleep(.25)
                    continue
            try:
                readable, _, _ = select.select([fd], [], [], .5)
                if not readable:
                    continue
                chunk = os.read(fd, 8192)
                if not chunk:
                    raise OSError("Serial device disconnected")
                last_bytes_at = time.monotonic()
                log.write(chunk.decode("utf-8", "replace"))
                log.flush()
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                    if line.startswith("DIAG_BEGIN") or line.startswith("DIAG_ERROR"):
                        print(line, flush=True)
                    if line.startswith("DIAG_STAGE "):
                        stage_count += 1
                        try:
                            result = json.loads(line[11:])
                            print("%d: %s %s fps %s p95 %s ms" % (
                                stage_count, result["name"], result["status"],
                                result["steady"]["fps"], result["steady"]["p95_ms"]), flush=True)
                        except (ValueError, KeyError, TypeError):
                            print(line, flush=True)
                    if line.startswith("DIAG_DONE "):
                        print(line, flush=True)
                        captured_done = True
            except OSError as exc:
                print("Serial reconnect:", exc, flush=True)
                os.close(fd)
                fd = None
                buffer = b""
    if fd is not None:
        os.close(fd)
    return captured_done, stage_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="/Volumes/CIRCUITPY")
    parser.add_argument("--port", help="USB serial device, if more than one is plugged in")
    parser.add_argument("--timeout", type=int, default=900, help="Maximum collection seconds")
    parser.add_argument("--idle-timeout", type=int, default=60,
                        help="Seconds without any board serial output before stopping")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("The collector expects macOS and /dev/cu.usbmodem* serial ports")
    logs = ROOT / "diagnostics"
    logs.mkdir(exist_ok=True)
    log_path = logs / ("totem-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
    fd = open_serial(args.port)
    try:
        deploy(Path(args.target))
    except Exception:
        if fd is not None:
            os.close(fd)
        raise
    print("The full serial log is being saved to", log_path, flush=True)
    complete, count = collect(log_path, args.port, args.timeout, fd, args.idle_timeout)
    print("Saved", count, "stages to", log_path, flush=True)
    if not complete:
        print("The board did not send DIAG_DONE. Upload this partial log for diagnosis.", file=sys.stderr)
        return 1
    marker = Path(args.target) / "totem_diagnostics.flag"
    if marker.exists():
        marker.unlink()
        os.sync()
    print("Diagnostic trigger removed; the next reset starts the normal app.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
