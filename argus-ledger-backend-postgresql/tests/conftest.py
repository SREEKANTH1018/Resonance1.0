"""Pytest fixtures.

The suite runs against a real PostgreSQL database (``TEST_DATABASE_URL``, default
``.../argus_test``) — the ORM uses PostgreSQL-specific types, so there is no
SQLite fallback. ``scripts/setup_db.ps1`` creates the ``argus_test`` database;
this module owns its schema (create/drop per session) and rolls back every test.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", get_settings().test_database_url)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(bind=eng)
        eng.dispose()


@pytest.fixture()
def db(engine) -> Session:
    """A session wrapped in an outer transaction that is rolled back per test."""
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, future=True)()

    # Keep the SAVEPOINT alive across the service-layer commit()s.
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_payload() -> dict:
    return {
        "input_text": "Customer application: eligibility satisfied; risk below threshold.",
        "decision": "APPROVED",
        "confidence": 0.91,
        "reasons": ["Eligibility satisfied", "Risk below threshold"],
        "evidence": [
            {
                "source": "policy.pdf",
                "page": 4,
                "content": "Eligibility requirements are satisfied.",
                "relevance": 0.96,
                "reason": "Eligibility requirement",
            }
        ],
        "model": "Model-A",
        "model_version": "1.2",
        "policy_name": "Policy-01",
        "policy_version": "3.1",
        "human_review_required": False,
        "resource": {
            "latency_ms": 720,
            "tokens": 1820,
            "energy_wh": 0.02,
            "carbon_g": 0.01,
        },
    }
