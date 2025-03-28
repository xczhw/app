# server8002.py
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from port 8002")

HTTPServer(('0.0.0.0', 8002), Handler).serve_forever()
