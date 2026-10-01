from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Competition, Fixture, TeamFixtureLink, TeamProfile
from app.providers.football.models import FootballFixture, ProviderDataError
from app.providers.football.registry import FootballProviderRegistry


@dataclass(frozen=True)
class SyncResult:
    team_profile_id: UUID
    created: int
    updated: int
    skipped: int
    warnings: list[str] = field(default_factory=list)


class MatchSyncService:
    """Persist provider-normalized fixtures without provider-specific business logic."""

    async def sync_team(
        self,
        session: Session,
        providers: FootballProviderRegistry,
        team_id: UUID,
        start: date,
        end: date,
    ) -> SyncResult:
        profile = self._get_team(session, team_id)
        if not profile.external_team_id:
            return SyncResult(
                team_profile_id=team_id,
                created=0,
                updated=0,
                skipped=0,
                warnings=["Team profile has no external_team_id configured"],
            )
        provider = providers.get(profile.football_provider)
        source_fixtures = await provider.get_fixtures(profile.external_team_id, start, end)
        created = updated = skipped = 0
        warnings: list[str] = []
        for source_fixture in source_fixtures:
            try:
                fixture, was_created = self._upsert_fixture(session, source_fixture)
                self._upsert_team_link(session, fixture, profile)
                created += int(was_created)
                updated += int(not was_created)
            except ProviderDataError as error:
                skipped += 1
                warnings.append(str(error))
        session.commit()
        return SyncResult(team_id, created, updated, skipped, warnings)

    async def refresh_fixture(
        self, session: Session, providers: FootballProviderRegistry, fixture_id: UUID
    ) -> Fixture:
        fixture = session.get(Fixture, fixture_id)
        if fixture is None:
            raise LookupError("Fixture not found")
        provider = providers.get(fixture.provider)
        source_fixture = await provider.get_fixture(fixture.external_fixture_id)
        refreshed, _ = self._upsert_fixture(session, source_fixture)
        session.commit()
        return refreshed

    def list_fixtures(
        self, session: Session, team_id: UUID | None = None, status: str | None = None
    ) -> list[Fixture]:
        statement = select(Fixture).order_by(Fixture.kickoff_at)
        if team_id is not None:
            statement = statement.join(TeamFixtureLink).where(
                TeamFixtureLink.team_profile_id == team_id
            )
        if status is not None:
            statement = statement.where(Fixture.status == status)
        return list(session.scalars(statement))

    @staticmethod
    def get_fixture(session: Session, fixture_id: UUID) -> Fixture:
        fixture = session.get(Fixture, fixture_id)
        if fixture is None:
            raise LookupError("Fixture not found")
        return fixture

    def _upsert_fixture(self, session: Session, source: FootballFixture) -> tuple[Fixture, bool]:
        fixture = session.scalar(
            select(Fixture).where(
                Fixture.provider == source.provider,
                Fixture.external_fixture_id == source.external_fixture_id,
            )
        )
        competition_id = self._upsert_competition(session, source)
        values = {
            "competition_id": competition_id,
            "season_id": source.season_id,
            "home_external_team_id": source.home_external_team_id,
            "away_external_team_id": source.away_external_team_id,
            "home_name": source.home_name,
            "away_name": source.away_name,
            "kickoff_at": source.kickoff_at,
            "status": source.status.value,
            "home_score": source.home_score,
            "away_score": source.away_score,
            "result_info": source.result_info,
            "last_provider_sync_at": datetime.now(UTC),
            "raw_payload": source.raw_payload,
        }
        if fixture is None:
            fixture = Fixture(
                provider=source.provider,
                external_fixture_id=source.external_fixture_id,
                **values,
            )
            session.add(fixture)
            session.flush()
            return fixture, True
        for field_name, value in values.items():
            setattr(fixture, field_name, value)
        return fixture, False

    @staticmethod
    def _upsert_competition(session: Session, source: FootballFixture) -> UUID | None:
        if not source.competition_external_id:
            return None
        competition = session.scalar(
            select(Competition).where(
                Competition.provider == source.provider,
                Competition.external_competition_id == source.competition_external_id,
            )
        )
        if competition is None:
            competition = Competition(
                provider=source.provider,
                external_competition_id=source.competition_external_id,
                name=source.competition_name or source.competition_external_id,
                country=source.competition_country,
            )
            session.add(competition)
            session.flush()
        elif source.competition_name:
            competition.name = source.competition_name
            competition.country = source.competition_country
        return competition.id

    @staticmethod
    def _upsert_team_link(session: Session, fixture: Fixture, profile: TeamProfile) -> None:
        if profile.external_team_id == fixture.home_external_team_id:
            team_side = "home"
        elif profile.external_team_id == fixture.away_external_team_id:
            team_side = "away"
        else:
            raise ProviderDataError("Fixture does not contain the synchronized team")
        link = session.get(
            TeamFixtureLink,
            {"fixture_id": fixture.id, "team_profile_id": profile.id},
        )
        if link is None:
            session.add(
                TeamFixtureLink(
                    fixture_id=fixture.id,
                    team_profile_id=profile.id,
                    team_side=team_side,
                )
            )
        else:
            link.team_side = team_side

    @staticmethod
    def _get_team(session: Session, team_id: UUID) -> TeamProfile:
        profile = session.get(TeamProfile, team_id)
        if profile is None:
            raise LookupError("Team profile not found")
        return profile
