from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import jwt
from backend.app.db.session import get_db
from backend.app.models.auth_sessions import AuthSession
from backend.app.models.entities import User, Audit, now
from backend.app.security.auth import current_user, require, bearer, SECRET, verify_password, hash_password

from backend.app.schemas.responses import LogoutResponse, RevocationResponse, PasswordResponse

router = APIRouter(prefix="/api/v1")


def revoke(db, user_id):
    sessions = list(db.scalars(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))))
    for session in sessions:
        session.revoked_at = now()
    return len(sessions)


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer), user=Depends(current_user), db: Session = Depends(get_db)):
    payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
    db.get(AuthSession, payload["jti"]).revoked_at = now()
    db.add(Audit(actor=user.username, action="session_revoked", details={"scope": "current"}))
    db.commit()
    return {"status": "signed_out"}


@router.post("/auth/logout-all", response_model=RevocationResponse)
def logout_all(user=Depends(current_user), db: Session = Depends(get_db)):
    count = revoke(db, user.id)
    db.add(Audit(actor=user.username, action="sessions_revoked", details={"scope": "all", "count": count}))
    db.commit()
    return {"revoked": count}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.post("/auth/password", response_model=PasswordResponse)
def change_password(body: PasswordChange, user=Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, "Current password does not match")
    user.password_hash = hash_password(body.new_password)
    count = revoke(db, user.id)
    db.add(Audit(actor=user.username, action="password_changed", details={"revoked_sessions": count}))
    db.commit()
    return {"status": "password_changed", "reauthentication_required": True}


@router.post("/users/{user_id}/sessions/revoke", response_model=RevocationResponse)
def administrator_revoke(user_id: int, user=Depends(require("administrator")), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    count = revoke(db, target.id)
    db.add(
        Audit(
            actor=user.username, action="administrator_session_revocation", details={"target_user_id": user_id, "revoked_sessions": count}
        )
    )
    db.commit()
    return {"revoked": count}
