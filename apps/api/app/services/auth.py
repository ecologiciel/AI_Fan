from __future__ import annotations

import base64
import hashlib
import hmac
import os
from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.models import User

PASSWORD_SCHEME = "scrypt"
PASSWORD_N = 2**14
PASSWORD_R = 8
PASSWORD_P = 1
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=PASSWORD_N, r=PASSWORD_R, p=PASSWORD_P
    )
    return ":".join(
        (
            PASSWORD_SCHEME,
            str(PASSWORD_N),
            str(PASSWORD_R),
            str(PASSWORD_P),
            _encode(salt),
            _encode(derived),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = password_hash.split(":")
        if scheme != PASSWORD_SCHEME:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=_decode(salt), n=int(n), r=int(r), p=int(p)
        )
        return hmac.compare_digest(actual, _decode(expected))
    except (ValueError, TypeError):
        return False


class AuthService:
    def authenticate(self, session: Session, email: str, password: str) -> User | None:
        user = session.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.active or not verify_password(password, user.password_hash):
            return None
        return user

    def ensure_admin(self, session: Session) -> User:
        settings = get_settings()
        email = settings.admin_email.lower()
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return existing
        admin = User(email=email, password_hash=hash_password(settings.admin_password), active=True)
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin

    @staticmethod
    def issue_session(user: User) -> str:
        return _serializer().dumps({"user_id": str(user.id)})

    @staticmethod
    def resolve_session(session: Session, token: str | None) -> User | None:
        if not token:
            return None
        try:
            payload = _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
            user_id = UUID(payload["user_id"])
        except (BadSignature, SignatureExpired, KeyError, ValueError):
            return None
        user = session.get(User, user_id)
        return user if user is not None and user.active else None


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_secret_key, salt="football-ai-session-v1")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))
