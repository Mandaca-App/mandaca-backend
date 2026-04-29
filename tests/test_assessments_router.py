"""
Testes smoke para os endpoints de assessments (app/routers/assessments.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: service completamente mockado; lógica de negócio é coberta em
test_assessment_service.py.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.session import get_db
from app.main import app
from app.models.assessment import TipoAvaliacao

client = TestClient(app, raise_server_exceptions=False)

FAKE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

_NOW = datetime.now(timezone.utc)

_ASSESSMENT_RESPONSE = SimpleNamespace(
    id_avaliacao=FAKE_ID,
    texto="Avaliação teste",
    tipo_avaliacao=TipoAvaliacao.POSITIVA,
    usuario_id=USER_ID,
    empresa_id=ENTERPRISE_ID,
    created_at=_NOW,
)

_UPDATED_ASSESSMENT_RESPONSE = SimpleNamespace(
    id_avaliacao=FAKE_ID,
    texto="Piorou bastante.",
    tipo_avaliacao=TipoAvaliacao.NEGATIVA,
    usuario_id=USER_ID,
    empresa_id=ENTERPRISE_ID,
    created_at=_NOW,
)

_ASSESSMENTS_LIST = [
    SimpleNamespace(
        id_avaliacao=FAKE_ID,
        texto="Avaliação teste",
        tipo_avaliacao=TipoAvaliacao.POSITIVA,
        usuario_id=USER_ID,
        empresa_id=ENTERPRISE_ID,
        created_at=_NOW,
    )
]


@pytest.fixture
def db_mock():
    def override_get_db():
        yield None  # não usamos o db diretamente aqui

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_given_assessments_exist_when_list_then_returns_200(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.list_all",
        return_value=_ASSESSMENTS_LIST,
    ):
        response = client.get("/assessments")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["texto"] == "Avaliação teste"
    assert data[0]["tipo_avaliacao"] == "positiva"
    assert "created_at" in data[0]


def test_given_assessment_exists_when_get_by_id_then_returns_200(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.get_by_id",
        return_value=_ASSESSMENT_RESPONSE,
    ):
        response = client.get(f"/assessments/{FAKE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id_avaliacao"] == str(FAKE_ID)
    assert data["tipo_avaliacao"] == "positiva"
    assert "created_at" in data


def test_given_valid_payload_when_create_then_returns_201(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.create",
        return_value=_ASSESSMENT_RESPONSE,
    ):
        response = client.post(
            "/assessments",
            json={
                "texto": "Muito bom!",
                "usuario_id": str(USER_ID),
                "empresa_id": str(ENTERPRISE_ID),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id_avaliacao"] == str(FAKE_ID)
    assert data["texto"] == "Avaliação teste"
    assert data["tipo_avaliacao"] == "positiva"
    assert data["usuario_id"] == str(USER_ID)
    assert data["empresa_id"] == str(ENTERPRISE_ID)
    assert "created_at" in data


def test_given_valid_payload_when_update_text_then_returns_200(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.update",
        return_value=_UPDATED_ASSESSMENT_RESPONSE,
    ):
        response = client.put(
            f"/assessments/{FAKE_ID}",
            json={"texto": "Piorou bastante."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id_avaliacao"] == str(FAKE_ID)
    assert data["texto"] == "Piorou bastante."
    assert data["tipo_avaliacao"] == "negativa"
    assert "created_at" in data


def test_given_assessment_exists_when_delete_then_returns_204(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.delete",
        return_value=None,
    ):
        response = client.delete(f"/assessments/{FAKE_ID}")

    assert response.status_code == 204


def test_given_enterprise_exists_when_get_by_enterprise_then_returns_200(db_mock):
    with patch(
        "app.routers.assessments.assessment_service.list_by_enterprise",
        return_value=_ASSESSMENTS_LIST,
    ):
        response = client.get(f"/assessments/by-enterprise/{ENTERPRISE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(ENTERPRISE_ID)
    assert data[0]["texto"] == "Avaliação teste"
    assert "created_at" in data[0]
