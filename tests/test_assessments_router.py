"""
Testes smoke para os endpoints de assessments (app/routers/assessments.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: dependências e classificação mockadas; lógica de negócio é coberta em
test_assessment_service.py / testes de serviço.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.session import get_db
from app.main import app
from app.models.assessment import TipoAvaliacao

client = TestClient(app, raise_server_exceptions=False)

FAKE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
NEW_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
NEW_ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")

_ASSESSMENT_RESPONSE = SimpleNamespace(
    id_avaliacao=FAKE_ID,
    texto="Avaliação teste",
    tipo_avaliacao=TipoAvaliacao.POSITIVA,
    usuario_id=USER_ID,
    empresa_id=ENTERPRISE_ID,
)

_ASSESSMENTS_LIST = [
    SimpleNamespace(
        id_avaliacao=FAKE_ID,
        texto="Avaliação teste",
        tipo_avaliacao=TipoAvaliacao.POSITIVA,
        usuario_id=USER_ID,
        empresa_id=ENTERPRISE_ID,
    )
]


@pytest.fixture
def db_mock():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield db
    app.dependency_overrides.pop(get_db, None)


def test_given_assessments_exist_when_list_then_returns_200(db_mock):
    # GIVEN
    db_mock.scalars.return_value.all.return_value = _ASSESSMENTS_LIST

    # WHEN
    response = client.get("/assessments")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["texto"] == "Avaliação teste"
    assert data[0]["tipo_avaliacao"] == "positiva"


def test_given_assessment_exists_when_get_by_id_then_returns_200(db_mock):
    # GIVEN
    db_mock.get.return_value = _ASSESSMENT_RESPONSE

    # WHEN
    response = client.get(f"/assessments/{FAKE_ID}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["id_avaliacao"] == str(FAKE_ID)
    assert data["tipo_avaliacao"] == "positiva"


def test_given_valid_payload_when_create_then_returns_201(db_mock):
    # GIVEN
    db_mock.get.side_effect = [
        SimpleNamespace(id_usuario=USER_ID),  # usuário existe
        SimpleNamespace(id_empresa=ENTERPRISE_ID),  # empresa existe
    ]

    with patch(
        "app.routers.assessments.classify_assessment_text",
        return_value=TipoAvaliacao.POSITIVA,
    ):
        # WHEN
        response = client.post(
            "/assessments",
            json={
                "texto": "Muito bom!",
                "usuario_id": str(USER_ID),
                "empresa_id": str(ENTERPRISE_ID),
            },
        )

    # THEN
    assert response.status_code == 201
    data = response.json()
    assert data["texto"] == "Muito bom!"
    assert data["tipo_avaliacao"] == "positiva"
    assert data["usuario_id"] == str(USER_ID)
    assert data["empresa_id"] == str(ENTERPRISE_ID)
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()


def test_given_valid_payload_when_update_text_then_returns_200_and_reclassifies(db_mock):
    # GIVEN
    db_mock.get.return_value = _ASSESSMENT_RESPONSE

    with patch(
        "app.routers.assessments.classify_assessment_text",
        return_value=TipoAvaliacao.NEGATIVA,
    ):
        # WHEN
        response = client.put(
            f"/assessments/{FAKE_ID}",
            json={"texto": "Piorou bastante."},
        )

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["id_avaliacao"] == str(FAKE_ID)
    assert data["texto"] == "Piorou bastante."
    assert data["tipo_avaliacao"] == "negativa"
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()


def test_given_assessment_exists_when_delete_then_returns_204(db_mock):
    # GIVEN
    db_mock.get.return_value = _ASSESSMENT_RESPONSE

    # WHEN
    response = client.delete(f"/assessments/{FAKE_ID}")

    # THEN
    assert response.status_code == 204
    db_mock.delete.assert_called_once()
    db_mock.commit.assert_called_once()


def test_given_enterprise_exists_when_get_by_enterprise_then_returns_200(db_mock):
    # GIVEN
    db_mock.get.return_value = SimpleNamespace(id_empresa=ENTERPRISE_ID)
    db_mock.scalars.return_value.all.return_value = _ASSESSMENTS_LIST

    # WHEN
    response = client.get(f"/assessments/by-enterprise/{ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(ENTERPRISE_ID)
    assert data[0]["texto"] == "Avaliação teste"
