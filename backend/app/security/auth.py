import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.models.entities import User
from backend.app.models.auth_sessions import AuthSession
from backend.app.core.config import ENVIRONMENT

SECRET = os.getenv("JWT_SECRET")
if ENVIRONMENT == "production" and (not SECRET or len(SECRET) < 32):
    raise RuntimeError("Production requires JWT_SECRET with at least 32 characters")
SECRET = SECRET or secrets.token_urlsafe(48)
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    raw = base64.b64decode(encoded)
    return hmac.compare_digest(raw[16:], hashlib.scrypt(password.encode(), salt=raw[:16], n=16384, r=8, p=1))


def token(user: User, db: Session):
    issued = datetime.now(timezone.utc)
    expires = issued + timedelta(hours=2)
    session_id = secrets.token_urlsafe(32)
    db.add(AuthSession(id=session_id, user_id=user.id, expires_at=expires.isoformat()))
    db.commit()
    return jwt.encode(
        {"sub": str(user.id), "jti": session_id, "exp": expires, "iat": issued},
        SECRET,
        algorithm="HS256",
    )


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    try:
        if not credentials:
            raise ValueError()
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
        session = db.get(AuthSession, payload["jti"])
        if (
            not user
            or not session
            or session.user_id != user.id
            or session.revoked_at
            or datetime.fromisoformat(session.expires_at) <= datetime.now(timezone.utc)
        ):
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Authentication required")


def require(*roles):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Role does not permit this action")
        return user

    return dependency
