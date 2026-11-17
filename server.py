import argparse
import base64
import binascii
import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape


PAGE = Path(__file__).with_name("index.html")
LOGO = PAGE.parent / "assets" / "dharmnandan-logo.png"
SITE_URL = os.environ.get(
    "SITE_URL", "https://dcclasses.onrender.com"
).strip().rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ANALYTICS_DB = Path(
    os.environ.get("ANALYTICS_DB_PATH", str(PAGE.parent / "analytics.sqlite3"))
)
EVENT_TYPES = (
    "page_view",
    "whatsapp_click",
    "call_click",
    "cart_add",
    "order_whatsapp_click",
    "product_view",
    "product_inquiry",
)
PRODUCTS = {
    "ccc-ai": "CCC કમ્પ્યુટર કોર્સ સાથે AI",
    "tally": "Tally Accounting",
    "dtp": "DTP & Graphic Designing",
    "typing": "Special Gujarati Typing",
    "dcso": "DCSO — Digital Cyber Seva Operator",
    "kids": "Special Kids Computer Course",
    "english": "Spoken English & Communication",
    "forms": "સરકારી ફોર્મ ભરવાની મદદ",
    "certificates": "પ્રમાણપત્ર માટે ઓનલાઈન અરજી",
    "print-scan": "પ્રિન્ટિંગ અને સ્કેનિંગ",
    "digital": "અન્ય ડિજિટલ સેવાઓ",
}


ADMIN_PAGE = """<!doctype html>
<html lang="gu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>વેબસાઇટના આંકડા | ધર્મનંદન</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 28px 18px; color: #1d2142; background: #f6f7ff; font-family: "Nirmala UI", "Shruti", "Noto Sans Gujarati", sans-serif; line-height: 1.5; }
    main { width: min(100%, 1100px); margin: 0 auto; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
    h1 { margin: 0; font-size: clamp(1.5rem, 4vw, 2rem); }
    p { color: #656b86; }
    button { min-height: 42px; padding: 8px 14px; border: 0; border-radius: 10px; color: white; background: #5145e5; font: inherit; font-weight: 700; cursor: pointer; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
    .card, .table-wrap { padding: 18px; border: 1px solid #e9e6f4; border-radius: 16px; background: white; box-shadow: 0 10px 24px rgba(38,35,88,.05); }
    .card h2 { margin: 0; color: #656b86; font-size: .95rem; }
    .value { margin-top: 6px; color: #5145e5; font-size: 2rem; font-weight: 800; }
    .table-wrap { margin-top: 22px; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th, td { padding: 10px 12px; border-bottom: 1px solid #e9e6f4; white-space: nowrap; }
    th { color: #5145e5; }
    #status { min-height: 1.5em; }
    @media (max-width: 560px) { body { padding: 20px 12px; } header { align-items: flex-start; flex-direction: column; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div><h1>ધર્મનંદન — વેબસાઇટના આંકડા</h1><p>ફક્ત કુલ ગણતરી; કોઈ મુલાકાતીની ઓળખ કે cookie સંગ્રહાતી નથી.</p></div>
      <button id="refresh" type="button">આંકડા ફરી લોડ કરો</button>
    </header>
    <p id="status" role="status" aria-live="polite">આંકડા લોડ થઈ રહ્યા છે…</p>
    <section class="cards" aria-label="આજના આંકડા">
      <article class="card"><h2>આજે પેજ વ્યૂ</h2><div class="value" id="today-page_view">0</div></article>
      <article class="card"><h2>આજે WhatsApp ક્લિક</h2><div class="value" id="today-whatsapp_click">0</div></article>
      <article class="card"><h2>આજે કૉલ ક્લિક</h2><div class="value" id="today-call_click">0</div></article>
      <article class="card"><h2>આજે કાર્ટમાં ઉમેર્યું</h2><div class="value" id="today-cart_add">0</div></article>
      <article class="card"><h2>આજે WhatsApp ઓર્ડર</h2><div class="value" id="today-order_whatsapp_click">0</div></article>
      <article class="card"><h2>આજે કોર્સ/સેવા જોવાઈ</h2><div class="value" id="today-product_view">0</div></article>
      <article class="card"><h2>આજે કોર્સ/સેવા પૂછપરછ ક્લિક</h2><div class="value" id="today-product_inquiry">0</div></article>
    </section>
    <section class="cards" aria-label="કુલ આંકડા">
      <article class="card"><h2>કુલ પેજ વ્યૂ</h2><div class="value" id="total-page_view">0</div></article>
      <article class="card"><h2>કુલ WhatsApp ક્લિક</h2><div class="value" id="total-whatsapp_click">0</div></article>
      <article class="card"><h2>કુલ કૉલ ક્લિક</h2><div class="value" id="total-call_click">0</div></article>
    </section>
    <section class="table-wrap">
      <h2>છેલ્લા 14 દિવસ</h2>
      <table>
        <thead><tr><th>તારીખ</th><th>પેજ વ્યૂ</th><th>WhatsApp</th><th>કૉલ</th><th>કાર્ટમાં ઉમેર્યું</th><th>WhatsApp ઓર્ડર</th><th>કોર્સ/સેવા જોવાઈ</th><th>પૂછપરછ ક્લિક</th></tr></thead>
        <tbody id="days"></tbody>
      </table>
    </section>
    <section class="table-wrap">
      <h2>કોર્સ અને સાયબર સેવાઓમાં રસ</h2>
      <table>
        <thead><tr><th>કોર્સ/સેવા</th><th>આજના views</th><th>આજની પૂછપરછ</th><th>આજના કાર્ટ ઉમેરા</th><th>કુલ views</th><th>કુલ પૂછપરછ</th><th>કુલ કાર્ટ ઉમેરા</th></tr></thead>
        <tbody id="products"></tbody>
      </table>
    </section>
  </main>
  <script>
    const eventTypes = ["page_view", "whatsapp_click", "call_click", "cart_add", "order_whatsapp_click", "product_view", "product_inquiry"];
    const statusElement = document.getElementById("status");
    const daysElement = document.getElementById("days");
    const productsElement = document.getElementById("products");
    async function refreshAnalytics() {
      statusElement.textContent = "આંકડા લોડ થઈ રહ્યા છે…";
      try {
        const response = await fetch("/api/analytics", { cache: "no-store" });
        if (!response.ok) throw new Error("આંકડા લોડ થઈ શક્યા નથી (" + response.status + ")");
        const data = await response.json();
        eventTypes.forEach((event) => {
          document.getElementById("today-" + event).textContent = String(data.today[event] || 0);
          const totalElement = document.getElementById("total-" + event);
          if (totalElement) totalElement.textContent = String(data.totals[event] || 0);
        });
        daysElement.replaceChildren();
        data.days.forEach((day) => {
          const row = document.createElement("tr");
          [day.date, ...eventTypes.map((event) => String(day[event] || 0))].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
          });
          daysElement.appendChild(row);
        });
        productsElement.replaceChildren();
        data.products.forEach((product) => {
          const row = document.createElement("tr");
          [
            product.name,
            String(product.today_views),
            String(product.today_inquiries),
            String(product.today_cart_adds),
            String(product.views),
            String(product.inquiries),
            String(product.cart_adds)
          ].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
          });
          productsElement.appendChild(row);
        });
        statusElement.textContent = "છેલ્લે અપડેટ: " + new Date().toLocaleString("gu-IN");
      } catch (error) {
        statusElement.textContent = error.message;
      }
    }
    document.getElementById("refresh").addEventListener("click", refreshAnalytics);
    refreshAnalytics();
    window.setInterval(refreshAnalytics, 60000);
  </script>
</body>
</html>"""


def india_date():
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()


def initialize_analytics():
    ANALYTICS_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(ANALYTICS_DB)) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS analytics_events ("
            "event_date TEXT NOT NULL, event_type TEXT NOT NULL, item_id TEXT NOT NULL DEFAULT '', "
            "count INTEGER NOT NULL, PRIMARY KEY (event_date, event_type, item_id))"
        )


def record_event(event_type, item_id=""):
    event_date = india_date().isoformat()
    with sqlite3.connect(str(ANALYTICS_DB), timeout=10) as connection:
        connection.execute(
            "INSERT INTO analytics_events (event_date, event_type, item_id, count) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(event_date, event_type, item_id) DO UPDATE SET count = count + 1",
            (event_date, event_type, item_id),
        )


def get_analytics():
    today = india_date()
    first_day = today - timedelta(days=13)
    days = {
        (first_day + timedelta(days=offset)).isoformat(): {
            event_type: 0 for event_type in EVENT_TYPES
        }
        for offset in range(14)
    }
    products = {
        product_id: {
            "name": name,
            "today_views": 0,
            "today_inquiries": 0,
            "today_cart_adds": 0,
            "views": 0,
            "inquiries": 0,
            "cart_adds": 0,
        }
        for product_id, name in PRODUCTS.items()
    }
    totals = {event_type: 0 for event_type in EVENT_TYPES}
    with sqlite3.connect(str(ANALYTICS_DB), timeout=10) as connection:
        rows = connection.execute(
            "SELECT event_date, event_type, item_id, count FROM analytics_events"
        ).fetchall()

    for event_date, event_type, item_id, count in rows:
        if event_type in totals:
            totals[event_type] += count
            if event_date in days:
                days[event_date][event_type] = count
            if item_id in products:
                if event_type == "product_view":
                    products[item_id]["views"] += count
                    if event_date == today.isoformat():
                        products[item_id]["today_views"] += count
                elif event_type == "product_inquiry":
                    products[item_id]["inquiries"] += count
                    if event_date == today.isoformat():
                        products[item_id]["today_inquiries"] += count
                elif event_type == "cart_add":
                    products[item_id]["cart_adds"] += count
                    if event_date == today.isoformat():
                        products[item_id]["today_cart_adds"] += count
    return {
        "today": days[today.isoformat()],
        "totals": totals,
        "days": [
            {"date": event_date, **counts} for event_date, counts in days.items()
        ],
        "products": list(products.values()),
    }


class WebsiteHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if format == '"%s" %s %s':
            return
        sys.stderr.write((format % args) + "\n")

    def authorize_admin(self):
        if not ADMIN_PASSWORD:
            self.send_error(503, "Set ADMIN_PASSWORD to enable the analytics dashboard")
            return False

        authorization = self.headers.get("Authorization", "")
        try:
            scheme, encoded = authorization.split(" ", 1)
            if scheme.lower() != "basic":
                raise ValueError("Unsupported authorization scheme")
            credentials = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, separator, password = credentials.partition(":")
            valid_username = secrets.compare_digest(username.encode("utf-8"), b"admin")
            valid_password = secrets.compare_digest(
                password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")
            )
            if not separator or not (valid_username and valid_password):
                raise ValueError("Invalid credentials")
        except (ValueError, binascii.Error, UnicodeDecodeError):
            body = b"Admin login required."
            self.send_response(401)
            self.send_header(
                "WWW-Authenticate", 'Basic realm="Dharmnandan Analytics", charset="UTF-8"'
            )
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return False
        return True

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/health":
            body = json.dumps({"status": "ok", "service": "dharmnandan"}).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            status = 200
        elif route in ("/admin", "/api/analytics"):
            if not self.authorize_admin():
                return
            if route == "/admin":
                body = ADMIN_PAGE.encode("utf-8")
            else:
                try:
                    body = json.dumps(get_analytics()).encode("utf-8")
                except sqlite3.Error as error:
                    self.send_error(500, "Analytics data could not be read")
                    self.log_error("Could not read analytics database: %s", error)
                    return
            content_type = (
                "text/html; charset=utf-8"
                if route == "/admin"
                else "application/json; charset=utf-8"
            )
            status = 200
        elif route == "/robots.txt":
            sitemap_line = "\nSitemap: {}/sitemap.xml".format(SITE_URL) if SITE_URL else ""
            body = (
                "User-agent: *\nAllow: /\nDisallow: /admin\n{}".format(sitemap_line)
            ).encode("utf-8")
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
            try:
                record_event("page_view")
            except sqlite3.Error as error:
                self.log_error("Could not record page view: %s", error)
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

    def do_POST(self):
        if urlsplit(self.path).path != "/api/analytics":
            self.send_error(404, "Not found")
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415, "Expected application/json")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > 1024:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "Invalid analytics event")
            return

        if not isinstance(payload, dict):
            self.send_error(400, "Invalid analytics event")
            return
        event_type = payload.get("event")
        item_id = payload.get("item", "")
        product_events = ("product_view", "product_inquiry", "cart_add")
        if (
            not isinstance(event_type, str)
            or not isinstance(item_id, str)
            or event_type not in EVENT_TYPES
            or (event_type in product_events and item_id not in PRODUCTS)
            or (event_type not in product_events and item_id != "")
        ):
            self.send_error(400, "Invalid analytics event")
            return

        try:
            record_event(event_type, item_id)
        except sqlite3.Error as error:
            self.send_error(500, "Analytics event could not be recorded")
            self.log_error("Could not record analytics event: %s", error)
            return

        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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

    initialize_analytics()
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
