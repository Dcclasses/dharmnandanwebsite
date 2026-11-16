import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape


PAGE = Path(__file__).with_name("index.html")
LOGO = PAGE.parent / "assets" / "dharmnandan-logo.png"
SITE_URL = os.environ.get(
    "SITE_URL", "https://dcclasses.onrender.com"
).strip().rstrip("/")


class WebsiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/health":
            body = json.dumps({"status": "ok", "service": "dharmnandan"}).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            status = 200
        elif route == "/robots.txt":
            sitemap_line = "\nSitemap: {}/sitemap.xml".format(SITE_URL) if SITE_URL else ""
            body = ("User-agent: *\nAllow: /{}\n".format(sitemap_line)).encode("utf-8")
            content_type = "text/plain; charset=utf-8"
            status = 200
        elif route == "/sitemap.xml":
            if not SITE_URL.startswith("https://"):
                self.send_error(503, "Set SITE_URL to the public HTTPS domain")
                return
            page_url = escape(SITE_URL + "/")
            body = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>{}</loc></url></urlset>".format(page_url)
            ).encode("utf-8")
            content_type = "application/xml; charset=utf-8"
            status = 200
        elif route in ("/", "/index.html"):
            try:
                body = PAGE.read_bytes()
            except OSError as error:
                self.send_error(500, "Website page could not be read")
                self.log_error("Could not read %s: %s", PAGE, error)
                return
            content_type = "text/html; charset=utf-8"
            status = 200
        elif route == "/assets/dharmnandan-logo.png":
            try:
                body = LOGO.read_bytes()
            except OSError as error:
                self.send_error(500, "Website logo could not be read")
                self.log_error("Could not read %s: %s", LOGO, error)
                return
            content_type = "image/png"
            status = 200
        else:
            self.send_error(404, "Not found")
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Run the Dharmnandan website locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind to (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port to use (default: 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), WebsiteHandler)
    print("Website running at http://{}:{}".format(*server.server_address))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWebsite server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
