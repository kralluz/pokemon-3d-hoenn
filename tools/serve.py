#!/usr/bin/env python3
"""
Servidor local para o viewer 3D.

O viewer usa ES modules e fetch, entao precisa de HTTP -- abrir o index.html
direto com file:// nao funciona.

Uso: python tools/serve.py [--port 8080] [--no-browser]
Depois abra http://localhost:8080/viewer/
"""

import argparse
import functools
import http.server
import os
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".json": "application/json",
        ".fbx": "application/octet-stream",
        ".glb": "model/gltf-binary",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        # so mostra erros; 200 de textura polui demais
        if args and str(args[1]).startswith(("4", "5")):
            sys.stderr.write(f"  {args[0]} -> {args[1]}\n")

    def handle_one_request(self):
        # o navegador cancela o download ao trocar de modelo depressa; sem isso
        # o servidor cospe um traceback de ConnectionAbortedError a cada troca
        try:
            super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            self.close_connection = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    handler = functools.partial(Handler, directory=ROOT)

    # threaded: um modelo puxa o .fbx e varias texturas em paralelo
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    for port in range(args.port, args.port + 20):
        try:
            httpd = Server(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    else:
        sys.exit(f"nenhuma porta livre entre {args.port} e {args.port + 19}")

    url = f"http://localhost:{port}/viewer/"
    print(f"servindo {ROOT}")
    print(f"\n  {url}\n")
    print("ctrl+c para parar")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")


if __name__ == "__main__":
    main()
