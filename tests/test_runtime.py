"""Run against Uvicorn with HOUSEHOLD_SIX_LIVE=1 and a disposable DB."""
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid


@unittest.skipUnless(os.environ.get("HOUSEHOLD_SIX_LIVE") == "1", "requires loopback sockets")
class RuntimeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = os.environ.get("HOUSEHOLD_SIX_TEST_URL", "http://127.0.0.1:18763")
        log = tempfile.TemporaryFile()
        self.addCleanup(log.close)
        process = subprocess.Popen(
            [sys.executable, "-m", "app.server"],
            env={**os.environ, "BIND_ADDRESS": "127.0.0.1", "APP_PORT": self.base.rsplit(":", 1)[1],
                 "DATA_DIR": directory.name, "APP_URL": self.base},
            stdout=log, stderr=log,
        )

        def stop():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

        self.addCleanup(stop)
        for _ in range(100):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(self.base + "/api/health", timeout=1) as response:
                    if response.headers.get("Server") == "uvicorn" and Path(directory.name, "household.sqlite3").is_file():
                        return
            except OSError:
                pass
            time.sleep(.05)
        log.seek(0)
        raise AssertionError("Uvicorn did not start the app: " + log.read().decode()[-4000:])

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, data=None, *, headers=None, method=None):
        body = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(self.base + path, body,
                                         {"Content-Type": "application/json", **(headers or {})}, method=method)
        try:
            response = client.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            raw = response.read()
            return response.status, json.loads(raw) if raw else None

    def test_authenticated_workflow(self):
        owner, child = self.client(), self.client()
        password = "A disposable passphrase"
        self.assertEqual(self.request(owner, "/api/members")[0], 401)
        status, setup = self.request(owner, "/api/setup", {
            "household": "Runtime Test", "displayName": "Parent", "username": "parent", "password": password,
        })
        self.assertEqual(status, 200)
        csrf = setup["csrf"]
        status, member = self.request(owner, "/api/members", {
            "csrf": csrf, "displayName": "Child", "username": "child", "role": "child", "password": password,
        })
        self.assertEqual(status, 201)
        status, task = self.request(owner, "/api/items", {
            "csrf": csrf, "kind": "task", "title": "Water plants", "assignedTo": member["id"], "points": 3,
        })
        self.assertEqual(status, 201)
        status, login = self.request(child, "/api/login", {"username": "child", "password": password})
        self.assertEqual(status, 200)
        self.assertEqual(login["user"]["role"], "child")
        path = f"/api/items/{task['id']}/complete"
        change = {"csrf": login["csrf"], "expectedVersion": 1, "mutationId": str(uuid.uuid4())}
        self.assertEqual(self.request(child, path, change, headers={"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request(child, path, {**change, "csrf": "invalid"})[0], 403)
        with owner.open(self.base + "/api/events", timeout=5) as events:
            self.assertEqual(events.headers["Content-Type"], "text/event-stream; charset=utf-8")
            self.assertEqual(events.readline(), b"retry: 3000\n")
            self.assertEqual(events.readline(), b"\n")
            self.assertEqual(self.request(child, path, change)[0], 200)
            self.assertEqual(events.readline(), b"event: household-change\n")
            self.assertEqual(json.loads(events.readline()[6:])["id"], task["id"])
        self.assertEqual(self.request(child, path, change)[1]["version"], 2)
        self.assertEqual(self.request(child, path, {**change, "mutationId": str(uuid.uuid4())})[0], 409)
        _, summary = self.request(owner, "/api/summary")
        self.assertEqual(next(m for m in summary["members"] if m["id"] == member["id"])["points"], 3)
        self.assertEqual(self.request(child, "/api/logout", {"csrf": login["csrf"]})[0], 204)
        self.assertEqual(self.request(child, "/api/items?kind=task")[0], 401)

    def test_shopping_workflow(self):
        owner, child = self.client(), self.client()
        password = "A disposable passphrase"
        login = self.setup_owner(owner)
        self.assertEqual(self.request(owner, "/api/members", {
            "csrf": login["csrf"], "displayName": "Child", "username": "child", "role": "child", "password": password,
        })[0], 201)
        _, child_login = self.request(child, "/api/login", {"username": "child", "password": password})

        def change(client, path, data, auth=login, *, method="POST", mutation_id=None):
            return self.request(client, path, {
                **data, "csrf": auth["csrf"], "mutationId": mutation_id or str(uuid.uuid4()),
            }, method=method)

        status, initial = self.request(owner, "/api/shopping?list=default")
        self.assertEqual(status, 200)
        self.assertEqual(initial["list"]["id"], "default")
        status, grocery_list = change(owner, "/api/shopping/lists", {"name": "Market"})
        self.assertEqual(status, 201)
        self.assertEqual(change(child, "/api/shopping/lists", {"name": "Forbidden"}, child_login)[0], 403)
        url = f"/api/shopping?list={grocery_list['id']}"
        path = f"/api/shopping/lists/{grocery_list['id']}/items"
        request_id = str(uuid.uuid4())
        data = {"title": "Oats", "quantity": "2 bags", "category": "Dry goods"}
        status, item = change(child, path, data, child_login, mutation_id=request_id)
        self.assertEqual(status, 201)
        self.assertEqual(change(child, path, data, child_login, mutation_id=request_id)[1]["id"], item["id"])
        self.assertEqual(len(self.request(owner, url)[1]["items"]), 1)
        self.assertFalse(self.request(owner, "/api/shopping?list=default")[1]["items"])
        edits = {**data, "quantity": "3 bags", "expectedVersion": 1}
        item_path = f"/api/shopping/items/{item['id']}"
        status, updated = change(child, item_path, edits, child_login, method="PUT")
        self.assertEqual((status, updated["quantity"], updated["version"]), (200, "3 bags", 2))
        self.assertEqual(change(owner, item_path, edits, method="PUT")[0], 409)
        legacy_path = f"/api/items/{item['id']}/complete"
        self.assertEqual(change(child, legacy_path, {"expectedVersion": 2}, child_login)[0], 200)
        self.assertEqual(self.request(owner, url)[1]["items"][0]["completed"], 1)
        self.assertEqual(change(owner, item_path, {"expectedVersion": 3}, method="DELETE")[0], 204)
        self.assertEqual(change(child, legacy_path, {"expectedVersion": 3}, child_login)[0], 404)
        self.assertEqual(self.request(owner, url)[1]["items"], [])


    def setup_owner(self, client):
        status, result = self.request(client, "/api/setup", {
            "household": "Runtime Test", "displayName": "Parent", "username": "parent",
            "password": "A disposable passphrase",
        })
        self.assertEqual(status, 200)
        return result

    def test_calendar_series_and_exchange(self):
        owner = self.client()
        csrf = self.setup_owner(owner)["csrf"]

        def mutate(path, fields, method="POST"):
            return self.request(owner, path, {**fields, "csrf": csrf, "mutationId": str(uuid.uuid4())}, method=method)

        path = "/api/calendar"
        invalid = {"title": "Missing hour", "start": "2026-03-08T02:00", "end": "2026-03-08T03:30"}
        self.assertEqual(mutate(path, invalid)[0], 422)
        event = {
            "title": "Swim practice", "start": "2026-03-01T09:00", "end": "2026-03-01T10:00",
            "repeat": "weekly", "exceptions": ["2026-03-15"],
        }
        status, series = mutate(path, event)
        self.assertEqual(status, 201)
        url = path + "?from=2026-03-01&to=2026-03-25"
        _, result = self.request(owner, url)
        self.assertEqual([item["occurrenceStart"] for item in result["events"]],
                         ["2026-03-01T09:00:00", "2026-03-08T09:00:00", "2026-03-22T09:00:00"])
        self.assertEqual([item["utcOffset"] for item in result["events"]], ["-06:00", "-05:00", "-05:00"])

        all_day = {"title": "Family trip", "start": "2026-03-10", "end": "2026-03-12", "allDay": True}
        self.assertEqual(mutate(path, all_day)[0], 201)
        _, result = self.request(owner, path + "?from=2026-03-11&to=2026-03-12")
        self.assertEqual([(item["title"], item["occurrenceEnd"]) for item in result["events"]],
                         [("Family trip", "2026-03-12")])
        series_url = f"{path}/{series['id']}"
        self.assertEqual(mutate(series_url, {**event, "title": "Swim team", "expectedVersion": 1}, "PUT")[0], 200)
        self.assertEqual(mutate(series_url, {"expectedVersion": 1}, "DELETE")[0], 409)

        with owner.open(self.base + path + "/export", timeout=5) as response:
            self.assertEqual(response.headers["Content-Type"], "text/calendar; charset=utf-8")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            exported = response.read().decode()
        self.assertIn("SUMMARY:Swim team", exported)
        self.assertIn("RRULE:FREQ=WEEKLY", exported)
        self.assertIn("EXDATE", exported)
        self.assertEqual(mutate(series_url, {"expectedVersion": 2}, "DELETE")[0], 204)
        self.assertEqual(mutate(path + "/import", {"ics": exported})[0], 201)
        self.assertEqual(mutate(path + "/import", {"ics": exported})[1]["created"], 0)

    def test_today_uses_household_date_and_separates_old_records(self):
        from datetime import datetime, timedelta, timezone
        from zoneinfo import ZoneInfo

        owner = self.client()
        login = self.setup_owner(owner)
        zone = ZoneInfo(login["user"]["timezone"])
        local_today = datetime.now(zone).date()
        today = local_today.isoformat()
        yesterday = (local_today - timedelta(days=1)).isoformat()
        tomorrow = (local_today + timedelta(days=1)).isoformat()
        next_midnight = datetime.combine(local_today + timedelta(days=1), datetime.min.time(), zone)
        last_local_hour = (next_midnight - timedelta(hours=1)).astimezone(timezone.utc).isoformat()
        for kind, title, due in [
            ("task", "Due late today", last_local_hour), ("task", "Overdue", yesterday),
            ("task", "Due tomorrow", tomorrow), ("meal", "Tonight", today),
            ("meal", "Yesterday's meal", yesterday), ("event", "Scheduled tomorrow", tomorrow),
        ]:
            self.assertEqual(self.request(owner, "/api/items", {
                "csrf": login["csrf"], "kind": kind, "title": title, "dueAt": due,
            })[0], 201)
        status, dashboard = self.request(owner, "/api/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["date"], today)
        self.assertEqual([item["title"] for item in dashboard["chores"]], ["Due late today"])
        self.assertEqual([item["title"] for item in dashboard["overdue"]], ["Overdue"])
        self.assertEqual([item["title"] for item in dashboard["meals"]], ["Tonight"])
        self.assertEqual([item["title"] for item in dashboard["upcoming"]], ["Scheduled tomorrow"])
