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
import subprocess
import struct
import sys
import termios
import time
import tty


ROOT = Path(__file__).resolve().parents[1]
PASSWORD_LINE = re.compile(r'^WIFI_PASSWORD\s*=\s*(.*)$', re.MULTILINE)
BOARD_MODULES = (
    "matrixportal_backend.py", "matrixportal_effects.py", "chaos_engine.py", "info_scenes.py",
    "visual_engine.py", "transition_engine.py", "matrixportal_diagnostics.py",
)


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


def changed_modules(target):
    """Stage only differing runtime modules, preserving board media and Wi-Fi."""
    changes = []
    for name in BOARD_MODULES:
        destination = target / name
        if destination.exists() and not destination.is_file():
            raise ValueError("Expected a file on CIRCUITPY: " + str(destination))
        content = (ROOT / name).read_bytes()
        if not destination.exists() or hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(content).digest():
            changes.append((destination, content))
    return changes


def deploy(target):
    if not target.is_dir() or not os.path.ismount(target):
        raise ValueError("Mount CIRCUITPY first: " + str(target))
    deployed = target / "code.py"
    if not deployed.is_file():
        raise ValueError("Existing CIRCUITPY/code.py is required to preserve your private password")
    program = private_program((ROOT / "code.py").read_text(), deployed.read_text())
    changes = changed_modules(target)
    if shutil.disk_usage(target).free < len(program.encode()) + sum(len(data) for _, data in changes) + 32768:
        raise ValueError("CIRCUITPY needs 32 KiB plus the program and changed runtime modules")
    print("Installing %d changed runtime modules and trigger; copying code.py last." % len(changes), flush=True)
    for destination, content in changes:
        print("Updating", destination.name, flush=True)
        checked_write(destination, content)
    checked_write(target / "totem_diagnostics.flag", b"one-shot serial diagnostic\n")
    checked_write(deployed, program.encode())  # CircuitPython auto-reloads here.
    os.sync()


def port_candidates(preferred):
    if preferred:
        return [preferred]
    return sorted(glob.glob("/dev/cu.usbmodem*"))


def open_serial(preferred_port, errors=None):
    candidates = port_candidates(preferred_port)
    if not candidates and errors is not None:
        errors.append("No /dev/cu.usbmodem* port was found")
    for port in candidates:
        fd = None
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
            try:
                fcntl.ioctl(fd, termios.TIOCMBIS,
                            struct.pack('I', termios.TIOCM_DTR))
                dtr_status = 'DTR enabled'
            except (OSError, AttributeError) as exc:
                # Some macOS USB drivers do not support this modem ioctl.
                # Opening a callout device may already assert DTR; verify by
                # actually reading board output before changing CIRCUITPY.
                dtr_status = 'DTR ioctl unavailable: %s' % exc
            print("Reading serial from", port, '(' + dtr_status + ')', flush=True)
            return fd
        except (OSError, AttributeError) as exc:
            if errors is not None:
                errors.append("%s: %s: %s" % (port, type(exc).__name__, exc))
            if fd is not None:
                os.close(fd)
    return None


def probe_serial(fd, seconds=15):
    """Confirm the current board actually prints before starting a new tour."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        readable, _, _ = select.select([fd], [], [], max(0, min(.5, deadline - time.monotonic())))
        if readable:
            chunk = os.read(fd, 8192)
            if not chunk:
                raise OSError("USB serial disconnected during preflight")
            return chunk
    raise TimeoutError("USB port opened, but the running board sent no console output in %s seconds" % seconds)


def port_owners(ports):
    """Return brief macOS lsof output for the port that blocked preflight."""
    executable = shutil.which('lsof') or '/usr/sbin/lsof'
    owners = []
    for port in ports:
        try:
            result = subprocess.run([executable, '-nP', port], capture_output=True,
                                    text=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        lines = result.stdout.strip().splitlines()
        if len(lines) > 1:
            owners.append(port + ':\n' + '\n'.join(lines[:5]))
    return '\n'.join(owners)


def collect(log_path, preferred_port, timeout, initial_fd=None, idle_timeout=60,
            done_hold_seconds=0):
    deadline = time.monotonic() + timeout
    fd = initial_fd
    buffer = b""
    stage_count = 0
    captured_done = False
    last_bytes_at = time.monotonic()
    last_notice_at = last_bytes_at
    last_probe_at = last_bytes_at
    probe_index = 0
    with log_path.open("w", encoding="utf-8") as log:
        log.write("# MatrixPortal serial capture started; waiting for board output\n")
        log.write("# candidate ports: %s\n" % (port_candidates(preferred_port),))
        log.write("# connected port: %s\n" %
                  (os.ttyname(fd) if fd is not None else "none",))
        log.flush()
        while time.monotonic() < deadline and not captured_done:
            idle = time.monotonic() - last_bytes_at
            if idle >= 20 and time.monotonic() - last_probe_at >= 20 and not preferred_port:
                alternatives = [port for port in port_candidates(None)
                                if fd is None or port != os.ttyname(fd)]
                if alternatives:
                    alternative = alternatives[probe_index % len(alternatives)]
                    probe_index += 1
                    last_probe_at = time.monotonic()
                    replacement = open_serial(alternative)
                    if replacement is not None:
                        if fd is not None:
                            os.close(fd)
                        fd = replacement
                        log.write("# switched to serial port: %s\n" % alternative)
                        log.flush()
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
    if captured_done and done_hold_seconds:
        print("DONE is on the panels. Keeping it visible for %d seconds." % done_hold_seconds,
              flush=True)
        time.sleep(done_hold_seconds)
    if fd is not None:
        os.close(fd)
    return captured_done, stage_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="/Volumes/CIRCUITPY")
    parser.add_argument("--port", help="USB serial device, if more than one is plugged in")
    parser.add_argument("--timeout", type=int, default=1800, help="Maximum collection seconds")
    parser.add_argument("--idle-timeout", type=int, default=60,
                        help="Seconds without any board serial output before stopping")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("The collector expects macOS and /dev/cu.usbmodem* serial ports")
    logs = ROOT / "diagnostics"
    logs.mkdir(exist_ok=True)
    log_path = logs / ("totem-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
    open_errors = []
    fd = open_serial(args.port, open_errors)
    if fd is None:
        owners = port_owners(port_candidates(args.port))
        parser.error("USB serial preflight failed before changing CIRCUITPY: "
                     + "; ".join(open_errors)
                     + ("\nPort owner:\n" + owners if owners else "")
                     + "\nClose the program holding the port. If it is screen, run "
                       "screen -ls and then screen -S <session-id> -X quit; retry.")
    try:
        print("Checking for existing board console output before deploying...", flush=True)
        probe_serial(fd)
        print("Board serial output confirmed.", flush=True)
        deploy(Path(args.target))
    except TimeoutError as exc:
        os.close(fd)
        parser.error("%s. The board was not changed. Check the selected USB port or close another serial monitor." % exc)
    except Exception:
        os.close(fd)
        raise
    print("The full serial log is being saved to", log_path, flush=True)
    complete, count = collect(log_path, args.port, args.timeout, fd,
                              args.idle_timeout, done_hold_seconds=15)
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
