import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SUPABASE_URL"] = "http://mock-url.com"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-key"
os.environ["GROQ_API_KEY"] = "mock-groq-key"
os.environ["GOOGLE_MAPS_API_KEY"] = "mock-google-maps-key"
os.environ["APP_ENV"] = "testing"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.session import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(db):
    return TestClient(app)
