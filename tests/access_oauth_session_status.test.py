"""session_status must ask the server, not just find a stored token.

On 2026-09-23 OCR's --auth-status printed "session active" while the token
endpoint answered `invalid_grant: Grant not found`; work that trusted it
stopped at a browser sign-in nobody could complete. Run: python3 <this file>.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib" / "stardust_access"))
os.environ["STARDUST_ACCESS_TOKEN_FILE"] = str(Path(tempfile.mkdtemp()) / "oauth.json")

import access_oauth  # noqa: E402

BASE = "https://ocr.example.test/v1"
access_oauth.discover = lambda base_url: {"token_endpoint": "t", "resource": "r"}


def refused(metadata, record):
    raise RuntimeError('OAuth endpoint returned HTTP 400: {"error":"invalid_grant"}')


def unreachable(metadata, record):
    raise RuntimeError("Could not reach OAuth endpoint: timed out")


def rotated(metadata, record):
    return {"access_token": "a", "refresh_token": "new"}


def never_interactive(metadata):
    raise AssertionError("status must never open a browser")


access_oauth._interactive_tokens = never_interactive

assert access_oauth.session_status(BASE) is False, "no stored session"

account = access_oauth._origin(BASE)
access_oauth.store_record({"client_id": "c", "refresh_token": "old"}, account)

access_oauth._refresh = refused
assert access_oauth.session_status(BASE) is False, "a revoked grant is not active"

access_oauth._refresh = unreachable
try:
    access_oauth.session_status(BASE)
except RuntimeError:
    pass
else:
    raise AssertionError("an unreachable endpoint must not read as signed out")

access_oauth._refresh = rotated
assert access_oauth.session_status(BASE) is True
assert access_oauth.load_record(account)["refresh_token"] == "new", "keep the rotated token"

print("ok")
