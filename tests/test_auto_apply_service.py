"""
Testes unitários para AutoApplyService.

Foco: validação de whitelist, mapeamento campo lógico → coluna real,
parsing de horário e tratamento de erros do banco.
Session do SQLAlchemy completamente mockada — sem banco real.
"""

import uuid
from datetime import time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    AutoApplyPersistenceError,
    EnterpriseNotFoundError,
    FieldNotAllowedError,
    InvalidFieldValueError,
    MenuNotFoundError,
)
from app.models.enterprise import Enterprise
from app.models.menu import CategoriaCardapio, Menu
from app.schemas.auto_apply import AutoApplyRequest, AutoApplyTarget
from app.services.auto_apply_service import AutoApplyService

FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_MENU_ID = uuid.uuid4()


def _make_enterprise() -> Enterprise:
    return Enterprise(
        id_empresa=FAKE_ENTERPRISE_ID,
        nome="Empresa Teste",
        usuario_id=uuid.uuid4(),
    )


def _make_menu() -> Menu:
    return Menu(
        id_cardapio=FAKE_MENU_ID,
        descricao="Item teste",
        historia=None,
        preco=Decimal("10.00"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )


def _mock_db_with(record) -> MagicMock:
    db = MagicMock()
    db.get.return_value = record
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = record
    db.execute.return_value = execute_result
    return db


# ---------------------------------------------------------------------------
# Enterprise
# ---------------------------------------------------------------------------


def test_given_valid_historia_when_applied_then_updates_enterprise() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="historia",
        novo_valor="Nova história",
    )

    # WHEN
    response = AutoApplyService().apply(payload, db)

    # THEN
    assert enterprise.historia == "Nova história"
    assert response.campo_alterado == "historia"
    assert response.status == "aplicado"
    db.commit.assert_called_once()


def test_given_commit_false_when_applied_then_skips_commit() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="historia",
        novo_valor="Sem commit",
    )

    # WHEN
    response = AutoApplyService().apply(payload, db, commit=False)

    # THEN
    assert enterprise.historia == "Sem commit"
    assert response.campo_alterado == "historia"
    db.commit.assert_not_called()


def test_given_telefone_when_applied_then_updates_enterprise() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="telefone",
        novo_valor="81999999999",
    )

    # WHEN
    AutoApplyService().apply(payload, db)

    # THEN
    assert enterprise.telefone == "81999999999"


def test_given_horario_when_applied_then_parses_and_sets_both_columns() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="horario_funcionamento",
        novo_valor="08:00-18:30",
    )

    # WHEN
    AutoApplyService().apply(payload, db)

    # THEN
    assert enterprise.hora_abrir == time(8, 0)
    assert enterprise.hora_fechar == time(18, 30)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------


def test_given_valid_preco_when_applied_then_updates_menu() -> None:
    # GIVEN
    menu = _make_menu()
    db = _mock_db_with(menu)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="preco",
        novo_valor="42.50",
    )

    # WHEN
    response = AutoApplyService().apply(payload, db)

    # THEN
    assert menu.preco == Decimal("42.50")
    assert response.campo_alterado == "preco"


def test_given_logical_nome_when_applied_then_writes_to_descricao_column() -> None:
    # GIVEN
    menu = _make_menu()
    db = _mock_db_with(menu)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="nome",
        novo_valor="Novo nome do prato",
    )

    # WHEN
    AutoApplyService().apply(payload, db)

    # THEN
    assert menu.descricao == "Novo nome do prato"


def test_given_logical_descricao_when_applied_then_writes_to_historia_column() -> None:
    # GIVEN
    menu = _make_menu()
    db = _mock_db_with(menu)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="descricao",
        novo_valor="Descrição longa do item",
    )

    # WHEN
    AutoApplyService().apply(payload, db)

    # THEN
    assert menu.historia == "Descrição longa do item"


# ---------------------------------------------------------------------------
# Whitelist e validações
# ---------------------------------------------------------------------------


def test_given_field_outside_whitelist_when_applied_then_raises_422() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="owner_id",
        novo_valor="qualquer",
    )

    # WHEN / THEN
    with pytest.raises(FieldNotAllowedError):
        AutoApplyService().apply(payload, db)
    db.commit.assert_not_called()


def test_given_menu_field_outside_whitelist_when_applied_then_raises_422() -> None:
    # GIVEN
    menu = _make_menu()
    db = _mock_db_with(menu)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="categoria",
        novo_valor="bebida",
    )

    # WHEN / THEN
    with pytest.raises(FieldNotAllowedError):
        AutoApplyService().apply(payload, db)


def test_given_target_menu_without_id_when_validated_then_raises_422() -> None:
    # GIVEN / WHEN / THEN
    with pytest.raises(ValueError):
        AutoApplyRequest(
            enterprise_id=FAKE_ENTERPRISE_ID,
            target=AutoApplyTarget.MENU_ITEM,
            campo_para_alterar="preco",
            novo_valor="10.00",
        )


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_given_missing_enterprise_when_applied_then_raises_404() -> None:
    # GIVEN
    db = _mock_db_with(None)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="historia",
        novo_valor="x",
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        AutoApplyService().apply(payload, db)


def test_given_missing_menu_item_when_applied_then_raises_404() -> None:
    # GIVEN
    db = _mock_db_with(None)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="preco",
        novo_valor="10.00",
    )

    # WHEN / THEN
    with pytest.raises(MenuNotFoundError):
        AutoApplyService().apply(payload, db)


# ---------------------------------------------------------------------------
# Coerção de valores
# ---------------------------------------------------------------------------


def test_given_invalid_preco_value_when_applied_then_raises_422() -> None:
    # GIVEN
    menu = _make_menu()
    db = _mock_db_with(menu)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=FAKE_MENU_ID,
        campo_para_alterar="preco",
        novo_valor="abc",
    )

    # WHEN / THEN
    with pytest.raises(InvalidFieldValueError):
        AutoApplyService().apply(payload, db)


def test_given_invalid_horario_format_when_applied_then_raises_422() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="horario_funcionamento",
        novo_valor="das 8 ate 18",
    )

    # WHEN / THEN
    with pytest.raises(InvalidFieldValueError):
        AutoApplyService().apply(payload, db)


def test_given_invalid_horario_time_when_applied_then_raises_422() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="horario_funcionamento",
        novo_valor="25:00-99:00",
    )

    # WHEN / THEN
    with pytest.raises(InvalidFieldValueError):
        AutoApplyService().apply(payload, db)


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def test_given_db_failure_when_applied_then_raises_persistence_error() -> None:
    # GIVEN
    enterprise = _make_enterprise()
    db = _mock_db_with(enterprise)
    db.commit.side_effect = RuntimeError("connection lost")
    payload = AutoApplyRequest(
        enterprise_id=FAKE_ENTERPRISE_ID,
        target=AutoApplyTarget.ENTERPRISE,
        campo_para_alterar="historia",
        novo_valor="x",
    )

    # WHEN / THEN
    with pytest.raises(AutoApplyPersistenceError):
        AutoApplyService().apply(payload, db)
    db.rollback.assert_called_once()
