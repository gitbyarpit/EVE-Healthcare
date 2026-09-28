import os

# Must be set before any `app.*` module is imported, since app.core.config
# reads DATABASE_URL at import time and app.main connects on startup.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.main import app

# Disable rate-limiting during tests so rapid-fire test requests are
# never blocked.
limiter.enabled = False

# Use SQLite in-memory for fast, isolated tests instead of requiring a
# running Postgres instance.  UUID columns still work here because we
# store them as strings (see models.py: as_uuid=False).
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Signs up + logs in a user, returns Authorization headers."""
    client.post("/auth/signup", json={
        "email": "patient@example.com",
        "full_name": "Test Patient",
        "password": "supersecret123",
    })
    resp = client.post("/auth/login", json={
        "email": "patient@example.com",
        "password": "supersecret123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
