from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.models import User
from app.services.auth import AuthService


def get_current_user(request: Request, session: Session = Depends(get_db_session)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    user = AuthService.resolve_session(session, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
