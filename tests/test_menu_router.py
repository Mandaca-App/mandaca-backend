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

# url_foto_item incluído para refletir o campo adicionado ao MenuResponse
_MENU_RESPONSE = SimpleNamespace(
    id_cardapio=FAKE_MENU_ID,
    descricao="Hambúrguer artesanal",
    historia="Receita da casa",
    preco=Decimal("25.50"),
    categoria=CategoriaCardapio.LANCHE,
    status=True,
    empresa_id=ENTERPRISE_ID,
    url_foto_item=None,
)

_UPDATED_MENU_RESPONSE = SimpleNamespace(
    id_cardapio=FAKE_MENU_ID,
    descricao="Hambúrguer premium",
    historia="Receita melhorada",
    preco=Decimal("30.00"),
    categoria=CategoriaCardapio.LANCHE,
    status=True,
    empresa_id=ENTERPRISE_ID,
    url_foto_item=None,
)

_MENU_RESPONSE_WITH_FOTO = SimpleNamespace(
    id_cardapio=FAKE_MENU_ID,
    descricao="Hambúrguer artesanal",
    historia="Receita da casa",
    preco=Decimal("25.50"),
    categoria=CategoriaCardapio.LANCHE,
    status=True,
    empresa_id=ENTERPRISE_ID,
    url_foto_item="https://mock-url.com/storage/v1/object/public/mandaca-bucket/cardapios/foto.jpg",
)

_MENUS_LIST = [_MENU_RESPONSE]

_PAGINATED_RESPONSE = {
    "page": 1,
    "items": [_MENU_RESPONSE],
    "has_more": False,
}

_PAGINATED_RESPONSE_WITH_MORE = {
    "page": 1,
    "items": [_MENU_RESPONSE],
    "has_more": True,
}


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
    """
    POST /menus/ com payload via Depends() (Pydantic model).
    FastAPI trata cada campo do modelo como query parameter, por isso usa params={}.
    O arquivo foto é opcional e não é enviado neste teste.
    """
    with patch(
        "app.routers.menus.menu_service.create",
        return_value=_MENU_RESPONSE,
    ):
        response = client.post(
            "/menus/",
            params={
                "descricao": "Hambúrguer artesanal",
                "historia": "Receita da casa",
                "preco": "25.50",
                "categoria": "lanche",
                "status": "true",
                "empresa_id": str(ENTERPRISE_ID),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["descricao"] == "Hambúrguer artesanal"
    assert data["categoria"] == "lanche"
    assert data["empresa_id"] == str(ENTERPRISE_ID)


def test_given_valid_payload_with_foto_when_create_then_returns_201(db_mock):
    """
    POST /menus/ com envio de imagem.
    Payload via params={} (query params do Depends()) + arquivo via files={}.
    """
    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # bytes que simulam uma imagem PNG

    with patch(
        "app.routers.menus.menu_service.create",
        return_value=_MENU_RESPONSE_WITH_FOTO,
    ):
        response = client.post(
            "/menus/",
            params={
                "descricao": "Hambúrguer artesanal",
                "historia": "Receita da casa",
                "preco": "25.50",
                "categoria": "lanche",
                "status": "true",
                "empresa_id": str(ENTERPRISE_ID),
            },
            files={"foto": ("foto.png", fake_image, "image/png")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["url_foto_item"] is not None


def test_given_valid_payload_when_update_then_returns_200(db_mock):
    """
    PUT /menus/{id} com payload via Depends() (Pydantic model).
    FastAPI trata cada campo do modelo como query parameter, por isso usa params={}.
    """
    with patch(
        "app.routers.menus.menu_service.update",
        return_value=_UPDATED_MENU_RESPONSE,
    ):
        response = client.put(
            f"/menus/{FAKE_MENU_ID}",
            params={"descricao": "Hambúrguer premium"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id_cardapio"] == str(FAKE_MENU_ID)
    assert data["descricao"] == "Hambúrguer premium"
    assert data["categoria"] == "lanche"


def test_given_valid_payload_with_foto_when_update_then_returns_200(db_mock):
    """
    PUT /menus/{id} com substituição de imagem.
    Payload via params={} (query params do Depends()) + arquivo via files={}.
    """
    fake_image = b"\xff\xd8\xff" + b"\x00" * 100  # bytes que simulam um JPEG

    with patch(
        "app.routers.menus.menu_service.update",
        return_value=_MENU_RESPONSE_WITH_FOTO,
    ):
        response = client.put(
            f"/menus/{FAKE_MENU_ID}",
            params={"descricao": "Hambúrguer premium"},
            files={"foto": ("nova_foto.jpg", fake_image, "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["url_foto_item"] is not None


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


def test_given_create_with_foto_when_valid_image_then_returns_201(db_mock):
    with patch(
        "app.routers.menus.menu_service.create",
        return_value=_MENU_RESPONSE,
    ):
        response = client.post(
            "/menus/",
            params={
                "descricao": "Hambúrguer artesanal",
                "preco": "25.50",
                "categoria": "lanche",
                "status": "true",
                "empresa_id": str(ENTERPRISE_ID),
            },
            files={"foto": ("burger.jpg", b"fakeimagebytes", "image/jpeg")},
        )

    assert response.status_code == 201


def test_given_update_with_foto_when_valid_image_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.update",
        return_value=_UPDATED_MENU_RESPONSE,
    ):
        response = client.put(
            f"/menus/{FAKE_MENU_ID}",
            params={"descricao": "Hambúrguer premium"},
            files={"foto": ("burger.jpg", b"fakeimagebytes", "image/jpeg")},
        )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# list_menus_by_enterprise_paginated
# ---------------------------------------------------------------------------


def test_given_enterprise_exists_when_paginated_then_returns_200(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_by_enterprise_paginated",
        return_value=_PAGINATED_RESPONSE,
    ):
        response = client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["has_more"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["empresa_id"] == str(ENTERPRISE_ID)


def test_given_page_param_when_paginated_then_passes_it_to_service(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_by_enterprise_paginated",
        return_value=_PAGINATED_RESPONSE,
    ) as mock_service:
        client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated?page=3")

    mock_service.assert_called_once()
    _, call_page, _, _ = mock_service.call_args[0]
    assert call_page == 3


def test_given_categoria_param_when_paginated_then_passes_it_to_service(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_by_enterprise_paginated",
        return_value=_PAGINATED_RESPONSE,
    ) as mock_service:
        client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated?categoria=lanche")

    mock_service.assert_called_once()
    _, _, call_categoria, _ = mock_service.call_args[0]
    assert call_categoria == CategoriaCardapio.LANCHE


def test_given_no_categoria_param_when_paginated_then_passes_none_to_service(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_by_enterprise_paginated",
        return_value=_PAGINATED_RESPONSE,
    ) as mock_service:
        client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated")

    mock_service.assert_called_once()
    _, _, call_categoria, _ = mock_service.call_args[0]
    assert call_categoria is None


def test_given_has_more_true_when_paginated_then_reflects_in_response(db_mock):
    with patch(
        "app.routers.menus.menu_service.list_by_enterprise_paginated",
        return_value=_PAGINATED_RESPONSE_WITH_MORE,
    ):
        response = client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated")

    assert response.status_code == 200
    assert response.json()["has_more"] is True


def test_given_page_zero_when_paginated_then_returns_422(db_mock):
    response = client.get(f"/menus/by-enterprise/{ENTERPRISE_ID}/paginated?page=0")
    assert response.status_code == 422
