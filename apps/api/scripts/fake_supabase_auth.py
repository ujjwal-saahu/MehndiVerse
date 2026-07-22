"""A minimal local stand-in for Supabase's Auth (GoTrue) REST API — see
docs/visual-testing-guide.md#real-registrationlogin-now-works-locally.

Not part of the product. Implements just the 6 endpoints
app/integrations/supabase_auth.py calls, enough for real registration/login
to work end-to-end against this machine's own backend without a real
Supabase project. Tokens are signed with this same backend's own
SUPABASE_JWT_SECRET (read from apps/api/.env, never printed), so the
backend verifies them locally exactly as it would a real Supabase-issued
token — see docs/authentication.md#2.

User accounts are kept in a small local JSON file (email -> {id, password,
email_confirmed}), seeded with the same 5 persona ids
scripts/seed_local_data.py printed, so logging in as e.g.
customer@mehndiverse.example resolves to the same backend User row that
already has seeded bookings/reviews.

Usage: .venv/Scripts/python scripts/fake_supabase_auth.py
"""

import json
import time
import uuid
from pathlib import Path
from typing import Any

import jwt as pyjwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
_STORE_PATH = Path(__file__).resolve().parent / ".fake_supabase_users.json"

# Known persona ids — keep in sync with scripts/seed_local_data.py's output
# so logging in as a persona resolves to its already-seeded backend row.
_SEEDED_IDS = {
    "customer@mehndiverse.example": "7d90055a-6d78-4a00-91ff-96f7ea749942",
    "artist@mehndiverse.example": "fc35b8f6-15af-4010-87fc-fe68c447b27e",
    "verified-artist@mehndiverse.example": "b3899688-78ab-4069-a6d5-4aa75e29112c",
    "moderator@mehndiverse.example": "aab42454-b31b-418f-80bc-2af27a946cd5",
    "admin@mehndiverse.example": "9122145f-4420-4154-b09e-3f5798825769",
}


def _load_jwt_secret() -> str:
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("SUPABASE_JWT_SECRET="):
            return line.strip().split("=", 1)[1]
    return "placeholder-jwt-secret-change-me"


def _load_store() -> dict[str, Any]:
    if _STORE_PATH.exists():
        loaded: dict[str, Any] = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return loaded
    store = {
        email: {"id": user_id, "password": None, "email_confirmed": True}
        for email, user_id in _SEEDED_IDS.items()
    }
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")
    return store


def _save_store(store: dict[str, Any]) -> None:
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


_SECRET = _load_jwt_secret()
_STORE = _load_store()

app = FastAPI(title="fake-supabase-auth")


def _mint(user_id: str, email: str) -> dict[str, Any]:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    access_token = pyjwt.encode(payload, _SECRET, algorithm="HS256")
    return {
        "access_token": access_token,
        "refresh_token": f"fake-refresh-{user_id}",
        "expires_in": 3600,
        "user": {"id": user_id, "email": email, "email_confirmed_at": "2026-01-01T00:00:00Z"},
    }


@app.post("/auth/v1/signup")
async def signup(request: Request) -> JSONResponse:
    body = await request.json()
    email = body["email"]
    existing = _STORE.get(email)
    if existing is None:
        user_id = str(uuid.uuid4())
        _STORE[email] = {"id": user_id, "password": body.get("password"), "email_confirmed": True}
        _save_store(_STORE)
    else:
        user_id = existing["id"]
    return JSONResponse(_mint(user_id, email))


@app.post("/auth/v1/token")
async def token(request: Request) -> JSONResponse:
    grant_type = request.query_params.get("grant_type")
    body = await request.json()
    if grant_type == "password":
        email = body["email"]
        record = _STORE.get(email)
        if record is None:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid login credentials."},
                status_code=400,
            )
        return JSONResponse(_mint(record["id"], email))
    if grant_type == "refresh_token":
        # Local-only convenience: not validating the refresh token's
        # authenticity (this is a disposable local test double, not a
        # security boundary) — just re-mint for whichever email last used it.
        refresh_token = body.get("refresh_token", "")
        user_id = refresh_token.removeprefix("fake-refresh-")
        for email, record in _STORE.items():
            if record["id"] == user_id:
                return JSONResponse(_mint(user_id, email))
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid refresh token."},
            status_code=400,
        )
    return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)


@app.post("/auth/v1/logout")
async def logout() -> JSONResponse:
    return JSONResponse({})


@app.post("/auth/v1/recover")
async def recover() -> JSONResponse:
    return JSONResponse({})


@app.post("/auth/v1/resend")
async def resend() -> JSONResponse:
    return JSONResponse({})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9999)
