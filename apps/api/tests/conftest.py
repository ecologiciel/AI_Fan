from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.domain.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db_session
from app.domain.models import User
from app.main import app
from app.services.auth import hash_password


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client: TestClient, session: Session) -> TestClient:
    user = User(email="admin@example.com", password_hash=hash_password("secure-password"))
    session.add(user)
    session.commit()
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "secure-password"}
    )
    assert response.status_code == 200
    return client
