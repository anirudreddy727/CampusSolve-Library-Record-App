"""Local browser interface for CampusSolve, built with Python's standard library."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import tempfile
import webbrowser
from http.cookies import SimpleCookie

from storage import Storage
from library import Library
from reports import render, summary, export_reports
from importer import import_csv
from auth import AuthManager, AuthError

WEB_DIR = Path(__file__).parent / "web"


def make_handler(library):
    auth = AuthManager(library.storage.directory)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send_json(self, payload, status=200, cookie=None):
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
            if cookie is not None: self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def current_user(self):
            cookie = SimpleCookie()
            try: cookie.load(self.headers.get("Cookie", ""))
            except Exception: return None, None
            morsel = cookie.get("campussolve_session")
            token = morsel.value if morsel else None
            return token, auth.get_session(token)

        def require_user(self, role=None):
            _, user = self.current_user()
            if not user:
                self.send_json({"error": "Please sign in to continue."}, 401); return None
            if role and user["role"] != role:
                self.send_json({"error": "This action requires administrator access."}, 403); return None
            return user

        def read_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 5_000_000: raise ValueError("Request is too large")
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/state":
                _, user = self.current_user()
                if not user:
                    self.send_json({"auth": {"authenticated": False, "setup_required": auth.needs_setup}}); return
                is_admin = user["role"] == "administrator"
                member_issues = library.issues if is_admin else [i for i in library.issues if i.member_id == user["member_id"]]
                member = None if is_admin else next((m for m in library.members if m.member_id == user["member_id"]), None)
                if is_admin:
                    report_data = summary(library)
                else:
                    active = [i for i in member_issues if not i.return_date]
                    returned = [i for i in member_issues if i.return_date]
                    report_data = {"book_titles": len(library.books), "book_copies": sum(b.total_copies for b in library.books),
                                   "members_by_type": {}, "active": len(active), "returned": len(returned),
                                   "overdue": sum(i.status == "Overdue" for i in active), "average_loan_days": 0,
                                   "average_overdue_fine": 0, "average_books_per_member": len(member_issues),
                                   "top_books": [], "top_members": [], "categories": {},
                                   "fines_collected": sum(i.fine_amount for i in returned),
                                   "fines_outstanding": sum(i.fine_amount for i in active)}
                self.send_json({"auth": {"authenticated": True, "user": user},
                                "books": [b.to_dict() for b in library.books],
                                "members": ([member.to_dict()] if member else [m.to_dict() for m in library.members]),
                                "issues": [i.to_dict() for i in member_issues], "summary": report_data,
                                "report": render(library) if is_admin else "Your loan history is shown in the Loans tab.",
                                "warnings": library.storage.warnings if is_admin else []})
                return
            if path == "/api/export":
                if not self.require_user("administrator"): return
                files = export_reports(library)
                self.send_json({"files": [str(p) for p in files]}); return
            if path == "/" or path == "/index.html":
                content = (WEB_DIR / "index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content))); self.end_headers(); self.wfile.write(content); return
            self.send_json({"error": "Not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                data = self.read_json()
                if path == "/api/setup":
                    if not auth.needs_setup: raise AuthError("An administrator account is already configured.")
                    user = auth.setup_admin(data.get("username", ""), data.get("password", ""))
                    token, session = auth.login(user["username"], data["password"])
                    self.send_json({"message": "Administrator account created.", "user": session}, cookie=f"campussolve_session={token}; HttpOnly; SameSite=Strict; Path=/")
                    return
                if path == "/api/register":
                    user = auth.register_member(data.get("member_id", ""), data.get("email", ""), data.get("password", ""), library.members)
                    token, session = auth.login(user["username"], data["password"])
                    self.send_json({"message": "Member account created.", "user": session}, cookie=f"campussolve_session={token}; HttpOnly; SameSite=Strict; Path=/")
                    return
                if path == "/api/login":
                    token, session = auth.login(data.get("username", ""), data.get("password", ""))
                    self.send_json({"message": "Signed in.", "user": session}, cookie=f"campussolve_session={token}; HttpOnly; SameSite=Strict; Path=/")
                    return
                if path == "/api/logout":
                    token, _ = self.current_user(); auth.logout(token)
                    self.send_json({"message": "Signed out."}, cookie="campussolve_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
                    return
                if not self.require_user(): return
                if path in {"/api/books", "/api/members", "/api/import"} and not self.require_user("administrator"): return
                user = self.current_user()[1]
                if path == "/api/books":
                    from models import Book
                    from datetime import date
                    book = Book(data["book_id"].strip().upper(), data["title"].strip(), data["author"].strip(), data["category"].strip(), data.get("isbn", "").strip(), int(data["total_copies"]), int(data["total_copies"]), date.today(), float(data.get("value", 200)))
                    library.add_book(book); result = "Book added."
                elif path == "/api/members":
                    from models import Member
                    from datetime import date
                    member = Member(data["member_id"].strip().upper(), data["name"].strip(), data["email"].strip(), data["phone"].strip(), data["member_type"], date.today())
                    library.add_member(member); result = "Member added."
                elif path == "/api/issue":
                    if user["role"] == "member" and data.get("member_id", "").strip().upper() != user["member_id"]:
                        self.send_json({"error": "Members can only borrow using their own account."}, 403); return
                    record = library.issue_book(data["book_id"].strip().upper(), data["member_id"].strip().upper()); result = f"Issued successfully. Due {record.due_date}."
                elif path == "/api/return":
                    record = next((i for i in library.issues if i.issue_id.casefold() == data["issue_id"].strip().casefold()), None)
                    if user["role"] == "member" and (not record or record.member_id != user["member_id"]):
                        self.send_json({"error": "You can only return your own loans."}, 403); return
                    record = library.return_book(data["issue_id"].strip().upper()); result = f"Returned. Fine: Rs. {record.fine_amount:.2f}."
                elif path == "/api/renew":
                    record = next((i for i in library.issues if i.issue_id.casefold() == data["issue_id"].strip().casefold()), None)
                    if user["role"] == "member" and (not record or record.member_id != user["member_id"]):
                        self.send_json({"error": "You can only renew your own loans."}, 403); return
                    record = library.renew(data["issue_id"].strip().upper()); result = f"Renewed through {record.due_date}."
                elif path == "/api/import":
                    content = data["csv"]
                    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", dir=library.storage.directory, delete=False) as tmp:
                        tmp.write(content); filename = tmp.name
                    try: imported, rejected = import_csv(library, data["kind"], filename)
                    finally: Path(filename).unlink(missing_ok=True)
                    result = f"{imported} imported, {rejected} rejected."
                else:
                    self.send_json({"error": "Not found"}, 404); return
                self.send_json({"message": result})
            except Exception as exc:
                self.send_json({"error": str(exc) or "Request could not be completed."}, 400)

        def do_PATCH(self):
            path = urlparse(self.path).path
            try:
                if not self.require_user("administrator"): return
                data = self.read_json()
                if path.startswith("/api/books/"):
                    item = library.update_book(path.rsplit("/", 1)[1], **data)
                elif path.startswith("/api/members/"):
                    item = library.update_member(path.rsplit("/", 1)[1], **data)
                else:
                    self.send_json({"error": "Not found"}, 404); return
                self.send_json({"message": "Record updated.", "record": item})
            except Exception as exc: self.send_json({"error": str(exc)}, 400)

        def do_DELETE(self):
            path = urlparse(self.path).path
            try:
                if not self.require_user("administrator"): return
                if path.startswith("/api/books/"): library.delete_book(path.rsplit("/", 1)[1])
                elif path.startswith("/api/members/"): library.delete_member(path.rsplit("/", 1)[1])
                else: self.send_json({"error": "Not found"}, 404); return
                self.send_json({"message": "Record deleted."})
            except Exception as exc: self.send_json({"error": str(exc)}, 400)

    return Handler


def launch(library=None, host="127.0.0.1", port=8765, open_browser=True):
    library = library or Library(Storage())
    server = ThreadingHTTPServer((host, port), make_handler(library))
    url = f"http://{host}:{server.server_port}"
    print(f"CampusSolve is open at {url}. Press Ctrl+C to stop the local server.")
    if open_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

