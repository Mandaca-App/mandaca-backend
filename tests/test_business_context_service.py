"""
Testes unitários para business_context_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session completamente mockada.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    BusinessContextNotFoundError,
    EnterpriseNotFoundError,
    InvalidContextDataError,
)
from app.models.business_context import BusinessContext
from app.models.enterprise import Enterprise
from app.schemas.business_contexts import BusinessContextCreate, BusinessContextUpdate
from app.services import business_context_service

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_CONTEXT_ID = uuid.uuid4()
FAKE_ENTERPRISE_ID = uuid.uuid4()

FAKE_DADOS = {
    "nome": "Restaurante Teste",
    "especialidade": "Nordestina",
    "cardapio": [{"categoria": "prato_principal", "descricao": "Baião de dois", "preco": "35.00"}],
}

# dados_contexto para Create ainda é string (service chama _parse_dados internamente)
FAKE_DADOS_STR = (
    '{"nome": "Restaurante Teste", "especialidade": "Nordestina",'
    ' "cardapio": [{"categoria": "prato_principal", '
    '"descricao": "Baião de dois", "preco": "35.00"}]}'
)

FAKE_HASH = "a" * 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**kwargs) -> BusinessContext:
    ctx = BusinessContext(
        id_contexto=kwargs.get("id_contexto", FAKE_CONTEXT_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_ENTERPRISE_ID),
        hash_contexto=kwargs.get("hash_contexto", FAKE_HASH),
        dados_contexto=kwargs.get("dados_contexto", FAKE_DADOS),
        criado_em=kwargs.get("criado_em", datetime.now(timezone.utc)),
    )
    return ctx


def _make_enterprise(**kwargs) -> Enterprise:
    e = Enterprise(
        id_empresa=kwargs.get("id_empresa", FAKE_ENTERPRISE_ID),
        nome=kwargs.get("nome", "Empresa Teste"),
        especialidade=None,
        endereco=None,
        historia=None,
        hora_abrir=None,
        hora_fechar=None,
        telefone=None,
        latitude=None,
        longitude=None,
        usuario_id=uuid.uuid4(),
        deleted_at=None,
    )
    e.fotos = []
    e.cardapios = []
    e.reservas = []
    e.avaliacoes = []
    return e


def _mock_db() -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result
    db.get.return_value = None
    return db


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_existing_context_when_get_by_id_then_returns_it():
    # GIVEN
    db = _mock_db()
    context = _make_context()
    db.get.return_value = context

    # WHEN
    result = business_context_service.get_by_id(FAKE_CONTEXT_ID, db)

    # THEN
    assert result is context


def test_given_missing_context_when_get_by_id_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(BusinessContextNotFoundError):
        business_context_service.get_by_id(FAKE_CONTEXT_ID, db)


# ---------------------------------------------------------------------------
# list_by_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_list_by_enterprise_then_returns_contexts():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    contexts = [_make_context(), _make_context(id_contexto=uuid.uuid4())]
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = contexts

    # WHEN
    result = business_context_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert len(result) == 2


def test_given_existing_enterprise_with_no_contexts_when_list_then_returns_empty():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_enterprise()
    db.execute.return_value.scalars.return_value.all.return_value = []

    # WHEN
    result = business_context_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result == []


def test_given_missing_enterprise_when_list_by_enterprise_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        business_context_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)


# ---------------------------------------------------------------------------
# create_from_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_create_from_enterprise_then_persists_snapshot():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_enterprise()
    fake_snapshot = {"nome": "Empresa Teste", "cardapio": []}

    with patch(
        "app.services.business_context_service.BusinessContextBuilderService.build_snapshot",
        return_value=fake_snapshot,
    ):
        # WHEN
        business_context_service.create_from_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: BusinessContext = db.add.call_args[0][0]
    assert added.dados_contexto == fake_snapshot
    assert added.empresa_id == FAKE_ENTERPRISE_ID


def test_given_existing_enterprise_when_create_from_enterprise_then_computes_hash():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_enterprise()

    with patch(
        "app.services.business_context_service.BusinessContextBuilderService.build_snapshot",
        return_value={"nome": "Empresa Teste"},
    ):
        # WHEN
        business_context_service.create_from_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    added: BusinessContext = db.add.call_args[0][0]
    assert len(added.hash_contexto) == 64


def test_given_missing_enterprise_when_create_from_enterprise_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        business_context_service.create_from_enterprise(FAKE_ENTERPRISE_ID, db)


def test_given_missing_enterprise_when_create_from_enterprise_then_does_not_call_builder():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    with patch(
        "app.services.business_context_service.BusinessContextBuilderService.build_snapshot",
    ) as mock_builder:
        # WHEN / THEN
        with pytest.raises(EnterpriseNotFoundError):
            business_context_service.create_from_enterprise(FAKE_ENTERPRISE_ID, db)

    mock_builder.assert_not_called()


# ---------------------------------------------------------------------------
# update  (dados_contexto chega como dict — sem _parse_dados)
# ---------------------------------------------------------------------------


def test_given_new_dados_when_update_then_persists_them():
    # GIVEN
    db = _mock_db()
    context = _make_context(dados_contexto={"nome": "Antigo"})
    novos_dados = {"nome": "Atualizado", "especialidade": "Japonesa"}
    payload = BusinessContextUpdate(dados_contexto=novos_dados)

    with patch("app.services.business_context_service.get_by_id", return_value=context):
        # WHEN
        business_context_service.update(FAKE_CONTEXT_ID, payload, db)

    # THEN
    assert context.dados_contexto == novos_dados
    db.commit.assert_called_once()


def test_given_new_dados_when_update_then_recalculates_hash():
    # GIVEN
    db = _mock_db()
    old_hash = "b" * 64
    context = _make_context(hash_contexto=old_hash)
    payload = BusinessContextUpdate(dados_contexto={"nome": "Diferente"})

    with patch("app.services.business_context_service.get_by_id", return_value=context):
        # WHEN
        business_context_service.update(FAKE_CONTEXT_ID, payload, db)

    # THEN
    assert context.hash_contexto != old_hash
    assert len(context.hash_contexto) == 64


def test_given_empty_payload_when_update_then_does_not_change_context():
    # GIVEN
    db = _mock_db()
    original_dados = {"nome": "Inalterado"}
    original_hash = "c" * 64
    context = _make_context(dados_contexto=original_dados, hash_contexto=original_hash)
    payload = BusinessContextUpdate()

    with patch("app.services.business_context_service.get_by_id", return_value=context):
        # WHEN
        business_context_service.update(FAKE_CONTEXT_ID, payload, db)

    # THEN
    assert context.dados_contexto == original_dados
    assert context.hash_contexto == original_hash
    db.commit.assert_called_once()


def test_given_missing_context_when_update_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    payload = BusinessContextUpdate(dados_contexto={"nome": "X"})

    with patch(
        "app.services.business_context_service.get_by_id",
        side_effect=BusinessContextNotFoundError(FAKE_CONTEXT_ID),
    ):
        # WHEN / THEN
        with pytest.raises(BusinessContextNotFoundError):
            business_context_service.update(FAKE_CONTEXT_ID, payload, db)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_given_existing_context_when_delete_then_removes_it():
    # GIVEN
    db = _mock_db()
    context = _make_context()

    with patch("app.services.business_context_service.get_by_id", return_value=context):
        # WHEN
        business_context_service.delete(FAKE_CONTEXT_ID, db)

    # THEN
    db.delete.assert_called_once_with(context)
    db.commit.assert_called_once()


def test_given_missing_context_when_delete_then_raises_not_found():
    # GIVEN
    db = _mock_db()

    with patch(
        "app.services.business_context_service.get_by_id",
        side_effect=BusinessContextNotFoundError(FAKE_CONTEXT_ID),
    ):
        # WHEN / THEN
        with pytest.raises(BusinessContextNotFoundError):
            business_context_service.delete(FAKE_CONTEXT_ID, db)


def test_given_missing_context_when_delete_then_does_not_commit():
    # GIVEN
    db = _mock_db()

    with patch(
        "app.services.business_context_service.get_by_id",
        side_effect=BusinessContextNotFoundError(FAKE_CONTEXT_ID),
    ):
        # WHEN / THEN
        with pytest.raises(BusinessContextNotFoundError):
            business_context_service.delete(FAKE_CONTEXT_ID, db)

    db.commit.assert_not_called()
