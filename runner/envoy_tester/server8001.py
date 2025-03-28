# server8001.py
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from port 8001")

HTTPServer(('0.0.0.0', 8001), Handler).serve_forever()
