"""Sobe o viewer 3D dos modelos em http://127.0.0.1:8765"""
import functools, http.server, os, socketserver, webbrowser
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", "apk", "_extracted", "out"))
PORT = 8765
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), H) as s:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"servindo {ROOT}\n -> {url}\nCtrl+C para parar")
    webbrowser.open(url)
    s.serve_forever()
