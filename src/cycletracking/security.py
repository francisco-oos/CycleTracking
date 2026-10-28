"""Sesiones opacas revocables y autorización por rol. Sin cuentas predeterminadas."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from cycletracking.models import SessionToken, User


password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
ROLES = frozenset({"ADMIN", "OPERATIVO", "INVENTARIOS"})


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Se requieren al menos 12 caracteres")
    return password_hasher.hash(password)


def verify_password(password: str, digest: str) -> bool:
    return password_hasher.verify(password, digest)


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(40)
    db.add(SessionToken(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
    ))
    db.commit()
    return token


def get_current_user(session_dependency):
    """Fábrica para vincular la sesión de BD de esta instancia ASGI."""
    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(session_dependency),
    ) -> User:
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED"})
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        token = db.get(SessionToken, digest)
        if token is None:
            raise HTTPException(status_code=401, detail={"code": "AUTH_INVALID"})
        expiry = token.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            db.delete(token)
            db.commit()
            raise HTTPException(status_code=401, detail={"code": "AUTH_EXPIRED"})
        user = db.get(User, token.user_id)
        if user is None or not user.active:
            raise HTTPException(status_code=401, detail={"code": "AUTH_INVALID"})
        return user
    return current_user


def require_role(user: User, *allowed: str) -> None:
    if user.role not in allowed:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})
