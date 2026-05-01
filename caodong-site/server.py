import http.server
import os
import socketserver

PORT = 36413
DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"caodong-site serving on http://localhost:{PORT}")
    httpd.serve_forever()
