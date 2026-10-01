from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models import TeamProfile, TeamRivalry
from app.schemas.team_profiles import (
    TeamDuplicateRequest,
    TeamProfileCreate,
    TeamProfileUpdate,
    TeamRivalryCreate,
    TeamRivalryUpdate,
)


class TeamProfileNotFoundError(Exception):
    pass


class DuplicateTeamProfileError(Exception):
    pass


class TeamProfileService:
    """Persistence operations for configurable teams; no team is hard-coded here."""

    def list_profiles(self, session: Session) -> list[TeamProfile]:
        return list(session.scalars(select(TeamProfile).order_by(TeamProfile.display_name)))

    def get_profile(self, session: Session, team_id: UUID) -> TeamProfile:
        profile = session.get(TeamProfile, team_id)
        if profile is None:
            raise TeamProfileNotFoundError
        return profile

    def create_profile(self, session: Session, payload: TeamProfileCreate) -> TeamProfile:
        profile = TeamProfile(**payload.model_dump())
        session.add(profile)
        self._commit(session)
        return profile

    def update_profile(
        self, session: Session, team_id: UUID, payload: TeamProfileUpdate
    ) -> TeamProfile:
        profile = self.get_profile(session, team_id)
        changes = payload.model_dump(exclude_unset=True)
        if changes:
            for field, value in changes.items():
                setattr(profile, field, value)
            profile.profile_version += 1
            self._commit(session)
        return profile

    def set_active(self, session: Session, team_id: UUID, active: bool) -> TeamProfile:
        profile = self.get_profile(session, team_id)
        if profile.active != active:
            profile.active = active
            profile.profile_version += 1
            self._commit(session)
        return profile

    def duplicate_profile(
        self, session: Session, team_id: UUID, payload: TeamDuplicateRequest
    ) -> TeamProfile:
        source = self.get_profile(session, team_id)
        values = {
            column.name: getattr(source, column.name)
            for column in TeamProfile.__table__.columns
            if column.name
            not in {"id", "slug", "display_name", "short_name", "created_at", "updated_at"}
        }
        profile = TeamProfile(
            **values,
            slug=payload.slug,
            display_name=payload.display_name or source.display_name,
            short_name=payload.short_name or source.short_name,
            profile_version=1,
        )
        session.add(profile)
        self._commit(session)
        return profile

    def list_rivalries(self, session: Session, team_id: UUID) -> list[TeamRivalry]:
        self.get_profile(session, team_id)
        return list(
            session.scalars(
                select(TeamRivalry)
                .where(TeamRivalry.team_profile_id == team_id)
                .order_by(TeamRivalry.intensity.desc(), TeamRivalry.opponent_name)
            )
        )

    def create_rivalry(
        self, session: Session, team_id: UUID, payload: TeamRivalryCreate
    ) -> TeamRivalry:
        profile = self.get_profile(session, team_id)
        rivalry = TeamRivalry(team_profile_id=team_id, **payload.model_dump())
        session.add(rivalry)
        profile.profile_version += 1
        self._commit(session)
        return rivalry

    def update_rivalry(
        self, session: Session, team_id: UUID, rivalry_id: UUID, payload: TeamRivalryUpdate
    ) -> TeamRivalry:
        rivalry = self._get_rivalry(session, team_id, rivalry_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rivalry, field, value)
        self.get_profile(session, team_id).profile_version += 1
        self._commit(session)
        return rivalry

    def delete_rivalry(self, session: Session, team_id: UUID, rivalry_id: UUID) -> None:
        rivalry = self._get_rivalry(session, team_id, rivalry_id)
        session.delete(rivalry)
        self.get_profile(session, team_id).profile_version += 1
        session.commit()

    def _get_rivalry(self, session: Session, team_id: UUID, rivalry_id: UUID) -> TeamRivalry:
        rivalry = session.get(TeamRivalry, rivalry_id)
        if rivalry is None or rivalry.team_profile_id != team_id:
            raise TeamProfileNotFoundError
        return rivalry

    @staticmethod
    def _commit(session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise DuplicateTeamProfileError from error
