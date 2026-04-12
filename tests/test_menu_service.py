"""
Testes unitários para menu_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session completamente mockada.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import EnterpriseNotFoundError
from app.models.enterprise import Enterprise
from app.models.menu import CategoriaCardapio, Menu
from app.schemas.menus import MenuCreate, MenuUpdate
from app.services import menu_service

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_MENU_ID = uuid.uuid4()
FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_OTHER_ENTERPRISE_ID = uuid.uuid4()

FAKE_PRECO = Decimal("25.90")
FAKE_CATEGORIA = CategoriaCardapio.PRATO_PRINCIPAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_menu(**kwargs) -> Menu:
    menu = Menu(
        id_cardapio=kwargs.get("id_cardapio", FAKE_MENU_ID),
        descricao=kwargs.get("descricao", "Frango grelhado com legumes"),
        historia=kwargs.get("historia", None),
        preco=kwargs.get("preco", FAKE_PRECO),
        categoria=kwargs.get("categoria", FAKE_CATEGORIA),
        status=kwargs.get("status", True),
        empresa_id=kwargs.get("empresa_id", FAKE_ENTERPRISE_ID),
    )
    return menu


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
# get_by_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_get_by_enterprise_then_returns_menus():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    menus = [_make_menu(), _make_menu(id_cardapio=uuid.uuid4(), descricao="Sopa de legumes")]
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = menus

    # WHEN
    result = menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert len(result) == 2


def test_given_existing_enterprise_with_no_menus_when_get_by_enterprise_then_returns_empty():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = []

    # WHEN
    result = menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result == []


def test_given_missing_enterprise_when_get_by_enterprise_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_active_menu_when_get_by_id_then_returns_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu()
    db.execute.return_value.scalar_one_or_none.return_value = menu

    # WHEN
    result = menu_service.get_by_id(FAKE_MENU_ID, db)

    # THEN
    assert result is menu


def test_given_missing_menu_when_get_by_id_then_raises_404():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        menu_service.get_by_id(FAKE_MENU_ID, db)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_given_active_menus_when_list_all_then_returns_all():
    # GIVEN
    db = _mock_db()
    menus = [_make_menu(), _make_menu(id_cardapio=uuid.uuid4())]
    db.execute.return_value.scalars.return_value.all.return_value = menus

    # WHEN
    result = menu_service.list_all(db)

    # THEN
    assert len(result) == 2


def test_given_no_menus_when_list_all_then_returns_empty():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalars.return_value.all.return_value = []

    # WHEN
    result = menu_service.list_all(db)

    # THEN
    assert result == []


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_create_then_persists_menu():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Picanha ao molho",
        preco=Decimal("59.90"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    # WHEN
    menu_service.create(payload, db)

    # THEN
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Menu = db.add.call_args[0][0]
    assert added.descricao == "Picanha ao molho"
    assert added.preco == Decimal("59.90")
    assert added.categoria == CategoriaCardapio.PRATO_PRINCIPAL
    assert added.empresa_id == FAKE_ENTERPRISE_ID


def test_given_valid_payload_with_all_fields_when_create_then_persists_all():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Brigadeiro gourmet",
        historia="Receita da vovó transmitida por gerações.",
        preco=Decimal("8.50"),
        categoria=CategoriaCardapio.SOBREMESA,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    # WHEN
    menu_service.create(payload, db)

    # THEN
    added: Menu = db.add.call_args[0][0]
    assert added.historia == "Receita da vovó transmitida por gerações."
    assert added.status is True


def test_given_missing_enterprise_when_create_then_raises_enterprise_not_found():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None
    payload = MenuCreate(
        descricao="Caldo verde",
        preco=Decimal("18.00"),
        categoria=CategoriaCardapio.ENTRADA,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        menu_service.create(payload, db)


def test_given_missing_enterprise_when_create_then_does_not_persist():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None
    payload = MenuCreate(
        descricao="Limonada",
        preco=Decimal("9.00"),
        categoria=CategoriaCardapio.BEBIDA,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        menu_service.create(payload, db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_given_new_preco_when_update_then_persists_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(preco=Decimal("39.90"))

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.preco == Decimal("39.90")
    db.commit.assert_called_once()


def test_given_new_descricao_when_update_then_persists_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(descricao="Novo nome do prato")

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.descricao == "Novo nome do prato"
    db.commit.assert_called_once()


def test_given_new_historia_when_update_then_persists_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(historia="Uma história deliciosa sobre este prato.")

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.historia == "Uma história deliciosa sobre este prato."
    db.commit.assert_called_once()


def test_given_new_categoria_when_update_then_persists_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(categoria=CategoriaCardapio.ENTRADA)
    payload = MenuUpdate(categoria=CategoriaCardapio.SOBREMESA)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.categoria == CategoriaCardapio.SOBREMESA
    db.commit.assert_called_once()


def test_given_status_false_in_payload_when_update_then_persists_status():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(status=True)
    payload = MenuUpdate(status=False)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.status is False
    db.commit.assert_called_once()


def test_given_new_empresa_id_when_update_and_enterprise_exists_then_updates_it():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    new_enterprise = _make_enterprise(id_empresa=FAKE_OTHER_ENTERPRISE_ID)
    db.get.return_value = new_enterprise
    payload = MenuUpdate(empresa_id=FAKE_OTHER_ENTERPRISE_ID)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    assert menu.empresa_id == FAKE_OTHER_ENTERPRISE_ID
    db.commit.assert_called_once()


def test_given_new_empresa_id_when_update_and_enterprise_missing_then_raises():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    db.get.return_value = None
    payload = MenuUpdate(empresa_id=FAKE_OTHER_ENTERPRISE_ID)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN / THEN
        with pytest.raises(EnterpriseNotFoundError):
            menu_service.update(FAKE_MENU_ID, payload, db)


def test_given_same_empresa_id_when_update_then_skips_enterprise_lookup():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    payload = MenuUpdate(empresa_id=FAKE_ENTERPRISE_ID)  # mesmo id, sem troca

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        # WHEN
        menu_service.update(FAKE_MENU_ID, payload, db)

    # THEN
    db.get.assert_not_called()
    db.commit.assert_called_once()


def test_given_missing_menu_when_update_then_raises_404():
    # GIVEN
    db = _mock_db()
    payload = MenuUpdate(preco=Decimal("12.00"))

    with patch(
        "app.services.menu_service.get_by_id",
        side_effect=HTTPException(status_code=404, detail="Cardápio não encontrado."),
    ):
        # WHEN / THEN
        with pytest.raises(HTTPException) as exc_info:
            menu_service.update(FAKE_MENU_ID, payload, db)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_given_active_menu_when_delete_then_marks_status_false():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(status=True)
    db.get.return_value = menu

    # WHEN
    menu_service.delete(FAKE_MENU_ID, db)

    # THEN
    assert menu.status is False
    db.commit.assert_called_once()


def test_given_missing_menu_when_delete_then_raises_404():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        menu_service.delete(FAKE_MENU_ID, db)

    assert exc_info.value.status_code == 404


def test_given_already_inactive_menu_when_delete_then_raises_404():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(status=False)
    db.get.return_value = menu

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        menu_service.delete(FAKE_MENU_ID, db)

    assert exc_info.value.status_code == 404


def test_given_active_menu_when_delete_then_does_not_remove_from_db():
    # GIVEN
    db = _mock_db()
    menu = _make_menu(status=True)
    db.get.return_value = menu

    # WHEN
    menu_service.delete(FAKE_MENU_ID, db)

    # THEN
    db.delete.assert_not_called()
