from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.team_profiles import (
    TeamDuplicateRequest,
    TeamProfileCreate,
    TeamProfileRead,
    TeamProfileUpdate,
    TeamRivalryCreate,
    TeamRivalryRead,
    TeamRivalryUpdate,
)
from app.services.team_profiles import (
    DuplicateTeamProfileError,
    TeamProfileNotFoundError,
    TeamProfileService,
)

router = APIRouter(prefix="/teams")
service = TeamProfileService()


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team profile not found")


def _duplicate() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="A duplicate value already exists"
    )


@router.get("", response_model=list[TeamProfileRead])
def list_teams(session: Session = Depends(get_db_session)) -> list[TeamProfileRead]:
    return [TeamProfileRead.model_validate(profile) for profile in service.list_profiles(session)]


@router.post("", response_model=TeamProfileRead, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamProfileCreate,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.create_profile(session, payload))
    except DuplicateTeamProfileError as error:
        raise _duplicate() from error


@router.get("/{team_id}", response_model=TeamProfileRead)
def get_team(team_id: UUID, session: Session = Depends(get_db_session)) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.get_profile(session, team_id))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error


@router.patch("/{team_id}", response_model=TeamProfileRead)
def update_team(
    team_id: UUID,
    payload: TeamProfileUpdate,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.update_profile(session, team_id, payload))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error
    except DuplicateTeamProfileError as error:
        raise _duplicate() from error


@router.post("/{team_id}/activate", response_model=TeamProfileRead)
def activate_team(
    team_id: UUID,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.set_active(session, team_id, True))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error


@router.post("/{team_id}/deactivate", response_model=TeamProfileRead)
def deactivate_team(
    team_id: UUID,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.set_active(session, team_id, False))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error


@router.post(
    "/{team_id}/duplicate", response_model=TeamProfileRead, status_code=status.HTTP_201_CREATED
)
def duplicate_team(
    team_id: UUID,
    payload: TeamDuplicateRequest,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamProfileRead:
    try:
        return TeamProfileRead.model_validate(service.duplicate_profile(session, team_id, payload))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error
    except DuplicateTeamProfileError as error:
        raise _duplicate() from error


@router.get("/{team_id}/rivalries", response_model=list[TeamRivalryRead])
def list_rivalries(
    team_id: UUID, session: Session = Depends(get_db_session)
) -> list[TeamRivalryRead]:
    try:
        return [
            TeamRivalryRead.model_validate(rivalry)
            for rivalry in service.list_rivalries(session, team_id)
        ]
    except TeamProfileNotFoundError as error:
        raise _not_found() from error


@router.post(
    "/{team_id}/rivalries", response_model=TeamRivalryRead, status_code=status.HTTP_201_CREATED
)
def create_rivalry(
    team_id: UUID,
    payload: TeamRivalryCreate,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamRivalryRead:
    try:
        return TeamRivalryRead.model_validate(service.create_rivalry(session, team_id, payload))
    except TeamProfileNotFoundError as error:
        raise _not_found() from error
    except DuplicateTeamProfileError as error:
        raise _duplicate() from error


@router.patch("/{team_id}/rivalries/{rivalry_id}", response_model=TeamRivalryRead)
def update_rivalry(
    team_id: UUID,
    rivalry_id: UUID,
    payload: TeamRivalryUpdate,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> TeamRivalryRead:
    try:
        return TeamRivalryRead.model_validate(
            service.update_rivalry(session, team_id, rivalry_id, payload)
        )
    except TeamProfileNotFoundError as error:
        raise _not_found() from error
    except DuplicateTeamProfileError as error:
        raise _duplicate() from error


@router.delete("/{team_id}/rivalries/{rivalry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rivalry(
    team_id: UUID,
    rivalry_id: UUID,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> Response:
    try:
        service.delete_rivalry(session, team_id, rivalry_id)
    except TeamProfileNotFoundError as error:
        raise _not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
