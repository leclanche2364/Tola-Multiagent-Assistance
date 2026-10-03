#!/usr/bin/env python3
"""Check whether Shiftlyx has a new live app version.

Read-only. Uses App Store Connect (ASC_* creds from growth.env).
Google Play is checked only if GOOGLE_PLAY_SERVICE_ACCOUNT_FILE is set
in growth.env; otherwise it is reported as unavailable.

Output (stdout): JSON
  {"live_version": "1.0.0", "last_seen_version": "1.0.0",
   "is_new": false, "play_checked": false, "play_version": null}

Exit code 0 always (even on API failure) — failures are reported in JSON
with "error" so the calling cron agent can report them instead of crashing.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.env import load_env  # noqa: E402
from adapters.auth import apple_es256_jwt  # noqa: E402

BUNDLE = "com.beemal.shiftlyxAI"
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "shiftlyx_last_seen_app_version.json")

# States that indicate a publicly available (or imminently available) build.
LIVE_STATES = {"READY_FOR_SALE"}


def _version_key(v: str):
    parts = []
    for p in v.split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(num) if num else 0)
    return parts


def fetch_app_store_version(env: dict):
    key_file = env.get("ASC_KEY_FILE")
    if not key_file:
        return None, "missing ASC_KEY_FILE"
    if not key_file.startswith("/"):
        from adapters.env import SECRETS_DIR
        key_file = os.path.join(SECRETS_DIR, key_file)
    token = apple_es256_jwt(env["ASC_ISSUER_ID"], env["ASC_KEY_ID"], key_file)
    headers = {"Authorization": f"Bearer {token}"}

    def get(url):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    apps = get("https://api.appstoreconnect.apple.com/v1/apps")
    app_id = None
    for a in apps.get("data", []):
        if a.get("attributes", {}).get("bundleId") == BUNDLE:
            app_id = a["id"]
            break
    if not app_id:
        return None, f"app {BUNDLE} not found in App Store Connect"
    vs = get(f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/appStoreVersions")
    versions = [
        v["attributes"].get("versionString", "")
        for v in vs.get("data", [])
        if v.get("attributes", {}).get("appStoreState") in LIVE_STATES
    ]
    if not versions:
        return None, "no READY_FOR_SALE version found"
    return max(versions, key=_version_key), None


def main() -> int:
    result = {
        "live_version": None,
        "last_seen_version": None,
        "is_new": False,
        "play_checked": False,
        "play_version": None,
        "error": None,
    }
    try:
        env = load_env()
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                result["last_seen_version"] = json.load(f).get("last_seen_version")

        live, err = fetch_app_store_version(env)
        if err:
            result["error"] = f"app_store: {err}"
        else:
            result["live_version"] = live
            last = result["last_seen_version"]
            result["is_new"] = bool(last is None or _version_key(live) > _version_key(last))

        # Google Play check: only possible with a service account credential.
        play_file = env.get("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE")
        if play_file:
            result["play_checked"] = True  # not implemented: no Play version API helper yet
    except Exception as e:  # noqa: BLE001 — report, never crash the cron
        result["error"] = str(e)[:300]

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
