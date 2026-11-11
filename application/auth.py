"""Small password session layer for the hosted dashboard."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

COOKIE_NAME = "xeng_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def auth_required() -> bool:
    return bool(os.getenv("XENG_ADMIN_PASSWORD", "").strip())


def password_valid(password: str) -> bool:
    expected = os.getenv("XENG_ADMIN_PASSWORD", "")
    return bool(expected) and hmac.compare_digest(password, expected)


def _secret() -> bytes:
    value = os.getenv("XENG_SESSION_SECRET", "")
    if not value:
        value = os.getenv("XENG_ADMIN_PASSWORD", "local-xeng-session")
    return value.encode("utf-8")


def create_session() -> str:
    expires = str(int(time.time()) + SESSION_SECONDS)
    signature = hmac.new(_secret(), expires.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def session_valid(value: str | None) -> bool:
    if not value:
        return False
    try:
        expires, signature = value.split(".", 1)
        if int(expires) < int(time.time()):
            return False
    except (ValueError, TypeError):
        return False
    expected = hmac.new(_secret(), expires.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def secure_cookies() -> bool:
    return os.getenv("XENG_SECURE_COOKIES", "").lower() in {"1", "true", "yes"}
