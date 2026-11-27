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
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.base = os.environ.get("HOUSEHOLD_SIX_TEST_URL", "http://127.0.0.1:18763")
        log = tempfile.TemporaryFile()
        cls.addClassCleanup(log.close)
        process = subprocess.Popen(
            [sys.executable, "-m", "app.server"],
            env={**os.environ, "BIND_ADDRESS": "127.0.0.1", "APP_PORT": cls.base.rsplit(":", 1)[1],
                 "DATA_DIR": directory.name, "APP_URL": cls.base},
            stdout=log, stderr=log,
        )

        def stop():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

        cls.addClassCleanup(stop)
        for _ in range(100):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(cls.base + "/api/health", timeout=1) as response:
                    if response.headers.get("Server") == "uvicorn" and Path(directory.name, "household.sqlite3").is_file():
                        return
            except OSError:
                pass
            time.sleep(.05)
        log.seek(0)
        raise AssertionError("Uvicorn did not start the app: " + log.read().decode())

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
