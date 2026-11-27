"""Small, dependency-free Household Six service for LAN deployment."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import queue
import secrets
import sqlite3
import time
import uuid
from threading import Lock
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "household.sqlite3"
COOKIE = "hs_session"
SESSION_DAYS = max(1, min(90, int(os.environ.get("SESSION_DAYS", "14"))))
KINDS = {"event", "task", "shopping", "meal", "inventory", "recipe", "announcement", "reward"}
PRIVILEGED = {"owner", "admin", "adult"}
COLORS = {"#233C32", "#78937D", "#C69A5D", "#54768C", "#9B6B72", "#7B6C9B"}
FAILED_LOGINS = {}
LOGIN_LOCK = 10 * 60


class EventHub:
    """Small process-local fanout; reconnecting clients refetch current state."""
    def __init__(self):
        self.lock = Lock()
        self.subscribers = {}

    def subscribe(self, household_id):
        channel = queue.Queue(maxsize=32)
        with self.lock:
            self.subscribers.setdefault(household_id, set()).add(channel)
        return channel

    def unsubscribe(self, household_id, channel):
        with self.lock:
            group = self.subscribers.get(household_id, set())
            group.discard(channel)
            if not group:
                self.subscribers.pop(household_id, None)

    def publish(self, household_id, event):
        encoded = json.dumps(event, separators=(",", ":"))
        with self.lock:
            targets = list(self.subscribers.get(household_id, set()))
        for channel in targets:
            if channel.full():
                try:
                    channel.get_nowait()
                except queue.Empty:
                    pass
            try:
                channel.put_nowait(encoded)
            except queue.Full:
                pass


EVENTS = EventHub()


def rate_limited(key):
    now = time.time()
    count, window_start, blocked_until = FAILED_LOGINS.get(key, (0, now, 0))
    if now - window_start >= LOGIN_LOCK:
        FAILED_LOGINS[key] = (0, now, 0)
        return False
    return blocked_until > now


def record_login_failure(keys):
    now = time.time()
    for key, threshold in keys:
        count, window_start, blocked_until = FAILED_LOGINS.get(key, (0, now, 0))
        if now - window_start >= LOGIN_LOCK:
            count, window_start = 0, now
        count += 1
        FAILED_LOGINS[key] = (count, window_start, now + LOGIN_LOCK if count >= threshold else 0)
    if len(FAILED_LOGINS) > 10_000:
        for key, (_, started, blocked) in list(FAILED_LOGINS.items()):
            if time.time() - started >= LOGIN_LOCK and blocked <= time.time():
                FAILED_LOGINS.pop(key, None)
        while len(FAILED_LOGINS) > 10_000:
            FAILED_LOGINS.pop(next(iter(FAILED_LOGINS)))


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect():
    con = sqlite3.connect(DB_PATH, timeout=10, factory=ClosingConnection)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=10000")
    return con


def migrate():
    os.umask(0o077)
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)
    with connect() as con:
        con.executescript((ROOT / "migrations/001_initial.sql").read_text())
    if DB_PATH.exists():
        os.chmod(DB_PATH, 0o600)


def new_id():
    return str(uuid.uuid4())


def pw_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt.hex() + "." + derived.hex()


def verify_password(password, encoded):
    try:
        salt_hex, want = encoded.split(".", 1)
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32).hex()
        return hmac.compare_digest(got, want)
    except (ValueError, TypeError):
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def store_csrf(con, session_id_hash, token):
    token_hash = digest(token)
    con.execute("INSERT OR IGNORE INTO csrf_tokens(session_id_hash,token_hash) VALUES(?,?)", (session_id_hash,token_hash))
    con.execute("DELETE FROM csrf_tokens WHERE session_id_hash=? AND token_hash NOT IN (SELECT token_hash FROM csrf_tokens WHERE session_id_hash=? ORDER BY created_at DESC,token_hash DESC LIMIT 16)", (session_id_hash,session_id_hash))


def valid_csrf(con, session_id_hash, token):
    token_hash = digest(token)
    return con.execute("""SELECT 1 FROM sessions s LEFT JOIN csrf_tokens c
        ON c.session_id_hash=s.id_hash AND c.token_hash=?
        WHERE s.id_hash=? AND (s.csrf_hash=? OR c.token_hash IS NOT NULL)""", (token_hash,session_id_hash,token_hash)).fetchone() is not None


def list_items(con, household_id, kind):
    return con.execute("""SELECT i.id,i.kind,i.title,i.details,i.due_at,i.assigned_to,i.completed,i.value,i.version,i.created_at,
        u.display_name assigned_name,u.color assigned_color
        FROM items i LEFT JOIN users u ON u.id=i.assigned_to AND u.household_id=i.household_id
        WHERE i.household_id=? AND i.kind=? ORDER BY i.completed,COALESCE(i.due_at,i.created_at),i.created_at DESC LIMIT 250""", (household_id, kind)).fetchall()


def complete_item(con, iid, household_id, actor_id, role):
    item = con.execute("SELECT * FROM items WHERE id=? AND household_id=?", (iid, household_id)).fetchone()
    if not item:
        return None
    if role == "display":
        raise PermissionError("This read-only display cannot change household data.")
    if item["kind"] == "task" and role == "child" and item["assigned_to"] not in (None, actor_id):
        raise PermissionError("You can only complete a task assigned to you.")
    if not item["completed"]:
        con.execute("UPDATE items SET completed=1,version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND completed=0", (iid,))
        if item["kind"] == "task" and item["value"] and item["assigned_to"]:
            con.execute("INSERT OR IGNORE INTO points_ledger(id,household_id,member_id,item_id,amount,reason) VALUES(?,?,?,?,?,'task.complete')", (new_id(),household_id,item["assigned_to"],iid,item["value"]))
        con.execute("INSERT INTO audit_log(id,household_id,actor_id,action,object_id) VALUES(?,?,?,'item.complete',?)", (new_id(),household_id,actor_id,iid))
    return con.execute("SELECT id,kind,title,details,due_at,assigned_to,completed,value,version FROM items WHERE id=?", (iid,)).fetchone()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "HouseholdSix/0.1"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Never log paths, form contents, cookies, or household data.
        print("%s - %s" % (self.log_date_time_string(), fmt.split(" ")[0]))

    def response_headers(self, content_type="application/json; charset=utf-8", cache="no-store"):
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    def json(self, status, data, extra_headers=None):
        raw = json.dumps(data, separators=(",", ":")).encode()
        self.send_response(status)
        self.response_headers()
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (ValueError, AttributeError):
            raise ValueError("Invalid request length")
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-encoded requests are not supported")
        if length < 0:
            raise ValueError("Invalid request length")
        if length > 32768:
            raise ValueError("Request is too large")
        data = self.rfile.read(length) if length else b"{}"
        value = json.loads(data or b"{}")
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    def route(self):
        return urlparse(self.path).path.rstrip("/") or "/"

    def origin_ok(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        parsed = urlparse(origin)
        return parsed.netloc == host and parsed.scheme in {"http", "https"}

    def csrf_ok(self, csrf):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        c = cookie.get(COOKIE)
        if not (c and csrf and self.session):
            return False
        with connect() as con:
            return valid_csrf(con,self.session["id_hash"],csrf)

    def auth(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        c = cookie.get(COOKIE)
        if not c:
            return None
        con = connect()
        row = con.execute("""SELECT s.id_hash,s.csrf_hash,u.id,u.household_id,u.username,u.display_name,u.role,u.color,h.name household_name,h.timezone
                            FROM sessions s JOIN users u ON u.id=s.user_id JOIN households h ON h.id=u.household_id
                            WHERE s.id_hash=? AND s.expires_at>?""", (digest(c.value), datetime.now(timezone.utc).isoformat())).fetchone()
        con.close()
        self.session = row
        return row

    def require_auth(self):
        user = self.auth()
        if not user:
            self.json(401, {"error": "Sign in to continue."})
        return user

    def do_GET(self):
        path = self.route()
        try:
            if path == "/api/health":
                return self.json(200, {"ok": True, "service": "Household Six"})
            if path == "/api/setup-state":
                with connect() as con:
                    exists = con.execute("SELECT 1 FROM households LIMIT 1").fetchone() is not None
                return self.json(200, {"initialized": exists})
            if path == "/api/me":
                user = self.auth()
                if not user:
                    return self.json(200, {"user": None})
                csrf = secrets.token_urlsafe(32)
                with connect() as con:
                    store_csrf(con,user["id_hash"],csrf)
                    con.execute("UPDATE sessions SET csrf_hash=? WHERE id_hash=?", (digest(csrf), user["id_hash"]))
                return self.json(200, {"user": self.user_json(user), "csrf": csrf})
            if not path.startswith("/api/"):
                return self.static(path)
            user = self.require_auth()
            if not user:
                return
            if path == "/api/members":
                with connect() as con:
                    rows = con.execute("SELECT id,display_name,role,color FROM users WHERE household_id=? ORDER BY created_at", (user["household_id"],)).fetchall()
                return self.json(200, {"members": [dict(r) for r in rows]})
            if path == "/api/items":
                query = parse_qs(urlparse(self.path).query)
                kind = query.get("kind", [""])[0]
                if kind not in KINDS:
                    return self.json(400, {"error": "Choose a supported household list."})
                with connect() as con:
                    rows = list_items(con, user["household_id"], kind)
                return self.json(200, {"items": [dict(r) for r in rows]})
            if path == "/api/summary":
                with connect() as con:
                    rows = con.execute("SELECT kind,COUNT(*) total,SUM(CASE WHEN completed=0 THEN 1 ELSE 0 END) open FROM items WHERE household_id=? GROUP BY kind", (user["household_id"],)).fetchall()
                    balances = con.execute("SELECT member_id,SUM(amount) balance FROM points_ledger WHERE household_id=? GROUP BY member_id", (user["household_id"],)).fetchall()
                    members = con.execute("SELECT id,display_name,role,color FROM users WHERE household_id=?", (user["household_id"],)).fetchall()
                return self.json(200, {"counts": {r["kind"]: {"total": r["total"], "open": r["open"]} for r in rows}, "members": [dict(m, points=next((b["balance"] for b in balances if b["member_id"] == m["id"]), 0)) for m in members]})
            if path == "/api/events":
                return self.event_stream(user)
            return self.static(path)
        except Exception as exc:
            self.json(500, {"error": "Request could not be completed.", "requestId": new_id()})

    def user_json(self, user):
        return {"id": user["id"], "username": user["username"], "displayName": user["display_name"], "role": user["role"], "color": user["color"], "household": user["household_name"], "timezone": user["timezone"]}

    def event_stream(self, user):
        channel = EVENTS.subscribe(user["household_id"])
        self.close_connection = True
        self.send_response(200)
        self.response_headers("text/event-stream; charset=utf-8", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            last_check = time.monotonic()
            while True:
                if time.monotonic() - last_check >= 15:
                    current = self.auth()
                    if not current or current["id"] != user["id"] or current["household_id"] != user["household_id"]:
                        break
                    last_check = time.monotonic()
                try:
                    payload = channel.get(timeout=15)
                    self.wfile.write(("event: household-change\ndata: " + payload + "\n\n").encode())
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass
        finally:
            EVENTS.unsubscribe(user["household_id"], channel)

    def do_POST(self):
        path = self.route()
        if not self.origin_ok():
            return self.json(403, {"error": "Request origin was not accepted."})
        try:
            data = self.body()
            if path == "/api/setup":
                return self.setup(data)
            if path == "/api/login":
                return self.login(data)
            user = self.require_auth()
            if not user:
                return
            if user["role"] == "display" and path not in {"/api/logout"}:
                return self.json(403, {"error": "This read-only display cannot change household data."})
            if not self.csrf_ok(data.get("csrf")):
                return self.json(403, {"error": "Refresh the page and try again."})
            if path == "/api/logout":
                with connect() as con:
                    con.execute("DELETE FROM sessions WHERE id_hash=?", (user["id_hash"],))
                self.send_response(204)
                self.response_headers()
                secure = "; Secure" if os.environ.get("APP_URL", "https://localhost").startswith("https://") else ""
                self.send_header("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict{secure}")
                self.end_headers()
                return
            if path == "/api/items":
                return self.create_item(user, data)
            if path.startswith("/api/items/") and path.endswith("/complete"):
                return self.complete_item(user, path.split("/")[3], data)
            if path == "/api/members":
                return self.create_member(user, data)
            if path == "/api/password":
                return self.change_password(user, data)
            return self.json(404, {"error": "That action is not available."})
        except ValueError as exc:
            self.json(400, {"error": str(exc)[:180]})
        except Exception:
            self.json(500, {"error": "Request could not be completed.", "requestId": new_id()})

    def setup(self, data):
        username = self.clean(data.get("username"), 40)
        password = data.get("password", "")
        display = self.clean(data.get("displayName"), 70)
        household = self.clean(data.get("household"), 70)
        if not username or len(username) < 3 or not display or not household:
            raise ValueError("Enter a household, your name, and a username with at least 3 characters.")
        if not isinstance(password, str) or len(password) < 12 or len(password) > 200:
            raise ValueError("Choose a password between 12 and 200 characters.")
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT 1 FROM households LIMIT 1").fetchone():
                con.rollback()
                return self.json(409, {"error": "Initial setup has already been completed."})
            hid, uid = new_id(), new_id()
            con.execute("INSERT INTO households(id,name,timezone) VALUES(?,?,?)", (hid, household, os.environ.get("HOUSEHOLD_TIMEZONE", "America/Chicago")))
            con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES(?,?,?,?,?,'owner')", (uid,hid,username,pw_hash(password),display))
            con.commit()
        finally:
            con.close()
        return self.open_session(uid)

    def login(self, data):
        username = self.clean(data.get("username"), 40)
        password = data.get("password", "")
        if not username or not isinstance(password, str):
            return self.json(400, {"error": "Enter your username and password."})
        ip_key = "ip:" + self.client_address[0]
        throttle_key = "user:" + username.casefold()
        if rate_limited(ip_key) or rate_limited(throttle_key):
            return self.json(429, {"error": "Too many attempts. Wait a few minutes, then try again."})
        with connect() as con:
            row = con.execute("SELECT id,password_hash FROM users WHERE username=? COLLATE NOCASE LIMIT 1", (username,)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            record_login_failure([(ip_key, 24),(throttle_key, 8)])
            time.sleep(.15)
            return self.json(401, {"error": "Username or password did not match."})
        FAILED_LOGINS.pop(throttle_key, None)
        return self.open_session(row["id"])

    def open_session(self, uid):
        token, csrf = secrets.token_urlsafe(36), secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        with connect() as con:
            con.execute("INSERT INTO sessions(id_hash,user_id,csrf_hash,expires_at) VALUES(?,?,?,?)", (digest(token),uid,digest(csrf),expiry.isoformat()))
            store_csrf(con,digest(token),csrf)
            user = con.execute("SELECT u.*,h.name household_name,h.timezone FROM users u JOIN households h ON h.id=u.household_id WHERE u.id=?", (uid,)).fetchone()
            con.execute("INSERT INTO audit_log(id,household_id,actor_id,action) VALUES(?,?,?,'session.login')", (new_id(),user["household_id"],uid))
        secure = "; Secure" if os.environ.get("APP_URL", "https://localhost").startswith("https://") else ""
        self.json(200, {"user": self.user_json(user), "csrf": csrf}, {"Set-Cookie": f"{COOKIE}={token}; Path=/; Max-Age={SESSION_DAYS*86400}; HttpOnly; SameSite=Strict{secure}"})

    def create_member(self, user, data):
        if user["role"] not in {"owner", "admin"}:
            return self.json(403, {"error": "Only household owners and administrators can add members."})
        name = self.clean(data.get("displayName"), 70)
        username = self.clean(data.get("username"), 40)
        role = data.get("role")
        password = data.get("password", "")
        color = data.get("color", "#78937D")
        if not name or not username or len(username) < 3:
            raise ValueError("Enter a name and username with at least 3 characters.")
        if role not in {"admin", "adult", "child", "display"}:
            raise ValueError("Choose an available member role.")
        if role != "child" and (not isinstance(password,str) or len(password) < 12):
            raise ValueError("Choose a password with at least 12 characters.")
        if role == "child" and password and len(password) < 12:
            raise ValueError("If a child password is set, it must be at least 12 characters.")
        if color not in COLORS:
            color = "#78937D"
        uid = new_id()
        try:
            with connect() as con:
                con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role,color) VALUES(?,?,?,?,?,?,?)", (uid,user["household_id"],username,pw_hash(password or secrets.token_urlsafe(24)),name,role,color))
                con.execute("INSERT INTO audit_log(id,household_id,actor_id,action,object_id) VALUES(?,?,?,'member.create',?)", (new_id(),user["household_id"],user["id"],uid))
        except sqlite3.IntegrityError:
            raise ValueError("That username is already in use.")
        EVENTS.publish(user["household_id"], {"kind": "member", "id": uid, "action": "created"})
        self.json(201, {"id": uid, "displayName": name, "role": role, "color": color})

    def change_password(self, user, data):
        current = data.get("currentPassword", "")
        password = data.get("newPassword", "")
        if not isinstance(password, str) or len(password) < 12 or len(password) > 200:
            raise ValueError("Choose a password between 12 and 200 characters.")
        with connect() as con:
            row = con.execute("SELECT password_hash FROM users WHERE id=? AND household_id=?", (user["id"],user["household_id"])).fetchone()
            if not row or not verify_password(current, row["password_hash"]):
                return self.json(400, {"error": "Current password did not match."})
            con.execute("UPDATE users SET password_hash=? WHERE id=? AND household_id=?", (pw_hash(password),user["id"],user["household_id"]))
            con.execute("DELETE FROM sessions WHERE user_id=? AND id_hash<>?", (user["id"],user["id_hash"]))
            con.execute("INSERT INTO audit_log(id,household_id,actor_id,action) VALUES(?,?,?,'account.password.change')", (new_id(),user["household_id"],user["id"]))
        self.json(200, {"ok": True})

    def create_item(self, user, data):
        kind = data.get("kind")
        title = self.clean(data.get("title"), 120)
        details = self.clean(data.get("details", ""), 1000)
        due = self.clean(data.get("dueAt", ""), 40) or None
        assigned = self.clean(data.get("assignedTo", ""), 40) or (user["id"] if kind == "task" and user["role"] == "child" else None)
        value = data.get("points", 0)
        if kind not in KINDS or not title:
            raise ValueError("Choose a list and provide a title.")
        if due:
            try:
                datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Enter a valid date or date and time.")
        if not isinstance(value, int) or value < 0 or value > 10000:
            raise ValueError("Points must be a whole number from 0 to 10,000.")
        if kind == "task" and value and user["role"] not in PRIVILEGED:
            return self.json(403, {"error": "Only an adult can assign points to a task."})
        if kind == "task" and user["role"] == "child" and assigned not in (None, user["id"]):
            return self.json(403, {"error": "You can only create tasks assigned to yourself."})
        with connect() as con:
            if assigned and not con.execute("SELECT 1 FROM users WHERE id=? AND household_id=?", (assigned,user["household_id"])).fetchone():
                raise ValueError("Choose a member in this household.")
            iid = new_id()
            key = self.clean(data.get("idempotencyKey", ""), 80) or None
            con.execute("INSERT INTO items(id,household_id,kind,title,details,due_at,assigned_to,value,idempotency_key,created_by) VALUES(?,?,?,?,?,?,?,?,?,?)", (iid,user["household_id"],kind,title,details,due,assigned,value,key,user["id"]))
            con.execute("INSERT INTO audit_log(id,household_id,actor_id,action,object_id) VALUES(?,?,?,'item.create',?)", (new_id(),user["household_id"],user["id"],iid))
        EVENTS.publish(user["household_id"], {"kind": kind, "id": iid, "action": "created"})
        self.json(201, {"id": iid,"kind":kind,"title":title,"details":details,"due_at":due,"assigned_to":assigned,"completed":0,"value":value,"version":1})

    def complete_item(self, user, iid, data):
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            updated = complete_item(con,iid,user["household_id"],user["id"],user["role"])
            if not updated:
                con.rollback()
                return self.json(404, {"error": "That household item was not found."})
            con.commit()
            EVENTS.publish(user["household_id"], {"kind": updated["kind"], "id": iid, "action": "completed"})
            return self.json(200, dict(updated))
        except PermissionError as exc:
            con.rollback()
            return self.json(403, {"error": str(exc)})
        finally:
            con.close()

    def clean(self, value, limit):
        if not isinstance(value, str):
            return ""
        value = " ".join(value.replace("\x00", "").split())
        if len(value) > limit:
            raise ValueError(f"Text must be {limit} characters or fewer.")
        return value

    def static(self, path):
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/manifest.webmanifest": "manifest.webmanifest", "/sw.js": "sw.js", "/logo.svg": "logo.svg", "/icon.svg": "icon.svg"}
        name = files.get(path)
        if not name:
            return self.json(404, {"error": "Page not found."})
        file = ROOT / "app" / "static" / name
        raw = file.read_bytes()
        typ = {".html":"text/html; charset=utf-8", ".js":"text/javascript; charset=utf-8", ".css":"text/css; charset=utf-8", ".svg":"image/svg+xml", ".webmanifest":"application/manifest+json"}.get(file.suffix,"application/octet-stream")
        self.send_response(200)
        self.response_headers(typ, "no-cache" if name in {"index.html", "sw.js"} else "public, max-age=86400")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    migrate()
    address = os.environ.get("BIND_ADDRESS", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "3000"))
    print(f"Household Six listening on {address}:{port}; SQLite database at {DB_PATH}")
    ThreadingHTTPServer((address, port), Handler).serve_forever()
