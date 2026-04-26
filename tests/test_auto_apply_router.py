import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    EnterpriseNotFoundError,
    FieldNotAllowedError,
    InvalidFieldValueError,
)
from app.main import app
from app.routers.auto_apply import get_auto_apply_service
from app.schemas.auto_apply import AutoApplyResponse, SuggestionStatus

FAKE_ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_client(mock_service: MagicMock) -> TestClient:
    app.dependency_overrides[get_auto_apply_service] = lambda: mock_service
    return TestClient(app, raise_server_exceptions=False)


def test_given_valid_payload_when_auto_apply_then_returns_200():
    # GIVEN
    mock_service = MagicMock()
    mock_service.apply.return_value = AutoApplyResponse(
        campo_alterado="historia",
        status=SuggestionStatus.APPLIED,
    )
    client = _make_client(mock_service)

    # WHEN
    response = client.post(
        "/auto-apply",
        json={
            "enterprise_id": str(FAKE_ENTERPRISE_ID),
            "target": "enterprise",
            "campo_para_alterar": "historia",
            "novo_valor": "Nova historia",
        },
    )

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["campo_alterado"] == "historia"
    assert body["status"] == "aplicado"


def test_given_missing_enterprise_when_auto_apply_then_returns_404():
    # GIVEN
    mock_service = MagicMock()
    mock_service.apply.side_effect = EnterpriseNotFoundError(FAKE_ENTERPRISE_ID)
    client = _make_client(mock_service)

    # WHEN
    response = client.post(
        "/auto-apply",
        json={
            "enterprise_id": str(FAKE_ENTERPRISE_ID),
            "target": "enterprise",
            "campo_para_alterar": "historia",
            "novo_valor": "x",
        },
    )

    # THEN
    assert response.status_code == 404


def test_given_forbidden_field_when_auto_apply_then_returns_422():
    # GIVEN
    mock_service = MagicMock()
    mock_service.apply.side_effect = FieldNotAllowedError("owner_id")
    client = _make_client(mock_service)

    # WHEN
    response = client.post(
        "/auto-apply",
        json={
            "enterprise_id": str(FAKE_ENTERPRISE_ID),
            "target": "enterprise",
            "campo_para_alterar": "owner_id",
            "novo_valor": "x",
        },
    )

    # THEN
    assert response.status_code == 422


def test_given_invalid_value_when_auto_apply_then_returns_422():
    # GIVEN
    mock_service = MagicMock()
    mock_service.apply.side_effect = InvalidFieldValueError("preco", "invalido")
    client = _make_client(mock_service)

    # WHEN
    response = client.post(
        "/auto-apply",
        json={
            "enterprise_id": str(FAKE_ENTERPRISE_ID),
            "target": "menu_item",
            "menu_item_id": str(uuid.uuid4()),
            "campo_para_alterar": "preco",
            "novo_valor": "abc",
        },
    )

    # THEN
    assert response.status_code == 422


def test_given_invalid_json_when_auto_apply_then_returns_422():
    # WHEN
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/auto-apply", json={"enterprise_id": "not-a-uuid"})

    # THEN
    assert response.status_code == 422
