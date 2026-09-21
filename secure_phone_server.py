from pathlib import Path
import ssl

import phone_server
import audio_phone_server


CERT_DIR = Path("certs")
CERT_FILE = CERT_DIR / "totem-cert.pem"
KEY_FILE = CERT_DIR / "totem-key.pem"

_BASE_HTTP_SERVER = phone_server.ThreadingHTTPServer

# BaseHTTPRequestHandler defaults to HTTP/1.0. Over HTTPS that encourages the
# browser to create many short-lived TLS connections. The controller polls
# state and posts audio data frequently, so HTTP/1.1 connection reuse is much
# cheaper and prevents TLS handshakes from piling up.
phone_server.BaseHTTPRequestHandler.protocol_version = "HTTP/1.1"


class SecureThreadingHTTPServer(_BASE_HTTP_SERVER):
    """Threading HTTP server that enables TLS when local cert files exist."""

    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if CERT_FILE.exists() and KEY_FILE.exists():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(
                certfile=str(CERT_FILE),
                keyfile=str(KEY_FILE),
            )
            self.socket = context.wrap_socket(
                self.socket,
                server_side=True,
            )


# PhoneControlServer resolves ThreadingHTTPServer from the phone_server module
# when start() runs, so replacing it here keeps the existing API implementation.
phone_server.ThreadingHTTPServer = SecureThreadingHTTPServer


class PhoneControlServer(audio_phone_server.PhoneControlServer):
    def start(self):
        url = super().start()

        if CERT_FILE.exists() and KEY_FILE.exists():
            secure_url = url.replace("http://", "https://", 1)
            print("HTTPS enabled (HTTP/1.1 keep-alive)")
            print(f"Secure phone URL: {secure_url}")
            return secure_url

        print("HTTPS certificates not found; using HTTP.")
        print(f"Expected certificate: {CERT_FILE}")
        print(f"Expected private key: {KEY_FILE}")
        return url
