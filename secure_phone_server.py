from pathlib import Path
import ssl
import sys

import phone_server
import controller_state_ui
import chaos_layout_patch  # noqa: F401
import text_ui_patch  # noqa: F401
import image_processing_ui
import safe_controls_patch  # noqa: F401
import intense_transition_patch  # noqa: F401
import intense_transition_router  # noqa: F401

if Path(sys.argv[0]).name == "simulator.py":
    import simulator_display_patch  # noqa: F401

CERT_DIR = Path("certs")
CERT_FILE = CERT_DIR / "totem-cert.pem"
KEY_FILE = CERT_DIR / "totem-key.pem"
_BASE_HTTP_SERVER = phone_server.ThreadingHTTPServer

# Keep the polling/audio connection alive instead of repeatedly handshaking TLS.
phone_server.BaseHTTPRequestHandler.protocol_version = "HTTP/1.1"

class SecureThreadingHTTPServer(_BASE_HTTP_SERVER):
    daemon_threads = True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if CERT_FILE.exists() and KEY_FILE.exists():
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version=ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(certfile=str(CERT_FILE),keyfile=str(KEY_FILE))
            self.socket=context.wrap_socket(self.socket,server_side=True)

phone_server.ThreadingHTTPServer=SecureThreadingHTTPServer

class PhoneControlServer(image_processing_ui.PhoneControlServer):
    def start(self):
        url=super().start()
        if CERT_FILE.exists() and KEY_FILE.exists():
            secure_url=url.replace("http://","https://",1)
            print("HTTPS enabled (performance controller)")
            print(f"Secure phone URL: {secure_url}")
            return secure_url
        print("HTTPS certificates not found; using HTTP.")
        print(f"Expected certificate: {CERT_FILE}")
        print(f"Expected private key: {KEY_FILE}")
        return url