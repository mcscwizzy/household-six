"""Exercise authenticated HTTP persistence against the disposable Compose app."""
from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
import uuid


BASE = os.environ.get("HOUSEHOLD_SIX_URL", "http://127.0.0.1:18088").rstrip("/")
RUN_ID = os.environ["CI_RUN_ID"]
USERNAME = f"ci-{RUN_ID[:24]}"
PASSWORD = f"CI-{uuid.uuid5(uuid.NAMESPACE_URL, RUN_ID).hex}-Safe-Passphrase"
TITLE = f"compose-persistence-{RUN_ID}"
JAR = http.cookiejar.CookieJar()
CLIENT = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))


def request(path: str, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with CLIENT.open(req, timeout=8) as response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else None


def sign_in():
    _, result = request("/api/login", "POST", {"username": USERNAME, "password": PASSWORD})
    return result["csrf"]


def create_and_complete():
    _, setup = request("/api/setup", "POST", {
        "household": f"CI {RUN_ID}", "displayName": "CI Owner",
        "username": USERNAME, "password": PASSWORD,
    })
    csrf = setup["csrf"]
    _, item = request("/api/items", "POST", {"kind": "task", "title": TITLE, "csrf": csrf})
    _, completed = request(f"/api/items/{item['id']}/complete", "POST", {
        "csrf": csrf, "expectedVersion": item["version"], "mutationId": str(uuid.uuid4()),
    })
    if completed["completed"] != 1:
        raise AssertionError("task completion was not persisted")
    print(f"Created and completed disposable task {TITLE}")


def verify_persisted():
    csrf = sign_in()
    _, response = request("/api/items?kind=task")
    found = next((item for item in response["items"] if item["title"] == TITLE), None)
    if not found or found["completed"] != 1:
        raise AssertionError("task was not preserved after container restart")
    _, me = request("/api/me")
    if not me["user"] or not me["csrf"]:
        raise AssertionError("authenticated session did not survive restart")
    if not csrf:
        raise AssertionError("login did not return a CSRF token")
    print(f"Verified authenticated data after restart: {TITLE}")


if __name__ == "__main__":
    if sys.argv[1:] == ["create"]:
        create_and_complete()
    elif sys.argv[1:] == ["verify"]:
        verify_persisted()
    else:
        raise SystemExit("usage: compose_smoke.py create|verify")
