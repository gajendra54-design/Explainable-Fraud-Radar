"""Verify authenticated API -> durable queue -> separate worker integration.

Run inside the backend container after migration. Replays the default synthetic
seed, so transaction IDs are deduplicated. Credentials are never printed.
"""

import json
import os
import time
import urllib.request


def request(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1" + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


auth = request("/auth/login", {"username": os.environ.get("BOOTSTRAP_USERNAME", "admin"), "password": os.environ["BOOTSTRAP_PASSWORD"]})
access = auth["access_token"]
before = request("/transactions?page_size=1", token=access)["total"]
run = request("/pipeline/runs", {"transactions": 3000, "customers": 180, "seed": 42, "fraud_rate": 0.06}, access)
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    runs = request("/pipeline/runs", token=access)["items"]
    current = next(row for row in runs if row["id"] == run["id"])
    if current["status"] in ("completed", "failed"):
        break
    time.sleep(1)
else:
    raise AssertionError("Worker did not finish the persisted job within 120 seconds")
assert current["status"] == "completed", current["status"]
after = request("/transactions?page_size=1", token=access)["total"]
assert after == before, "Default seed replay unexpectedly added transactions"
assert current["duplicates"] == 3000
live = request("/monitoring/live-performance", token=access)
request("/auth/logout", {}, access)
print(json.dumps({"worker_job": "completed", "attempts": current["attempts"], "deduplicated": current["duplicates"], "transactions_unchanged": after, "live_monitoring_status": live["status"]}))
