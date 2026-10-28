"""Pruebas del primer contrato: roles, eventos, consistencia y no duplicidad."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cycletracking.app import create_app
from cycletracking.models import Base, User
from cycletracking.security import hash_password


@pytest.fixture
def clients(tmp_path):
    url = "sqlite+pysqlite:///" + str(tmp_path / "test.sqlite")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for role in ("OPERATIVO", "INVENTARIOS", "ADMIN"):
            db.add(User(username=role.lower(), role=role, password_hash=hash_password("TestingOnly123!")))
        db.commit()
    with TestClient(create_app(url)) as client:
        def login(role):
            response = client.post("/api/v1/auth/login", json={"username": role.lower(), "password": "TestingOnly123!"})
            assert response.status_code == 200
            return {"Authorization": "Bearer " + response.json()["access_token"]}
        yield client, login
    engine.dispose()


def new_asset(client, inv):
    r = client.post("/api/v1/assets", headers=inv, json={
        "equipment_type": "NODE", "technology": "SERCEL",
        "identifier_kind": "SERIAL", "identifier": "25801",
    })
    assert r.status_code == 201, r.text
    return r.json()


def event_data(event_id=None):
    return {
        "event_id": str(event_id or uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "note": "Reportado por el responsable, pendiente de confrontación.",
        "event_type": "MISSING_REPORTED",
    }


def test_permissions_events_idempotency_and_history(clients):
    client, login = clients
    op, inv, admin = login("OPERATIVO"), login("INVENTARIOS"), login("ADMIN")
    assert client.get("/api/v1/assets").status_code == 401
    assert client.post("/api/v1/assets", headers=op, json={
        "equipment_type": "NODE", "identifier": "25801",
    }).status_code == 403
    assert client.post("/api/v1/assets", headers=admin, json={
        "equipment_type": "NODE", "identifier": "25801",
    }).status_code == 403  # administración técnica no suplanta Inventarios
    a = new_asset(client, inv)
    assert a["status"] == "REGISTERED" and a["version"] == 1
    assert client.get("/api/v1/assets?q=25801", headers=op).json()[0]["id"] == a["id"]
    obs = event_data()
    url = f'/api/v1/assets/{a["id"]}/observations'
    first = client.post(url, headers=op, json=obs)
    assert first.status_code == 200, first.text
    assert first.json()["replayed"] is False
    replay = client.post(url, headers=op, json=obs)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    conflicting = {**obs, "note": "Otra descripción para el mismo UUID."}
    assert client.post(url, headers=op, json=conflicting).status_code == 409
    details = client.get(f'/api/v1/assets/{a["id"]}', headers=inv).json()
    assert details["asset"]["status"] == "REGISTERED"  # reportar NO confirma pérdida
    assert len(details["events"]) == 2  # alta + observación, no duplicación
    decision_url = f'/api/v1/assets/{a["id"]}/decisions'
    decision = {
        "event_id": str(uuid4()), "occurred_at": datetime.now(timezone.utc).isoformat(),
        "new_status": "MISSING", "expected_version": 1,
        "note": "Inventarios confirma el estado por evidencia de revisión.",
    }
    assert client.post(decision_url, headers=op, json=decision).status_code == 403
    assert client.post(decision_url, headers=inv, json=decision).status_code == 409
    decision["expected_version"] = 2
    assert client.post(decision_url, headers=inv, json=decision).status_code == 200
    assert client.post(decision_url, headers=inv, json=decision).json()["replayed"] is True
    after = client.get(f'/api/v1/assets/{a["id"]}', headers=op).json()
    assert after["asset"]["status"] == "MISSING"
    assert after["asset"]["version"] == 3
    assert len(after["events"]) == 3
    found = {**event_data(), "event_type": "FOUND_REPORTED"}
    assert client.post(url, headers=op, json=found).status_code == 200
    assert client.get(f'/api/v1/assets/{a["id"]}', headers=op).json()["asset"]["status"] == "MISSING"


def test_duplicate_identifier_case_insensitive(clients):
    client, login = clients
    inv = login("INVENTARIOS")
    new_asset(client, inv)
    duplicate = client.post("/api/v1/assets", headers=inv, json={
        "equipment_type": "NODE", "identifier_kind": "SERIAL", "identifier": " 25801 ",
    })
    assert duplicate.status_code == 409


def test_i18n_and_auth(clients):
    client, login = clients
    dictionaries = []
    for language in ("es-MX", "en", "zh-CN"):
        response = client.get("/api/v1/i18n/" + language)
        assert response.status_code == 200
        dictionaries.append(set(response.json()))
    assert dictionaries[0] == dictionaries[1] == dictionaries[2]
    assert client.get("/api/v1/i18n/fr").status_code == 404
    assert client.post("/api/v1/auth/login", json={"username":"inventarios", "password":"wrong"}).status_code == 401
    inv = login("INVENTARIOS")
    assert client.get("/api/v1/me", headers=inv).json()["role"] == "INVENTARIOS"
    assert client.post("/api/v1/auth/logout", headers=inv).status_code == 200
    assert client.get("/api/v1/me", headers=inv).status_code == 401
    assert client.get("/").status_code == 200
    assert client.get("/").headers["x-content-type-options"] == "nosniff"
