"""Household Six API and local web application, served by Uvicorn."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
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
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app import announcements, assistant, calendar_service, chores, dashboard, database, inventory, meals, rewards, shopping
from app.mutations import DomainError, Mutation, row, statement

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


class ConflictError(Exception):
    """A write was based on an entity version that is no longer current."""


def can_create_member(actor_role, target_role):
    """Keep administrator creation and all member management owner-controlled."""
    if target_role == "owner":
        return False
    if actor_role == "owner":
        return target_role in {"admin", "adult", "child", "display"}
    if actor_role == "admin":
        return target_role in {"adult", "child", "display"}
    return False


def can_create_item(actor_role, kind):
    if kind not in KINDS or actor_role == "display":
        return False
    if actor_role == "child":
        return kind in {"task", "shopping"}
    return actor_role in PRIVILEGED


def valid_mutation_id(value):
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


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


def connect():
    return database.LegacyConnection(DB_PATH)


def migrate():
    database.migrate(DB_PATH)


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


def lookup_session(con, session_hash, now=None):
    """Resolve only unexpired sessions belonging to enabled accounts."""
    now = now or datetime.now(timezone.utc).isoformat()
    return con.execute("""SELECT s.id_hash,s.csrf_hash,u.id,u.household_id,u.username,u.display_name,u.role,u.color,
        h.name household_name,h.timezone
        FROM sessions s JOIN users u ON u.id=s.user_id JOIN households h ON h.id=u.household_id
        WHERE s.id_hash=? AND s.expires_at>? AND u.disabled_at IS NULL""", (session_hash, now)).fetchone()


def list_items(con, household_id, kind, day=None):
    return con.execute("""SELECT i.id,i.kind,i.title,i.details,i.due_at,i.assigned_to,i.completed,i.value,i.version,i.created_at,
        u.display_name assigned_name,u.color assigned_color
        FROM items i LEFT JOIN users u ON u.id=i.assigned_to AND u.household_id=i.household_id
        WHERE i.household_id=? AND i.kind=? AND i.deleted_at IS NULL
        AND NOT EXISTS (SELECT 1 FROM chore_completions c WHERE c.id=i.id AND c.household_id=i.household_id)
        AND NOT EXISTS (SELECT 1 FROM announcement_settings a WHERE a.id=i.id AND a.household_id=i.household_id AND a.expires_on<?)
        ORDER BY i.completed,COALESCE(i.due_at,i.created_at),i.created_at DESC LIMIT 250""", (household_id, kind, day)).fetchall()


def complete_item(con, iid, household_id, actor_id, role, expected_version=None):
    item = con.execute("SELECT * FROM items WHERE id=? AND household_id=? AND deleted_at IS NULL", (iid, household_id)).fetchone()
    if not item:
        return None
    if item["kind"] not in {"task", "shopping"} or con.execute(
        "SELECT 1 FROM chore_completions WHERE household_id=? AND id=?", (household_id, iid),
    ).fetchone():
        raise PermissionError("This household record does not support completion.")
    if role == "display":
        raise PermissionError("This read-only display cannot change household data.")
    if item["kind"] == "task" and role == "child" and item["assigned_to"] not in (None, actor_id):
        raise PermissionError("You can only complete a task assigned to you.")
    if expected_version is not None and item["version"] != expected_version:
        raise ConflictError("This item changed on another device. Refresh and try again.")
    if not item["completed"]:
        con.execute("UPDATE items SET completed=1,version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND household_id=? AND completed=0", (iid, household_id))
        if item["kind"] == "task" and item["value"] and item["assigned_to"]:
            con.execute("INSERT OR IGNORE INTO points_ledger(id,household_id,member_id,item_id,amount,reason) VALUES(?,?,?,?,?,'task.complete')", (new_id(),household_id,item["assigned_to"],iid,item["value"]))
        con.execute("INSERT INTO audit_log(id,household_id,actor_id,action,object_id) VALUES(?,?,?,'item.complete',?)", (new_id(),household_id,actor_id,iid))
    return con.execute("SELECT id,kind,title,details,due_at,assigned_to,completed,value,version FROM items WHERE id=? AND household_id=?", (iid, household_id)).fetchone()


class RequestContext:
    def __init__(self, request):
        self.request = request
        self.headers = request.headers
        self.session = None

    @staticmethod
    def json(status, data, extra_headers=None):
        return JSONResponse(data, status_code=status, headers=extra_headers)

    async def body(self, limit=32768):
        if self.headers.get("Transfer-Encoding"):
            raise HTTPException(400, "Transfer-encoded requests are not supported.")
        data = bytearray()
        async for chunk in self.request.stream():
            if len(data) + len(chunk) > limit:
                raise HTTPException(413, "Request is too large.")
            data.extend(chunk)
        try:
            object_value = json.loads(data or b"{}")
        except (ValueError, RecursionError):
            raise HTTPException(400, "Expected a JSON object.") from None
        if not isinstance(object_value, dict):
            raise HTTPException(400, "Expected a JSON object.")
        return object_value

    def origin_ok(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        parsed = urlparse(origin)
        return parsed.netloc == host and parsed.scheme in {"http", "https"}

    def csrf_ok(self, csrf):
        if not isinstance(csrf, str) or not csrf or not self.session:
            return False
        with connect() as con:
            return valid_csrf(con, self.session["id_hash"], csrf)

    def auth(self):
        token = self.request.cookies.get(COOKIE)
        if token:
            with connect() as con:
                self.session = lookup_session(con, digest(token))
        return self.session

    def read(self):
        path = self.request.url.path
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
            user = self.auth()
            if not user:
                return self.json(401, {"error": "Sign in to continue."})
            if path == "/api/members":
                with connect() as con:
                    rows = con.execute("SELECT id,display_name,role,color FROM users WHERE household_id=? ORDER BY created_at", (user["household_id"],)).fetchall()
                return self.json(200, {"members": [dict(r) for r in rows]})
            if path == "/api/items":
                kind = self.request.query_params.get("kind", "")
                if kind not in KINDS:
                    return self.json(400, {"error": "Choose a supported household list."})
                with connect() as con:
                    rows = list_items(con, user["household_id"], kind, announcements.current_day(user))
                return self.json(200, {"items": [dict(r) for r in rows]})
            if path == "/api/summary":
                with connect() as con:
                    rows = con.execute("SELECT kind,COUNT(*) total,SUM(CASE WHEN completed=0 THEN 1 ELSE 0 END) open FROM items WHERE household_id=? AND deleted_at IS NULL GROUP BY kind", (user["household_id"],)).fetchall()
                    balances = con.execute("SELECT member_id,SUM(amount) balance FROM points_ledger WHERE household_id=? GROUP BY member_id", (user["household_id"],)).fetchall()
                    members = con.execute("SELECT id,display_name,role,color FROM users WHERE household_id=?", (user["household_id"],)).fetchall()
                return self.json(200, {"counts": {r["kind"]: {"total": r["total"], "open": r["open"]} for r in rows}, "members": [dict(m, points=next((b["balance"] for b in balances if b["member_id"] == m["id"]), 0)) for m in members]})
            if path == "/api/events":
                return self.event_stream(user)
            return self.json(404, {"error": "Page not found."})
        except Exception:
            return self.json(500, {"error": "Request could not be completed.", "requestId": new_id()})

    def user_json(self, user):
        return {"id": user["id"], "username": user["username"], "displayName": user["display_name"], "role": user["role"], "color": user["color"], "household": user["household_name"], "timezone": user["timezone"]}

    def event_stream(self, user):
        household_id = user["household_id"]
        session_hash = user["id_hash"]

        def still_signed_in():
            with connect() as con:
                current = lookup_session(con, session_hash)
                return current and current["id"] == user["id"] and current["household_id"] == household_id

        async def events():
            channel = EVENTS.subscribe(household_id)
            try:
                yield "retry: 3000\n\n"
                heartbeat = time.monotonic() + 15
                while True:
                    if time.monotonic() >= heartbeat:
                        if not await run_in_threadpool(still_signed_in):
                            return
                        yield ": heartbeat\n\n"
                        heartbeat = time.monotonic() + 15
                    try:
                        payload = channel.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(.15)
                        continue
                    yield f"event: household-change\ndata: {payload}\n\n"
            finally:
                EVENTS.unsubscribe(household_id, channel)

        return StreamingResponse(events(), media_type="text/event-stream", headers={
            "X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-transform",
        })

    def write(self, data):
        path = self.request.url.path
        try:
            if path == "/api/setup":
                return self.setup(data)
            if path == "/api/login":
                return self.login(data)
            user = self.auth()
            if not user:
                return self.json(401, {"error": "Sign in to continue."})
            if user["role"] == "display" and path not in {"/api/logout"}:
                return self.json(403, {"error": "This read-only display cannot change household data."})
            if not self.csrf_ok(data.get("csrf")):
                return self.json(403, {"error": "Refresh the page and try again."})
            if path == "/api/logout":
                with connect() as con:
                    con.execute("DELETE FROM sessions WHERE id_hash=?", (user["id_hash"],))
                response = Response(status_code=204)
                response.delete_cookie(COOKIE, httponly=True, samesite="strict", secure=secure_cookie())
                return response
            if path == "/api/items":
                return self.create_item(user, data)
            if path.startswith("/api/items/") and path.endswith("/complete"):
                return self.complete_item(user, self.request.path_params["item_id"], data)
            if path == "/api/members":
                return self.create_member(user, data)
            if path == "/api/password":
                return self.change_password(user, data)
            return self.json(404, {"error": "That action is not available."})
        except DomainError as exc:
            return self.json(exc.status, {"error": str(exc)})
        except ValueError as exc:
            return self.json(400, {"error": str(exc)[:180]})
        except Exception:
            return self.json(500, {"error": "Request could not be completed.", "requestId": new_id()})

    def setup(self, data):
        username = self.clean(data.get("username"), 40)
        password = data.get("password", "")
        display = self.clean(data.get("displayName"), 70)
        household = self.clean(data.get("household"), 70)
        if not username or len(username) < 3 or not display or not household:
            raise ValueError("Enter a household, your name, and a username with at least 3 characters.")
        if not isinstance(password, str) or len(password) < 12 or len(password) > 200:
            raise ValueError("Choose a password between 12 and 200 characters.")
        timezone_name = os.environ.get("HOUSEHOLD_TIMEZONE", "America/Chicago")
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("The configured household timezone is invalid.") from None
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT 1 FROM households LIMIT 1").fetchone():
                con.rollback()
                return self.json(409, {"error": "Initial setup has already been completed."})
            hid, uid = new_id(), new_id()
            con.execute("INSERT INTO households(id,name,timezone) VALUES(?,?,?)", (hid, household, timezone_name))
            con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role) VALUES(?,?,?,?,?,'owner')", (uid,hid,username,pw_hash(password),display))
            con.commit()
        finally:
            con.close()
        return self.open_session(uid)

    def login(self, data):
        username = self.clean(data.get("username"), 40)
        password = data.get("password", "")
        if not username or not isinstance(password, str) or len(password) > 200:
            return self.json(400, {"error": "Enter your username and password."})
        ip_key = "ip:" + (self.request.client.host if self.request.client else "local")
        throttle_key = "user:" + username.casefold()
        if rate_limited(ip_key) or rate_limited(throttle_key):
            return self.json(429, {"error": "Too many attempts. Wait a few minutes, then try again."})
        with connect() as con:
            row = con.execute("SELECT id,password_hash,disabled_at FROM users WHERE username=? COLLATE NOCASE LIMIT 1", (username,)).fetchone()
        if not row or row["disabled_at"] or not verify_password(password, row["password_hash"]):
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
        response = self.json(200, {"user": self.user_json(user), "csrf": csrf})
        response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                            samesite="strict", secure=secure_cookie())
        return response

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
        if not isinstance(role, str) or role not in {"admin", "adult", "child", "display"}:
            raise ValueError("Choose an available member role.")
        if not can_create_member(user["role"], role):
            return self.json(403, {"error": "You are not allowed to add that household role."})
        if not isinstance(password, str) or len(password) > 200 or (role != "child" or password) and len(password) < 12:
            raise ValueError("Choose a password between 12 and 200 characters.")
        if not isinstance(color, str) or color not in COLORS:
            color = "#78937D"
        uid = new_id()
        try:
            with connect() as con:
                con.execute("INSERT INTO users(id,household_id,username,password_hash,display_name,role,color) VALUES(?,?,?,?,?,?,?)", (uid,user["household_id"],username,pw_hash(password or secrets.token_urlsafe(24)),name,role,color))
                con.execute("INSERT INTO audit_log(id,household_id,actor_id,action,object_id) VALUES(?,?,?,'member.create',?)", (new_id(),user["household_id"],user["id"],uid))
        except sqlite3.IntegrityError:
            raise ValueError("That username is already in use.")
        EVENTS.publish(user["household_id"], {"kind": "member", "id": uid, "action": "created"})
        return self.json(201, {"id": uid, "displayName": name, "role": role, "color": color})

    def change_password(self, user, data):
        current = data.get("currentPassword", "")
        password = data.get("newPassword", "")
        if not isinstance(password, str) or len(password) < 12 or len(password) > 200:
            raise ValueError("Choose a password between 12 and 200 characters.")
        with connect() as con:
            row = con.execute("SELECT password_hash FROM users WHERE id=? AND household_id=?", (user["id"],user["household_id"])).fetchone()
            if not row or not isinstance(current, str) or len(current) > 200 or not verify_password(current, row["password_hash"]):
                return self.json(400, {"error": "Current password did not match."})
            con.execute("UPDATE users SET password_hash=? WHERE id=? AND household_id=?", (pw_hash(password),user["id"],user["household_id"]))
            con.execute("DELETE FROM sessions WHERE user_id=? AND id_hash<>?", (user["id"],user["id_hash"]))
            con.execute("INSERT INTO audit_log(id,household_id,actor_id,action) VALUES(?,?,?,'account.password.change')", (new_id(),user["household_id"],user["id"]))
        return self.json(200, {"ok": True})

    def create_item(self, user, data):
        kind = data.get("kind")
        title = self.clean(data.get("title"), 120)
        details = self.clean(data.get("details", ""), 1000)
        due = self.clean(data.get("dueAt", ""), 40) or None
        assigned = self.clean(data.get("assignedTo", ""), 40) or (user["id"] if kind == "task" and user["role"] == "child" else None)
        value = data.get("points", 0)
        if not isinstance(kind, str) or kind not in KINDS or not title:
            raise ValueError("Choose a list and provide a title.")
        if not can_create_item(user["role"], kind):
            return self.json(403, {"error": "This account cannot create that household record."})
        if due:
            try:
                datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Enter a valid date or date and time.")
        if type(value) is not int or value < 0 or value > 10000:
            raise ValueError("Points must be a whole number from 0 to 10,000.")
        if kind == "task" and value and user["role"] not in PRIVILEGED:
            return self.json(403, {"error": "Only an adult can assign points to a task."})
        if kind == "task" and user["role"] == "child" and assigned not in (None, user["id"]):
            return self.json(403, {"error": "You can only create tasks assigned to yourself."})
        household, actor = user["household_id"], user["id"]
        key = self.clean(data.get("idempotencyKey", ""), 80) or None
        with database.engine(DB_PATH).connect() as con:
            con.exec_driver_sql("BEGIN IMMEDIATE")
            mutation = Mutation(con, user, "item.create", data, kind) if "mutationId" in data else None
            entity = mutation.replay_id if mutation else None
            fields = {"h": household, "actor": actor, "kind": kind, "title": title,
                      "details": details, "due": due, "assigned": assigned, "value": value, "key": key}
            if not entity and key:
                prior = row(con, "SELECT * FROM items WHERE household_id=:h AND idempotency_key=:key", **fields)
                if prior:
                    check = {"created_by": actor, "kind": kind, "title": title, "details": details,
                             "due_at": due, "assigned_to": assigned, "value": value}
                    if any(prior[name] != original for name, original in check.items()):
                        return self.json(409, {"error": "This request conflicts with a previous change."})
                    entity = prior["id"]
            if entity:
                existing = row(con, """SELECT id,kind,title,details,due_at,assigned_to,completed,value,version
                    FROM items WHERE id=:id AND household_id=:h AND deleted_at IS NULL""", h=household, id=entity)
                if not existing:
                    return self.json(404, {"error": "That household item was not found."})
                return self.json(201, dict(existing))
            if assigned and not row(con, "SELECT 1 FROM users WHERE id=:assigned AND household_id=:h AND disabled_at IS NULL", **fields):
                raise ValueError("Choose a member in this household.")
            iid = new_id()
            statement(con, """INSERT INTO items(id,household_id,kind,title,details,due_at,assigned_to,value,idempotency_key,created_by)
                VALUES(:id,:h,:kind,:title,:details,:due,:assigned,:value,:key,:actor)""", id=iid, **fields)
            if mutation:
                mutation.finish(iid, 1)
            else:
                statement(con, """INSERT INTO audit_log(id,household_id,actor_id,action,object_id)
                    VALUES(:audit,:h,:actor,'item.create',:id)""", audit=new_id(), id=iid, **fields)
            con.commit()
        EVENTS.publish(household, {"kind": kind, "id": iid, "action": "created"})
        return self.json(201, {"id": iid, "kind": kind, "title": title, "details": details, "due_at": due,
                               "assigned_to": assigned, "completed": 0, "value": value, "version": 1})

    def complete_item(self, user, iid, data):
        if "memberId" in data and data["memberId"] != user["id"]:
            return self.json(403, {"error": "Sign in as the member who queued this completion."})
        expected = data.get("expectedVersion")
        mutation_id = data.get("mutationId")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            return self.json(422, {"error": "Refresh this item before completing it."})
        if not valid_mutation_id(mutation_id):
            return self.json(422, {"error": "This completion request is invalid."})
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            receipt = con.execute("SELECT actor_id,operation,entity_id FROM mutation_receipts WHERE household_id=? AND mutation_id=?", (user["household_id"], mutation_id)).fetchone()
            if receipt:
                if receipt["actor_id"] != user["id"] or receipt["operation"] != "item.complete" or receipt["entity_id"] != iid:
                    con.rollback()
                    return self.json(409, {"error": "This queued change conflicts with another operation."})
                current = con.execute("SELECT id,kind,title,details,due_at,assigned_to,completed,value,version FROM items WHERE id=? AND household_id=? AND deleted_at IS NULL", (iid,user["household_id"])).fetchone()
                if not current:
                    con.rollback()
                    return self.json(404, {"error": "That household item was not found."})
                result = dict(current)
                con.commit()
                return self.json(200, result)
            updated = complete_item(con,iid,user["household_id"],user["id"],user["role"],expected_version=expected)
            if not updated:
                con.rollback()
                return self.json(404, {"error": "That household item was not found."})
            result = dict(updated)
            con.execute("INSERT INTO mutation_receipts(household_id,mutation_id,actor_id,operation,entity_id,result_version) VALUES(?,?,?,'item.complete',?,?)", (user["household_id"],mutation_id,user["id"],iid,result["version"]))
            con.commit()
            EVENTS.publish(user["household_id"], {"kind": updated["kind"], "id": iid, "action": "completed"})
            return self.json(200, result)
        except ConflictError as exc:
            con.rollback()
            return self.json(409, {"error": str(exc)})
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


def secure_cookie():
    return os.environ.get("APP_URL", "https://localhost").startswith("https://")


@asynccontextmanager
async def lifespan(_):
    await run_in_threadpool(migrate)
    stop = await run_in_threadpool(assistant.start_worker, database.engine(DB_PATH)) if assistant.enabled() else None
    try:
        yield
    finally:
        if stop:
            stop.set()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)


@app.middleware("http")
async def security_headers(request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse({"error": "Request could not be completed.", "requestId": new_id()}, status_code=500)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(HTTPException)
async def http_error(_, error):
    return JSONResponse({"error": error.detail}, status_code=error.status_code, headers=error.headers)


def read_api(request: Request):
    return RequestContext(request).read()


async def write_api(request: Request):
    context = RequestContext(request)
    if not context.origin_ok():
        return context.json(403, {"error": "Request origin was not accepted."})
    try:
        data = await context.body()
    except OSError:
        return context.json(400, {"error": "The request could not be read."})
    return await run_in_threadpool(context.write, data)


for path in ("/health", "/setup-state", "/me", "/members", "/items", "/summary", "/events"):
    app.add_api_route("/api" + path, read_api, methods=["GET"])

for path in ("/setup", "/login", "/logout", "/items", "/items/{item_id}/complete", "/members", "/password"):
    app.add_api_route("/api" + path, write_api, methods=["POST"])


def authorized(context, *, mutation=None):
    user = context.auth()
    if not user:
        raise DomainError(401, "Sign in to continue.")
    if mutation is not None:
        if user["role"] == "display":
            raise DomainError(403, "This read-only display cannot change household data.")
        if not context.csrf_ok(mutation.get("csrf")):
            raise DomainError(403, "Refresh the page and try again.")
    return user


@app.exception_handler(DomainError)
async def domain_error(_, error):
    return JSONResponse({"error": str(error)}, status_code=error.status)


@app.get("/api/shopping")
def shopping_read(request: Request, list: str = "default"):
    user = authorized(RequestContext(request))
    return shopping.load(database.engine(DB_PATH), user, list)


async def domain_write(request, service, kind, *, limit=32768):
    context = RequestContext(request)
    if not context.origin_ok():
        raise DomainError(403, "Request origin was not accepted.")
    data = await context.body(limit)
    operation = request.scope["route"].name
    target = request.path_params.get("target")

    def save():
        user = authorized(context, mutation=data)
        status, result, entity = service.write(database.engine(DB_PATH), user, operation, target, data)
        if entity:
            EVENTS.publish(user["household_id"], {"kind": kind, "id": entity, "action": operation})
        return Response(status_code=204) if status == 204 else JSONResponse(result, status_code=status)

    return await run_in_threadpool(save)


async def shopping_write(request: Request):
    return await domain_write(request, shopping, "shopping")


for path, method, operation in (
    ("/lists", "POST", "shopping.list.create"),
    ("/lists/{target}/items", "POST", "shopping.item.create"),
    ("/items/{target}", "PUT", "shopping.item.update"),
    ("/items/{target}", "DELETE", "shopping.item.delete"),
):
    app.add_api_route("/api/shopping" + path, shopping_write, methods=[method], name=operation)


@app.get("/api/calendar")
def calendar_read(request: Request, member: str | None = None):
    user = authorized(RequestContext(request))
    query = request.query_params
    return calendar_service.load(database.engine(DB_PATH), user, query.get("from"), query.get("to"), member)


@app.get("/api/calendar/export")
def calendar_export(request: Request):
    user = authorized(RequestContext(request))
    return Response(calendar_service.export_ics(database.engine(DB_PATH), user), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="household-six.ics"'})


async def calendar_write(request: Request):
    limit = 256_000 if request.scope["route"].name == "calendar.import" else 32_768
    return await domain_write(request, calendar_service, "event", limit=limit)


for path, method, operation in (
    ("", "POST", "calendar.create"),
    ("/import", "POST", "calendar.import"),
    ("/{target}", "PUT", "calendar.update"),
    ("/{target}", "DELETE", "calendar.delete"),
):
    app.add_api_route("/api/calendar" + path, calendar_write, methods=[method], name=operation)


@app.get("/api/dashboard")
def dashboard_read(request: Request):
    user = authorized(RequestContext(request))
    return dashboard.load(database.engine(DB_PATH), user)


@app.get("/api/chores")
def chores_read(request: Request, date: str | None = None):
    user = authorized(RequestContext(request))
    return chores.load(database.engine(DB_PATH), user, date)


@app.get("/api/rewards")
def rewards_read(request: Request):
    user = authorized(RequestContext(request))
    return rewards.load(database.engine(DB_PATH), user)


async def chores_write(request: Request):
    return await domain_write(request, chores, "task")


async def rewards_write(request: Request):
    return await domain_write(request, rewards, "reward")


for path, method, operation in (
    ("", "POST", "chore.create"),
    ("/{target}", "PUT", "chore.update"),
    ("/{target}", "DELETE", "chore.archive"),
    ("/{target}/complete", "POST", "chore.complete"),
    ("/occurrences/{target}/review", "POST", "chore.review"),
):
    app.add_api_route("/api/chores" + path, chores_write, methods=[method], name=operation)

for path, method, operation in (
    ("", "POST", "reward.create"),
    ("/{target}", "PUT", "reward.update"),
    ("/{target}", "DELETE", "reward.archive"),
    ("/{target}/request", "POST", "reward.request"),
    ("/redemptions/{target}/review", "POST", "reward.review"),
):
    app.add_api_route("/api/rewards" + path, rewards_write, methods=[method], name=operation)


@app.get("/api/recipes")
def recipes_read(request: Request):
    user = authorized(RequestContext(request))
    return meals.recipes(database.engine(DB_PATH), user)


@app.get("/api/meals")
def meals_read(request: Request, date: str | None = None):
    user = authorized(RequestContext(request))
    return meals.plan(database.engine(DB_PATH), user, date)


async def meals_write(request: Request):
    return await domain_write(request, meals, "meal")


for base, kind in (("/api/recipes", "recipe"), ("/api/meals", "meal")):
    app.add_api_route(base, meals_write, methods=["POST"], name=f"{kind}.create")
    app.add_api_route(base + "/{target}", meals_write, methods=["PUT"], name=f"{kind}.update")
    app.add_api_route(base + "/{target}", meals_write, methods=["DELETE"], name=f"{kind}.archive")
app.add_api_route("/api/meals/groceries", meals_write, methods=["POST"], name="meal.groceries")


@app.get("/api/six")
def six_read(request: Request):
    user = authorized(RequestContext(request))
    if not assistant.available():
        return {"modelEnabled": False, "jobs": []}
    return assistant.list_jobs(database.engine(DB_PATH), user)


async def six_write(request: Request):
    if not assistant.available():
        raise DomainError(404, "The assistant is disabled.")
    return await domain_write(request, assistant, "six", limit=800_000)


app.add_api_route("/api/six", six_write, methods=["POST"], name="six.enqueue")
app.add_api_route("/api/six/{target}/decision", six_write, methods=["POST"], name="six.decision")


@app.get("/api/inventory")
def inventory_read(request: Request, location: str = ""):
    user = authorized(RequestContext(request))
    return inventory.load(database.engine(DB_PATH), user, location)


async def inventory_write(request: Request):
    return await domain_write(request, inventory, "inventory")


for path, method, operation in (
    ("", "POST", "inventory.create"),
    ("/{target}", "PUT", "inventory.update"),
    ("/{target}", "DELETE", "inventory.archive"),
    ("/{target}/stock", "POST", "inventory.stock"),
):
    app.add_api_route("/api/inventory" + path, inventory_write, methods=[method], name=operation)


@app.get("/api/announcements")
def announcements_read(request: Request, include_expired: bool = False):
    user = authorized(RequestContext(request))
    return announcements.load(database.engine(DB_PATH), user, archive=include_expired)


async def announcements_write(request: Request):
    return await domain_write(request, announcements, "announcement")


for path, method, operation in (
    ("", "POST", "announcement.create"),
    ("/{target}", "PUT", "announcement.update"),
    ("/{target}", "DELETE", "announcement.archive"),
    ("/{target}/ack", "POST", "announcement.ack"),
):
    app.add_api_route("/api/announcements" + path, announcements_write, methods=[method], name=operation)


STATIC_FILES = {
    "index.html": "text/html", "app.js": "text/javascript", "offline.js": "text/javascript",
    "shopping.js": "text/javascript", "html.js": "text/javascript",
    "chores.js": "text/javascript", "rewards.js": "text/javascript", "meals.js": "text/javascript", "six.js": "text/javascript", "announcements.js": "text/javascript", "inventory.js": "text/javascript", "calendar.js": "text/javascript", "dashboard.js": "text/javascript", "dates.js": "text/javascript", "style.css": "text/css",
    "manifest.webmanifest": "application/manifest+json", "sw.js": "text/javascript",
    "logo.svg": "image/svg+xml", "icon.svg": "image/svg+xml",
    **dict.fromkeys(("apple-touch-icon.png", "pwa-192.png", "pwa-512.png", "pwa-maskable-512.png"), "image/png"),
}


@app.get("/")
@app.get("/{filename}")
def static(filename: str = "index.html"):
    media_type = STATIC_FILES.get(filename)
    if not media_type:
        raise HTTPException(404, "Page not found.")
    cache = "no-cache" if filename == "sw.js" or filename == "index.html" else "public, max-age=3600"
    return FileResponse(ROOT / "app" / "static" / filename, media_type=media_type,
                        headers={"Cache-Control": cache})


if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("BIND_ADDRESS", "127.0.0.1"),
                port=int(os.environ.get("APP_PORT", "3000")), access_log=False, proxy_headers=False, workers=1)
