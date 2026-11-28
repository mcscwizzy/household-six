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
        self.database_path = Path(directory.name, "household.sqlite3")
        self.base = os.environ.get("HOUSEHOLD_SIX_TEST_URL", "http://127.0.0.1:18763")
        log = tempfile.TemporaryFile()
        self.addCleanup(log.close)
        process = subprocess.Popen(
            [sys.executable, "-m", "app.server"],
            env={**os.environ, "BIND_ADDRESS": "127.0.0.1", "APP_PORT": self.base.rsplit(":", 1)[1],
                 "DATA_DIR": directory.name, "APP_URL": self.base, "HOUSEHOLD_TIMEZONE": "America/Chicago"},
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
        self.assertEqual(self.request(owner, "/requirements.lock")[0], 404)
        self.assertEqual(self.request(owner, "/api/setup", ["invalid"]), (400, {"error": "Expected a JSON object."}))
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
        utc_series = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Verification//EN",
                                    "BEGIN:VEVENT", "UID:synthetic-utc-series", "SUMMARY:UTC class",
                                    "DTSTART:20260301T150000Z", "DTEND:20260301T160000Z",
                                    "RRULE:FREQ=WEEKLY;COUNT=3", "END:VEVENT", "END:VCALENDAR", ""])
        self.assertEqual(mutate(path + "/import", {"ics": utc_series})[0], 201)
        _, expanded = self.request(owner, url)
        self.assertEqual([item["occurrenceStart"] for item in expanded["events"] if item["title"] == "UTC class"],
                         ["2026-03-01T09:00:00", "2026-03-08T10:00:00", "2026-03-15T10:00:00"])


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

    def test_recurring_chore_approval_and_reward_redemption(self):
        owner, child = self.client(), self.client()
        password = "A disposable passphrase"
        owner_auth = self.setup_owner(owner)
        _, member = self.request(owner, "/api/members", {
            "csrf": owner_auth["csrf"], "displayName": "Child", "username": "child", "role": "child", "password": password,
        })
        _, child_auth = self.request(child, "/api/login", {"username": "child", "password": password})

        def write(client, auth, path, fields, mutation_id=None):
            return self.request(client, path, {**fields, "csrf": auth["csrf"], "mutationId": mutation_id or str(uuid.uuid4())})

        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo(owner_auth["user"]["timezone"])).date()
        date = today.isoformat()
        tomorrow = (today + timedelta(days=1)).isoformat()
        status, chore = write(owner, owner_auth, "/api/chores", {
            "title": "Brush teeth", "start": date, "repeat": "daily", "routine": "bedtime",
            "assignees": [member["id"]], "points": 7, "approvalRequired": True,
        })
        self.assertEqual(status, 201)
        _, board = self.request(child, f"/api/chores?date={tomorrow}")
        self.assertEqual(board["scheduled"][0]["routine"], "bedtime")
        self.assertEqual(board["scheduled"][0]["status"], "open")
        finish_path = f"/api/chores/{chore['id']}/complete"
        completion = {"date": date, "assignedTo": member["id"], "expectedVersion": 1}
        request_id = str(uuid.uuid4())
        status, done = write(child, child_auth, finish_path, completion, request_id)
        self.assertEqual((status, done["status"]), (200, "pending"))
        self.assertEqual(write(child, child_auth, finish_path, completion, request_id)[1]["id"], done["id"])
        self.assertEqual(self.request(child, "/api/summary")[1]["members"][1]["points"], 0)
        approval = f"/api/chores/occurrences/{done['id']}/review"
        self.assertEqual(write(child, child_auth, approval, {"approved": True, "expectedVersion": done["version"]})[0], 403)
        self.assertEqual(write(owner, owner_auth, approval, {"approved": True, "expectedVersion": done["version"]})[1]["status"], "approved")
        self.assertEqual(write(owner, owner_auth, approval, {"approved": True, "expectedVersion": done["version"]})[0], 409)
        status, reward = write(owner, owner_auth, "/api/rewards", {"title": "Choose a movie", "points": 5})
        self.assertEqual(status, 201)
        status, request = write(child, child_auth, f"/api/rewards/{reward['id']}/request", {"expectedVersion": 1})
        self.assertEqual((status, request["status"]), (201, "pending"))
        self.assertEqual(write(child, child_auth, f"/api/rewards/{reward['id']}/request", {"expectedVersion": 1})[0], 409)
        review_path = f"/api/rewards/redemptions/{request['id']}/review"
        self.assertEqual(write(owner, owner_auth, review_path, {"approved": True, "expectedVersion": 1})[1]["status"], "approved")
        _, store = self.request(child, "/api/rewards")
        self.assertEqual(store["balance"], 2)
        self.assertEqual(store["requests"][0]["title"], "Choose a movie")

    def test_meal_plan_scales_and_synchronizes_groceries(self):
        owner = self.client()
        auth = self.setup_owner(owner)

        def write(path, fields, method="POST"):
            return self.request(owner, path, {**fields, "csrf": auth["csrf"], "mutationId": str(uuid.uuid4())},
                                method=method)

        status, recipe = write("/api/recipes", {
            "title": "Breakfast oats", "servings": 2, "instructions": "Cook oats. Add milk.",
            "ingredients": [{"name": "Oats", "quantity": "1.5", "unit": "cups", "category": "Pantry"}],
        })
        self.assertEqual(status, 201)
        fields = {"date": "2026-11-23", "slot": "breakfast", "recipeId": recipe["id"], "servings": 4}
        status, meal = write("/api/meals", fields)
        self.assertEqual(status, 201)
        _, plan = self.request(owner, "/api/meals?date=2026-11-25")
        self.assertEqual((plan["weekStart"], plan["meals"][0]["title"], plan["meals"][0]["servings"]),
                         ("2026-11-23", "Breakfast oats", 4))
        sync = {"date": "2026-11-23", "listId": "default"}
        self.assertEqual(write("/api/meals/groceries", sync)[1]["created"], 1)
        self.assertEqual(write("/api/meals/groceries", sync)[1]["created"], 0)
        _, groceries = self.request(owner, "/api/shopping")
        self.assertEqual([item["quantity"] for item in groceries["items"]], ["3 cups"])
        self.assertEqual(write(f"/api/meals/{meal['id']}", {**fields, "servings": 2, "expectedVersion": 1}, "PUT")[0], 200)
        self.assertEqual(write("/api/meals/groceries", sync)[1]["updated"], 1)
        _, groceries = self.request(owner, "/api/shopping")
        self.assertEqual([item["quantity"] for item in groceries["items"]], ["1.5 cups"])
        self.assertEqual(write(f"/api/meals/{meal['id']}", {"expectedVersion": 2}, "DELETE")[0], 204)
        self.assertEqual(write("/api/meals/groceries", sync)[1]["removed"], 1)
        self.assertEqual(self.request(owner, "/api/shopping")[1]["items"], [])

    @unittest.skipUnless(os.environ.get("HOUSEHOLD_SIX_AI_LIVE") == "1", "requires a configured local Ollama model")
    def test_six_real_model_and_explicit_confirmation(self):
        owner = self.client()
        auth = self.setup_owner(owner)

        def write(path, fields, request_id=None):
            return self.request(owner, path, {**fields, "csrf": auth["csrf"], "mutationId": request_id or str(uuid.uuid4())})

        cases = [
            ("grocery", "Add 2 bags of rolled oats to groceries.", "proposal"),
            ("calendar", "Schedule Library visit tomorrow from 09:00 to 10:00.", "proposal"),
            ("chore", "Every morning starting tomorrow, feed the cat.", "proposal"),
            ("question", "How many items are on the shopping list?", "result"),
            ("recipe", "Banana oats. Serves 2. Ingredients: 1 cup oats; 2 bananas. Bring to a simmer and serve.", "proposal"),
            ("document", "Library reminder: book club meets on the first Friday. Bring your library card.", "result"),
        ]
        for kind, prompt, expected in cases:
            with self.subTest(kind=kind):
                status, created = write("/api/six", {"kind": kind, "text": prompt})
                self.assertEqual(status, 202)
                for _ in range(150):
                    _, result = self.request(owner, "/api/six")
                    job = next(item for item in result["jobs"] if item["id"] == created["id"])
                    if job["state"] not in {"queued", "running"}:
                        break
                    time.sleep(.5)
                self.assertEqual(job["state"], expected, job["result"])
                if kind == "grocery":
                    self.assertEqual(self.request(owner, "/api/shopping")[1]["items"], [])
                    proposal_id = f"/api/six/{job['id']}/decision"
                    decision = {"confirm": True, "expectedVersion": job["version"]}
                    request_id = str(uuid.uuid4())
                    self.assertEqual(write(proposal_id, decision, request_id)[1]["state"], "applied")
                    self.assertEqual(write(proposal_id, decision, request_id)[1]["state"], "applied")
                    self.assertEqual(len(self.request(owner, "/api/shopping")[1]["items"]), 1)
                    self.assertIn("oats", self.request(owner, "/api/shopping")[1]["items"][0]["title"].lower())
                if kind == "question":
                    self.assertEqual(job["result"]["topic"], "shopping")
                    self.assertIn("1 to get", job["result"]["lines"][0])

    def test_inventory_preserves_stock_and_rejects_stale_changes(self):
        owner = self.client()
        auth = self.setup_owner(owner)

        def write(path, fields, method="POST", request_id=None):
            return self.request(owner, path, {**fields, "csrf": auth["csrf"], "mutationId": request_id or str(uuid.uuid4())},
                                method=method)

        status, item = write("/api/inventory", {
            "title": "Yogurt", "location": "refrigerator", "quantity": "1.5",
            "unit": "containers", "threshold": "1", "expiresOn": "2027-04-30",
        })
        self.assertEqual(status, 201)
        destination = f"/api/inventory/{item['id']}/stock"
        operation = str(uuid.uuid4())
        fields = {"direction": "use", "amount": "0.75", "expectedVersion": 1}
        self.assertEqual(write(destination, fields, request_id=operation)[1]["quantity"], "0.75")
        self.assertEqual(write(destination, fields, request_id=operation)[1]["quantity"], "0.75")
        self.assertEqual(write(destination, fields)[0], 409)
        self.assertEqual(write(destination, {"direction": "use", "amount": "1", "expectedVersion": 2})[0], 409)
        _, inventory = self.request(owner, "/api/inventory?location=refrigerator")
        self.assertTrue(inventory["items"][0]["low"])
        self.assertEqual(inventory["history"][0]["amount"], "0.75")
        self.assertFalse(self.request(owner, "/api/inventory?location=freezer")[1]["items"])

    def test_cross_household_api_cannot_read_or_modify_identified_records(self):
        import sqlite3

        from app.server import pw_hash

        first, second = self.client(), self.client()
        auth = self.setup_owner(first)
        password = "A separate synthetic password"
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("INSERT INTO households(id,name) VALUES('separate','Separate')")
            connection.execute("""INSERT INTO users(id,household_id,username,password_hash,display_name,role)
                VALUES('second','separate','second',?,'Second','owner')""", (pw_hash(password),))
        _, second_login = self.request(second, "/api/login", {"username": "second", "password": password})
        fields = {"csrf": auth["csrf"], "mutationId": str(uuid.uuid4()), "name": "Private list"}
        _, first_list = self.request(first, "/api/shopping/lists", fields)
        status, _ = self.request(second, "/api/shopping?list=" + first_list["id"])
        self.assertEqual(status, 404)
        status, _ = self.request(second, f"/api/shopping/lists/{first_list['id']}/items", {
            "csrf": second_login["csrf"], "mutationId": str(uuid.uuid4()), "title": "Foreign change",
        })
        self.assertEqual(status, 404)
        replay = {"csrf": auth["csrf"], "mutationId": str(uuid.uuid4()), "kind": "task", "title": "Private task"}
        status, original = self.request(first, "/api/items", replay)
        self.assertEqual(status, 201)
        self.assertEqual(self.request(first, "/api/items", replay)[1]["id"], original["id"])
        self.assertEqual(self.request(first, "/api/items", {**replay, "title": "Changed content"})[0], 409)
        self.assertEqual(self.request(second, "/api/items?kind=task")[1]["items"], [])

    def test_announcements_expire_and_acknowledge_per_member(self):
        owner, child = self.client(), self.client()
        auth = self.setup_owner(owner)
        _, member = self.request(owner, "/api/members", {
            "csrf": auth["csrf"], "displayName": "Child", "username": "child", "role": "child",
            "password": "A disposable passphrase",
        })
        self.assertEqual(member["role"], "child")
        _, child_auth = self.request(child, "/api/login", {"username": "child", "password": "A disposable passphrase"})

        def write(client, csrf, path, fields):
            return self.request(client, path, {**fields, "csrf": csrf, "mutationId": str(uuid.uuid4())})

        fields = {"title": "Family meeting", "details": "Saturday at breakfast", "pinned": True, "expiresOn": "2100-12-01"}
        self.assertEqual(write(child, child_auth["csrf"], "/api/announcements", fields)[0], 403)
        status, note = write(owner, auth["csrf"], "/api/announcements", fields)
        self.assertEqual(status, 201)
        self.assertEqual(write(owner, auth["csrf"], "/api/announcements",{**fields, "expiresOn": "2000-01-02"})[0], 201)
        _, result = self.request(child, "/api/announcements")
        self.assertEqual([item["id"] for item in result["items"]], [note["id"]])
        status, ack = write(child, child_auth["csrf"], f"/api/announcements/{note['id']}/ack", {"expectedVersion": 1})
        self.assertEqual((status, ack["acknowledged"]), (200, True))
        self.assertFalse(self.request(owner, "/api/announcements")[1]["items"][0]["acknowledged"])
        self.assertEqual(self.request(owner, "/api/announcements")[1]["items"][0]["ackCount"], 1)

    @unittest.skipUnless(os.environ.get("HOUSEHOLD_SIX_AI_LIVE") == "1", "requires a configured local Ollama model")
    def test_six_real_attachment_extraction(self):
        import base64

        owner = self.client()
        auth = self.setup_owner(owner)
        directory = Path(__file__).parent / "fixtures" / "six"
        for file, mime, expected in [
            ("note.png", "image/png", "library"),
            ("note.pdf", "application/pdf", "library"),
        ]:
            with self.subTest(file=file):
                status, created = self.request(owner, "/api/six", {
                    "kind": "document", "text": "Extract the printed text in this note.", "fileType": mime,
                    "attachment": base64.b64encode((directory / file).read_bytes()).decode(),
                    "csrf": auth["csrf"], "mutationId": str(uuid.uuid4()),
                })
                self.assertEqual(status, 202)
                for _ in range(150):
                    _, result = self.request(owner, "/api/six")
                    job = next(item for item in result["jobs"] if item["id"] == created["id"])
                    if job["state"] not in {"queued", "running"}:
                        break
                    time.sleep(.5)
                self.assertEqual(job["state"], "result", job["result"])
                self.assertIn(expected, job["result"]["extracted_text"].lower())

    def test_habit_streaks_and_immutable_allowance(self):
        owner, child = self.client(), self.client()
        owner_auth = self.setup_owner(owner)
        password = "A disposable passphrase"
        _, member = self.request(owner, "/api/members", {
            "csrf": owner_auth["csrf"], "displayName": "Child", "username": "child", "role": "child", "password": password,
        })
        _, child_auth = self.request(child, "/api/login", {"username": "child", "password": password})

        def write(client, auth, path, fields, operation=None):
            return self.request(client, path, {**fields, "csrf": auth["csrf"], "mutationId": operation or str(uuid.uuid4())})

        status, habit = write(child, child_auth, "/api/habits", {"title": "Read a book"})
        self.assertEqual(status, 201)
        _, initial = self.request(child, "/api/habits")
        change = {"expectedVersion": habit["version"], "date": initial["date"]}
        request_id = str(uuid.uuid4())
        path = f"/api/habits/{habit['id']}/check"
        self.assertEqual(write(child, child_auth, path, change, request_id)[1]["streak"], 1)
        self.assertEqual(write(child, child_auth, path, change, request_id)[1]["streak"], 1)
        _, board = self.request(child, "/api/habits")
        self.assertEqual(len(board["habits"][0]["days"]), 1)

        fields = {"memberId": member["id"], "amount": "5.50", "direction": "credit",
                  "note": "Weekly allowance", "expectedVersion": 1}
        self.assertEqual(write(child, child_auth, "/api/allowance", fields)[0], 403)
        self.assertEqual(write(owner, owner_auth, "/api/allowance", fields)[1]["balance"], 550)
        self.assertEqual(write(owner, owner_auth, "/api/allowance", fields)[0], 409)
        fields.update({"direction": "paid", "amount": "6", "expectedVersion": 2})
        self.assertEqual(write(owner, owner_auth, "/api/allowance", fields)[0], 409)
        fields["amount"] = "2.25"
        self.assertEqual(write(owner, owner_auth, "/api/allowance", fields)[1]["balance"], 325)
        _, ledger = self.request(child, "/api/allowance")
        self.assertEqual(len(ledger["wallets"]), 1)
        self.assertEqual(ledger["wallets"][0]["balance"], 325)
        self.assertEqual(len(ledger["entries"]), 2)

    def test_property_care_http_permissions_schedules_and_vehicle_history(self):
        owner, child = self.client(), self.client()
        owner_auth = self.setup_owner(owner)
        password = "A disposable passphrase"
        _, member = self.request(owner, "/api/members", {
            "csrf": owner_auth["csrf"], "displayName": "Child", "username": "child", "role": "child", "password": password,
        })
        _, child_auth = self.request(child, "/api/login", {"username": "child", "password": password})
        status, templates = self.request(owner, "/api/maintenance/templates")
        self.assertEqual(status, 200)
        self.assertEqual(len(templates["templates"]), 7)
        self.assertEqual(self.request(owner, "/api/maintenance")[1]["schedules"], [])
        self.assertEqual(self.request(child, "/api/maintenance")[0], 403)

        fields = {"title": "HVAC filter", "category": "hvac", "dueOn": "2026-12-01",
                  "frequency": "quarterly", "intervalCount": 1, "assignedTo": member["id"],
                  "estimatedCostCents": 1800}
        denied = self.request(child, "/api/maintenance", {**fields, "csrf": child_auth["csrf"], "mutationId": str(uuid.uuid4())})
        self.assertEqual(denied[0], 403)
        status, schedule = self.request(owner, "/api/maintenance", {
            **fields, "csrf": owner_auth["csrf"], "mutationId": str(uuid.uuid4()),
        })
        self.assertEqual(status, 201)
        owner_today = self.request(owner, "/api/dashboard")[1]
        self.assertEqual(owner_today["maintenance"][0]["title"], "HVAC filter")
        self.assertEqual(self.request(child, "/api/dashboard")[1]["maintenance"], [])
        complete_path = f"/api/maintenance/{schedule['id']}/complete"
        stale = self.request(owner, complete_path, {
            "csrf": owner_auth["csrf"], "mutationId": str(uuid.uuid4()), "expectedVersion": 9,
            "performedOn": "2026-12-01", "costCents": 2400,
        })
        self.assertEqual(stale[0], 409)
        status, saved = self.request(owner, complete_path, {
            "csrf": owner_auth["csrf"], "mutationId": str(uuid.uuid4()), "expectedVersion": 1,
            "performedOn": "2026-12-01", "costCents": 2400,
        })
        self.assertEqual((status, saved["dueOn"]), (200, "2027-03-01"))
        self.assertEqual(self.request(owner, "/api/maintenance")[1]["history"][0]["costCents"], 2400)

        status, vehicle = self.request(owner, "/api/vehicles", {
            "csrf": owner_auth["csrf"], "mutationId": str(uuid.uuid4()), "make": "Toyota", "model": "Prius",
            "year": 2022, "fuel": "hybrid", "odometer": 28000, "nickname": "Blue car", "registrationDue": "2026-12-01",
        })
        self.assertEqual(status, 201)
        status, service = self.request(owner, "/api/vehicles/services", {
            "csrf": owner_auth["csrf"], "mutationId": str(uuid.uuid4()), "vehicleId": vehicle["id"],
            "serviceType": "Tire rotation", "performedOn": "2026-11-27", "odometer": 28000,
            "intervalMiles": 5000, "costCents": 7500,
        })
        self.assertEqual((status, service["dueOdometer"]), (201, 33000))
        self.assertEqual(self.request(owner, "/api/dashboard")[1]["vehicleReminders"][0]["serviceType"], "Registration renewal")
        self.assertEqual(self.request(child, "/api/vehicles")[0], 403)

    def test_household_session_listing_requires_account_management_scope(self):
        owner, child = self.client(), self.client()
        owner_auth = self.setup_owner(owner)
        password = "A disposable passphrase"
        _, member = self.request(owner, "/api/members", {
            "csrf": owner_auth["csrf"], "displayName": "Child", "username": "child", "role": "child", "password": password,
        })
        _, child_auth = self.request(child, "/api/login", {"username": "child", "password": password})
        status, sessions = self.request(owner, "/api/sessions/list", {
            "csrf": owner_auth["csrf"], "targetId": member["id"],
        }, method="POST")
        self.assertEqual(status, 200)
        self.assertEqual(len(sessions["sessions"]), 1)
        self.assertFalse(sessions["sessions"][0]["current"])
        denied = self.request(child, "/api/sessions/list", {
            "csrf": child_auth["csrf"], "targetId": owner_auth["user"]["id"],
        }, method="POST")
        self.assertEqual(denied[0], 403)
