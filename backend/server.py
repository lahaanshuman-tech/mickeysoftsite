#!/usr/bin/env python3
"""
MickeySoftSite backend
- Serves frontend files from ../frontend
- Provides /api/* routes for register/login/orders/requests/tickets/installers
- Handles uploads via multipart POST to /upload (admin-only flag)
- Stores JSON under backend/data and uploaded installers under backend/uploads
- Binds to http://192.168.29.222:8000 (accessible on LAN)
"""

import http.server
import socketserver
import json
import os
from urllib.parse import urlparse
from pathlib import Path
from threading import Lock

PORT = int(os.environ.get("PORT", 8000))
app.run(host="0.0.0.0", port=port)
ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = (ROOT.parent / "frontend").resolve()
DATA_DIR = ROOT / "data"
UPLOADS_DIR = ROOT / "uploads"

# admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminms123"

# Thread-safe lock for reading/writing JSON files
FILE_LOCK = Lock()

# Ensure directories exist
for d in (DATA_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# Ensure JSON files exist
def init_json(name):
    p = DATA_DIR / name
    if not p.exists():
        p.write_text("[]", encoding="utf-8")


init_json("users.json")
init_json("installers.json")
init_json("orders.json")
init_json("requests.json")
init_json("tickets.json")


class Handler(http.server.SimpleHTTPRequestHandler):
    """
    Custom request handler to manage API routes and file serving.
    """

    def log_message(self, format, *args):
        # Suppress logging to keep the console clean
        pass

    def send_json(self, data, code=200):
        """Sends a JSON response with the given status code."""
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def read_json(self, filename):
        """Reads JSON data from a file with a file lock."""
        with FILE_LOCK:
            p = DATA_DIR / filename
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except:
                return []  # Return empty list on read error

    def write_json(self, filename, data):
        """Writes JSON data to a file with a file lock."""
        with FILE_LOCK:
            p = DATA_DIR / filename
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def translate_path(self, path):
        """Translates the URL path to a local filesystem path."""
        p = urlparse(path).path

        # Static file serving: Check for assets first
        if p.startswith("/assets/"):
            maybe = FRONTEND_DIR / p[1:]
            if maybe.exists():
                return str(maybe.resolve())

        # Downloads serving
        if p.startswith("/uploads/"):
            filename = Path(p[9:]).name
            maybe = UPLOADS_DIR / filename
            if maybe.exists():
                return str(maybe.resolve())

        # pages and root
        if p == "/" or p == "":
            return str((FRONTEND_DIR / "index.html").resolve())
        # remove leading slash
        if p.startswith("/"):
            p2 = p[1:]
        else:
            p2 = p
        maybe = FRONTEND_DIR / p2
        if maybe.exists():
            return str(maybe.resolve())

        # fallback to index.html for SPA-like behavior (optional: use 404.html if available)
        return str((FRONTEND_DIR / "index.html").resolve())

    def do_POST(self):
        """Handle POST requests for API routes and file uploads."""
        url = urlparse(self.path).path

        if url == "/api/register":
            return self.handle_register()
        if url == "/api/login":
            return self.handle_login()
        if url == "/api/order":
            return self.handle_order()
        if url == "/api/request":
            return self.handle_request()
        if url == "/api/tickets":
            return self.handle_create_tickets()

        if url == "/upload":
            return self.handle_upload()

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for API routes and file serving."""
        url = urlparse(self.path).path

        if url == "/api/installers":
            return self.handle_installers()
        if url == "/api/orders":
            return self.handle_orders()
        if url == "/api/requests":
            return self.handle_requests()
        if url == "/api/tickets":
            return self.handle_tickets()
        if url == "/api/users":
            return self.handle_users()

        # Serve static files and HTML pages
        f = self.translate_path(self.path)
        if os.path.isdir(f):
            # This is not a file, let the browser handle it as a directory access attempt
            # The translate_path fallback above should typically prevent this
            self.send_response(404)
            self.end_headers()
            return

        try:
            with open(f, 'rb') as file:
                self.send_response(200)
                # Determine content type based on extension
                if f.endswith(".html"):
                    self.send_header("Content-type", "text/html")
                elif f.endswith(".css"):
                    self.send_header("Content-type", "text/css")
                elif f.endswith(".js"):
                    self.send_header("Content-type", "application/javascript")
                elif f.endswith((".png", ".jpg", ".jpeg", ".gif")):
                    self.send_header("Content-type",
                                     "image/" + f.split(".")[-1])
                elif f.endswith((".exe", ".msi")):
                    self.send_header("Content-type",
                                     "application/octet-stream")
                    self.send_header(
                        "Content-Disposition",
                        f'attachment; filename="{os.path.basename(f)}"')
                else:
                    self.send_header("Content-type", self.guess_type(f))

                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def get_post_data(self):
        """Reads JSON data from the request body."""
        try:
            content_length = int(self.headers.get('content-length', 0))
            if content_length > 0:
                data = self.rfile.read(content_length)
                return json.loads(data.decode("utf-8"))
        except:
            pass
        return {}

    def handle_register(self):
        """API: /api/register (POST)"""
        data = self.get_post_data()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        name = data.get("name", "").strip()

        if not all([email, password, name]):
            return self.send_json({
                "ok": False,
                "error": "All fields required"
            },
                                  code=400)

        users = self.read_json("users.json")
        if any(u['email'] == email for u in users):
            return self.send_json(
                {
                    "ok": False,
                    "error": "Email already registered"
                }, code=409)

        user = {
            "id": len(users) + 1,
            "name": name,
            "email": email,
            "password": password
        }
        users.append(user)
        self.write_json("users.json", users)
        return self.send_json({
            "ok": True,
            "message": "User registered",
            "user": {
                "name": name,
                "email": email
            }
        })

    def handle_login(self):
        """API: /api/login (POST)"""
        data = self.get_post_data()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return self.send_json({
                "ok": True,
                "admin": True,
                "message": "Admin login successful"
            })

        users = self.read_json("users.json")
        user = next((u for u in users
                     if u['email'] == email and u['password'] == password),
                    None)

        if user:
            return self.send_json({
                "ok": True,
                "admin": False,
                "message": "User login successful",
                "user": {
                    "name": user['name'],
                    "email": user['email']
                }
            })
        else:
            return self.send_json(
                {
                    "ok": False,
                    "error": "Invalid email or password"
                }, code=401)

    def handle_order(self):
        """API: /api/order (POST)"""
        data = self.get_post_data()
        email = data.get("email", "").strip()
        installer_id = data.get("installer_id")

        if not all([email, installer_id]):
            return self.send_json(
                {
                    "ok": False,
                    "error": "Email and installer ID required"
                },
                code=400)

        orders = self.read_json("orders.json")
        order = {
            "id": len(orders) + 1,
            "email": email,
            "installer_id": installer_id,
            "date": self.date_time_string()
        }
        orders.append(order)
        self.write_json("orders.json", orders)
        return self.send_json({"ok": True, "message": "Order recorded"})

    def handle_request(self):
        """API: /api/request (POST)"""
        data = self.get_post_data()
        email = data.get("email", "").strip()
        software = data.get("software", "").strip()

        if not all([email, software]):
            return self.send_json(
                {
                    "ok": False,
                    "error": "Email and software request required"
                },
                code=400)

        # 1️⃣ READ existing requests
        requests = self.read_json("requests.json")

        # 2️⃣ CREATE new request
        req = {
            "id": len(requests) + 1,
            "email": email,
            "software": software,
            "date": self.date_time_string()
        }

        # 3️⃣ APPEND
        requests.append(req)

        # 4️⃣ WRITE back to file
        self.write_json("requests.json", requests)

        return self.send_json({"ok": True, "message": "Request recorded"})

    def handle_create_tickets(self):
        if self.command == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))

            email = data.get("email")
            subject = data.get("subject") or data.get("title")
            message = data.get("message") or data.get("body")

            if not email or not subject or not message:
                return self.send_json({
                    "ok": False,
                    "error": "Missing fields"
                }, 400)

            tickets = self.read_json("tickets.json")

            ticket = {
                "id": len(tickets) + 1,
                "email": email,
                "subject": subject,
                "message": message,
                "status": "Open",
                "date": self.date_time_string()
            }

            tickets.append(ticket)
            self.write_json("tickets.json", tickets)

            return self.send_json({"ok": True, "ticket": ticket})

    def handle_installers(self):
        installers = self.read_json("installers.json")
        return self.send_json({"ok": True, "installers": installers})

    def handle_orders(self):
        """API: /api/orders (GET) - Admin only, no auth check here for simplicity"""
        orders = self.read_json("orders.json")
        return self.send_json({"ok": True, "orders": orders})

    def handle_requests(self):
        """API: /api/requests (GET) - Admin only, no auth check here for simplicity"""
        requests = self.read_json("requests.json")
        return self.send_json({"ok": True, "requests": requests})

    def handle_tickets(self):
        """API: /api/tickets (GET) - Admin only, no auth check here for simplicity"""
        tickets = self.read_json("tickets.json")
        return self.send_json({"ok": True, "tickets": tickets})

    def handle_users(self):
        """API: /api/users (GET) - Admin only, removes passwords for output"""
        users = self.read_json("users.json")
        # Remove passwords before sending to frontend
        safe_users = [{
            "id": u['id'],
            "name": u['name'],
            "email": u['email']
        } for u in users]
        return self.send_json({"ok": True, "users": safe_users})

    def handle_upload(self):
        """Handles file upload via multipart form to /upload"""
        # multipart form upload expected: fields file, name, desc, admin=true, username, password
        ctype, pdict = cgi.parse_header(self.headers.get('content-type', ''))
        if ctype != 'multipart/form-data':
            return self.send_json(
                {
                    "ok": False,
                    "error": "Expected multipart/form-data"
                },
                code=400)

        # NOTE: cgi.FieldStorage is deprecated but used here for simplicity in this environment
        form = cgi.FieldStorage(fp=self.rfile,
                                headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST'},
                                keep_blank_values=True)

        admin_flag = form.getvalue("admin")
        username = form.getvalue("username")
        password = form.getvalue("password")

        # Simple admin check
        if admin_flag != "true" or username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            return self.send_json({
                "ok": False,
                "error": "Admin required"
            },
                                  code=403)

        # --- FIX FOR TypeError: Cannot be converted to bool. ---
        filefield = form.get('file')  # Use .get to handle missing key safely

        # The fix: Check if filefield is a FieldStorage object AND if it has a filename
        # This prevents the TypeError when cgi.FieldStorage returns a weird object on failure (e.g., file too large)
        is_valid_upload = filefield and hasattr(
            filefield, 'filename') and filefield.filename

        if not is_valid_upload:
            return self.send_json(
                {
                    "ok": False,
                    "error": "File required or file too large/invalid"
                },
                code=400)
        # --------------------------------------------------------

        filename = Path(filefield.filename).name  # Sanitize filename
        save_path = UPLOADS_DIR / filename

        # Save file (write in binary mode)
        with open(save_path, "wb") as out:
            out.write(filefield.file.read())

        # Add metadata entry in installers.json
        installers = self.read_json("installers.json")
        item = {
            "id": len(installers) + 1,
            "name": form.getvalue("name") or filename,
            "filename": filename,
            "desc": form.getvalue("desc") or ""
        }
        installers.append(item)
        self.write_json("installers.json", installers)
        return self.send_json({"ok": True, "installer": item})


if __name__ == "__main__":
    os.chdir(str(ROOT))

    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving MickeySoftSite on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
