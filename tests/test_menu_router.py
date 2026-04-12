"""
Testes smoke para os endpoints de menus (app/routers/menus.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: service completamente mockado; lógica de negócio é coberta em test_menu_service.py.
"""

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.session import get_db
from app.main import app
from app.models.menu import CategoriaCardapio

client = TestClient(app, raise_server_exceptions=False)

FAKE_MENU_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

_MENU_RESPONSE = SimpleNamespace(
    id_cardapio=FAKE_MENU_ID,
    descricao="Hambúrguer artesanal",
    historia="Receita da casa",
    preco=Decimal("25.50"),
    categoria=CategoriaCardapio.LANCHE,
    status=True,
    empresa_id=ENTERPRISE_ID,
)

_UPDATED_MENU_RESPONSE = SimpleNamespace(
    id_cardapio=FAKE_MENU_ID,
    descricao="Hambúrguer premium",
    historia="Receita melhorada",
    preco=Decimal("30.00"),
    categoria=CategoriaCardapio.LANCHE,
    status=True,
    empresa_id=ENTERPRISE_ID,
)

_MENUS_LIST = [_MENU_RESPONSE]


@pytest.fixture
def db_mock():
    def override_get_db():
        yield None  # não usamos o db diretamente aqui

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_given_menus_exist_when_list_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_all",
        return_value=_MENUS_LIST,
    ):
        response = client.get("/menus/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["descricao"] == "Hambúrguer artesanal"
    assert data[0]["categoria"] == "lanche"


def test_given_menu_exists_when_get_by_id_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.get_by_id",
        return_value=_MENU_RESPONSE,
    ):
        response = client.get(f"/menus/{FAKE_MENU_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["categoria"] == "lanche"


def test_given_valid_payload_when_create_then_returns_201(db_mock):
    with patch(
        "app.routers.menus.menu_service.create",
        return_value=_MENU_RESPONSE,
    ):
        response = client.post(
            "/menus/",
            json={
                "descricao": "Hambúrguer artesanal",
                "historia": "Receita da casa",
                "preco": 25.50,
                "categoria": "lanche",
                "status": True,
                "empresa_id": str(ENTERPRISE_ID),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["descricao"] == "Hambúrguer artesanal"
    assert data["categoria"] == "lanche"
    assert data["empresa_id"] == str(ENTERPRISE_ID)


def test_given_valid_payload_when_update_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.update",
        return_value=_UPDATED_MENU_RESPONSE,
    ):
        response = client.put(
            f"/menus/{FAKE_MENU_ID}",
            json={"descricao": "Hambúrguer premium"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["descricao"] == "Hambúrguer premium"
    assert data["categoria"] == "lanche"


def test_given_menu_exists_when_delete_then_returns_204(db_mock):
    with patch(
        "app.routers.menus.menu_service.delete",
        return_value=None,
    ):
        response = client.delete(f"/menus/{FAKE_MENU_ID}")

    assert response.status_code == 204


def test_given_enterprise_exists_when_get_by_enterprise_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.get_by_enterprise",
        return_value=_MENUS_LIST,
    ):
        response = client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(ENTERPRISE_ID)
    assert data[0]["descricao"] == "Hambúrguer artesanal"
