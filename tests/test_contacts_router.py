"""
Testes smoke para os endpoints de contacts (app/routers/contacts.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: services completamente mockados; lógica de negócio é coberta em
test_contact_service.py.
"""

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.contacts import ContactResponse

client = TestClient(app, raise_server_exceptions=False)

FAKE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_CONTACT_RESPONSE = ContactResponse(
    id_contato=FAKE_ID,
    telefone="81999999999",
    email="contato@empresa.com",
    whatsapp="81999999999",
)


def test_given_contacts_exist_when_list_then_returns_200():
    # GIVEN
    with patch(
        "app.services.contact_service.list_all",
        return_value=[_CONTACT_RESPONSE],
    ):
        # WHEN
        response = client.get("/contacts/")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "contato@empresa.com"


def test_given_contact_exists_when_get_then_returns_200():
    # GIVEN
    with patch(
        "app.services.contact_service.get_by_id",
        return_value=_CONTACT_RESPONSE,
    ):
        # WHEN
        response = client.get(f"/contacts/{FAKE_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json()["id_contato"] == str(FAKE_ID)


def test_given_valid_payload_when_create_then_returns_201():
    # GIVEN
    with patch(
        "app.services.contact_service.create",
        return_value=_CONTACT_RESPONSE,
    ):
        # WHEN
        response = client.post(
            "/contacts/",
            json={
                "telefone": "81999999999",
                "email": "contato@empresa.com",
                "whatsapp": "81999999999",
            },
        )

    # THEN
    assert response.status_code == 201
    assert response.json()["id_contato"] == str(FAKE_ID)


def test_given_valid_payload_when_update_then_returns_200():
    # GIVEN
    with patch(
        "app.services.contact_service.update",
        return_value=_CONTACT_RESPONSE,
    ):
        # WHEN
        response = client.put(
            f"/contacts/{FAKE_ID}",
            json={"email": "novo@empresa.com"},
        )

    # THEN
    assert response.status_code == 200
    assert response.json()["id_contato"] == str(FAKE_ID)


def test_given_contact_exists_when_delete_then_returns_204():
    # GIVEN
    with patch(
        "app.services.contact_service.delete",
        return_value=None,
    ):
        # WHEN
        response = client.delete(f"/contacts/{FAKE_ID}")

    # THEN
    assert response.status_code == 204
