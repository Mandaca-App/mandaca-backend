"""
Testes unitários para contact_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session completamente mockada.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import ContactNotFoundError
from app.models.contact import Contact
from app.schemas.contacts import ContactCreate, ContactUpdate
from app.services import contact_service

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_CONTACT_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contact(**kwargs) -> Contact:
    c = Contact(
        id_contato=kwargs.get("id_contato", FAKE_CONTACT_ID),
        telefone=kwargs.get("telefone"),
        email=kwargs.get("email"),
        whatsapp=kwargs.get("whatsapp"),
    )
    return c


def _mock_db() -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result
    return db


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_existing_contact_when_get_by_id_then_returns_it():
    # GIVEN
    db = _mock_db()
    contact = _make_contact(telefone="81999999999")
    db.execute.return_value.scalar_one_or_none.return_value = contact

    # WHEN
    result = contact_service.get_by_id(FAKE_CONTACT_ID, db)

    # THEN
    assert result is contact


def test_given_missing_contact_when_get_by_id_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    # WHEN / THEN
    with pytest.raises(ContactNotFoundError):
        contact_service.get_by_id(FAKE_CONTACT_ID, db)


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_given_contacts_when_list_all_then_returns_list():
    # GIVEN
    db = _mock_db()
    contacts = [_make_contact(telefone="81999999999"), _make_contact(email="a@b.com")]
    db.execute.return_value.scalars.return_value.all.return_value = contacts

    # WHEN
    result = contact_service.list_all(db)

    # THEN
    assert len(result) == 2


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_create_then_persists():
    # GIVEN
    db = _mock_db()
    payload = ContactCreate(
        telefone="81999999999",
        email="contato@empresa.com",
        whatsapp="81999999999",
    )

    # WHEN
    contact_service.create(payload, db)

    # THEN
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Contact = db.add.call_args[0][0]
    assert added.telefone == "81999999999"
    assert added.email == "contato@empresa.com"
    assert added.whatsapp == "81999999999"


def test_given_partial_payload_when_create_then_persists_with_nones():
    # GIVEN
    db = _mock_db()
    payload = ContactCreate(email="so@email.com")

    # WHEN
    contact_service.create(payload, db)

    # THEN
    db.add.assert_called_once()
    added: Contact = db.add.call_args[0][0]
    assert added.email == "so@email.com"
    assert added.telefone is None
    assert added.whatsapp is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_given_new_email_when_update_then_changes_field():
    # GIVEN
    db = _mock_db()
    contact = _make_contact(email="velho@email.com")
    db.execute.return_value.scalar_one_or_none.return_value = contact
    payload = ContactUpdate(email="novo@email.com")

    # WHEN
    contact_service.update(FAKE_CONTACT_ID, payload, db)

    # THEN
    assert contact.email == "novo@email.com"
    db.commit.assert_called_once()


def test_given_missing_contact_when_update_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None
    payload = ContactUpdate(telefone="81988888888")

    # WHEN / THEN
    with pytest.raises(ContactNotFoundError):
        contact_service.update(FAKE_CONTACT_ID, payload, db)


def test_given_none_fields_in_payload_when_update_then_does_not_overwrite():
    # GIVEN
    db = _mock_db()
    contact = _make_contact(telefone="81999999999", email="original@email.com")
    db.execute.return_value.scalar_one_or_none.return_value = contact
    payload = ContactUpdate(whatsapp="81977777777")

    # WHEN
    contact_service.update(FAKE_CONTACT_ID, payload, db)

    # THEN
    assert contact.telefone == "81999999999"
    assert contact.email == "original@email.com"
    assert contact.whatsapp == "81977777777"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_given_existing_contact_when_delete_then_removes_from_db():
    # GIVEN
    db = _mock_db()
    contact = _make_contact()
    db.execute.return_value.scalar_one_or_none.return_value = contact

    # WHEN
    contact_service.delete(FAKE_CONTACT_ID, db)

    # THEN
    db.delete.assert_called_once_with(contact)
    db.commit.assert_called_once()


def test_given_missing_contact_when_delete_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    # WHEN / THEN
    with pytest.raises(ContactNotFoundError):
        contact_service.delete(FAKE_CONTACT_ID, db)

    db.delete.assert_not_called()
    db.commit.assert_not_called()
