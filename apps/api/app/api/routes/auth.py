from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.auth import LoginRequest, UserRead
from app.services.auth import SESSION_MAX_AGE_SECONDS, AuthService

router = APIRouter()
service = AuthService()


@router.post("/auth/login", response_model=UserRead)
def login(
    payload: LoginRequest, response: Response, session: Session = Depends(get_db_session)
) -> UserRead:
    user = service.authenticate(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        service.issue_session(user),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "development",
    )
    return UserRead(id=user.id, email=user.email)


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(get_settings().session_cookie_name, httponly=True, samesite="lax")
    return response


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(id=user.id, email=user.email)
