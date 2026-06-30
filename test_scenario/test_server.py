"""
Test Scenario Server — Simulates a website that can be toggled UP/DOWN.
Used to test CloudGuard real-time health detection and alerting.

Endpoints:
  GET /           → 200 OK (UP) or 503 Service Unavailable (DOWN)
  GET /toggle     → Flips between UP ↔ DOWN, returns new state
  GET /status     → Shows current state as JSON

DELETE THIS FOLDER AFTER TESTING.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time

# Global state
IS_UP = True


class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global IS_UP

        if self.path == '/toggle':
            IS_UP = not IS_UP
            state = "UP" if IS_UP else "DOWN"
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "state": state,
                "message": f"Test website is now {state}",
                "toggled_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            }).encode())
            print(f"\n{'='*50}")
            print(f"  TOGGLED -> {state}")
            print(f"  Time: {time.strftime('%H:%M:%S')}")
            print(f"{'='*50}\n")

        elif self.path == '/status':
            state = "UP" if IS_UP else "DOWN"
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "state": state,
                "healthy": IS_UP,
                "checked_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            }).encode())

        else:
            # Main endpoint — returns 200 or 503 based on state
            if IS_UP:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <body style="font-family:Arial;text-align:center;padding:50px;background:#f0fdf4;">
                    <h1 style="color:#10b981;">Test Website is UP</h1>
                    <p>This is a test website for CloudGuard health check testing.</p>
                    <p><a href="/toggle">Click to toggle DOWN</a></p>
                    <p><a href="/status">Check status</a></p>
                </body>
                </html>
                """)
            else:
                self.send_response(503)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <body style="font-family:Arial;text-align:center;padding:50px;background:#fef2f2;">
                    <h1 style="color:#ef4444;">503 Service Unavailable</h1>
                    <p>This website is currently DOWN (simulated outage).</p>
                    <p><a href="/toggle">Click to toggle UP</a></p>
                    <p><a href="/status">Check status</a></p>
                </body>
                </html>
                """)

    def log_message(self, format, *args):
        # Suppress noisy logs, only print toggles
        pass


if __name__ == '__main__':
    PORT = 8888
    server = HTTPServer(('0.0.0.0', PORT), TestHandler)
    print("=" * 50)
    print("  CloudGuard Test Scenario Server")
    print(f"  Running on http://10.238.46.116:{PORT}")
    print("")
    print("  GET /         -> Website (200 or 503)")
    print("  GET /toggle   -> Flip UP / DOWN")
    print("  GET /status   -> Current state JSON")
    print("")
    print("  Current state: UP")
    print("=" * 50)
    server.serve_forever()
