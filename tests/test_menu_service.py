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

from app.core.exceptions import (
    EnterpriseNotFoundError,
    InvalidImageTypeError,
    MenuNotFoundError,
    MenuPageEmptyError,
)
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

_PAGE_SIZE = 10

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_menu(**kwargs) -> Menu:
    return Menu(
        id_cardapio=kwargs.get("id_cardapio", FAKE_MENU_ID),
        descricao=kwargs.get("descricao", "Frango grelhado com legumes"),
        historia=kwargs.get("historia", None),
        preco=kwargs.get("preco", FAKE_PRECO),
        categoria=kwargs.get("categoria", FAKE_CATEGORIA),
        status=kwargs.get("status", True),
        empresa_id=kwargs.get("empresa_id", FAKE_ENTERPRISE_ID),
        url_foto_item=kwargs.get("url_foto_item", None),
    )


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

    # Configura db.execute (usado por get_by_enterprise e get_by_id)
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    # Configura db.scalars (usado por list_all e list_by_enterprise_paginated)
    db.scalars.return_value.all.return_value = []

    db.get.return_value = None
    return db


# ---------------------------------------------------------------------------
# get_by_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_get_by_enterprise_then_returns_menus():
    db = _mock_db()
    enterprise = _make_enterprise()
    menus = [_make_menu(), _make_menu(id_cardapio=uuid.uuid4(), descricao="Sopa de legumes")]
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = menus

    result = menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)

    assert len(result) == 2


def test_given_existing_enterprise_with_no_menus_when_get_by_enterprise_then_returns_empty():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = []

    result = menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)

    assert result == []


def test_given_missing_enterprise_when_get_by_enterprise_then_raises_not_found():
    db = _mock_db()
    db.get.return_value = None

    with pytest.raises(EnterpriseNotFoundError):
        menu_service.get_by_enterprise(FAKE_ENTERPRISE_ID, db)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_active_menu_when_get_by_id_then_returns_it():
    db = _mock_db()
    menu = _make_menu()
    db.execute.return_value.scalar_one_or_none.return_value = menu

    result = menu_service.get_by_id(FAKE_MENU_ID, db)

    assert result is menu


def test_given_missing_menu_when_get_by_id_then_raises_domain_error():
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(MenuNotFoundError) as exc_info:
        menu_service.get_by_id(FAKE_MENU_ID, db)

    assert exc_info.value.menu_id == FAKE_MENU_ID


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_given_active_menus_when_list_all_then_returns_all():
    db = _mock_db()
    menus = [_make_menu(), _make_menu(id_cardapio=uuid.uuid4())]
    # list_all usa db.scalars(stmt).all()
    db.scalars.return_value.all.return_value = menus

    result = menu_service.list_all(db)

    assert len(result) == 2


def test_given_no_menus_when_list_all_then_returns_empty():
    db = _mock_db()
    # _mock_db já configura db.scalars.return_value.all.return_value = []
    db.scalars.return_value.all.return_value = []

    result = menu_service.list_all(db)

    assert result == []


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_create_then_persists_menu():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Picanha ao molho",
        preco=Decimal("59.90"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    menu_service.create(payload, foto=None, db=db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Menu = db.add.call_args[0][0]
    assert added.descricao == "Picanha ao molho"
    assert added.preco == Decimal("59.90")
    assert added.categoria == CategoriaCardapio.PRATO_PRINCIPAL
    assert added.empresa_id == FAKE_ENTERPRISE_ID


def test_given_valid_payload_with_all_fields_when_create_then_persists_all():
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

    menu_service.create(payload, foto=None, db=db)

    added: Menu = db.add.call_args[0][0]
    assert added.historia == "Receita da vovó transmitida por gerações."
    assert added.status is True


def test_given_missing_enterprise_when_create_then_raises_enterprise_not_found():
    db = _mock_db()
    db.get.return_value = None
    payload = MenuCreate(
        descricao="Caldo verde",
        preco=Decimal("18.00"),
        categoria=CategoriaCardapio.ENTRADA,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        menu_service.create(payload, foto=None, db=db)


def test_given_missing_enterprise_when_create_then_does_not_persist():
    db = _mock_db()
    db.get.return_value = None
    payload = MenuCreate(
        descricao="Limonada",
        preco=Decimal("9.00"),
        categoria=CategoriaCardapio.BEBIDA,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        menu_service.create(payload, foto=None, db=db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_given_new_preco_when_update_then_persists_it():
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(preco=Decimal("39.90"))

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.preco == Decimal("39.90")
    db.commit.assert_called_once()


def test_given_new_descricao_when_update_then_persists_it():
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(descricao="Novo nome do prato")

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.descricao == "Novo nome do prato"
    db.commit.assert_called_once()


def test_given_new_historia_when_update_then_persists_it():
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate(historia="Uma história deliciosa sobre este prato.")

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.historia == "Uma história deliciosa sobre este prato."
    db.commit.assert_called_once()


def test_given_new_categoria_when_update_then_persists_it():
    db = _mock_db()
    menu = _make_menu(categoria=CategoriaCardapio.ENTRADA)
    payload = MenuUpdate(categoria=CategoriaCardapio.SOBREMESA)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.categoria == CategoriaCardapio.SOBREMESA
    db.commit.assert_called_once()


def test_given_status_false_in_payload_when_update_then_persists_status():
    db = _mock_db()
    menu = _make_menu(status=True)
    payload = MenuUpdate(status=False)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.status is False
    db.commit.assert_called_once()


def test_given_new_empresa_id_when_update_and_enterprise_exists_then_updates_it():
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    new_enterprise = _make_enterprise(id_empresa=FAKE_OTHER_ENTERPRISE_ID)
    db.get.return_value = new_enterprise
    payload = MenuUpdate(empresa_id=FAKE_OTHER_ENTERPRISE_ID)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    assert menu.empresa_id == FAKE_OTHER_ENTERPRISE_ID
    db.commit.assert_called_once()


def test_given_new_empresa_id_when_update_and_enterprise_missing_then_raises():
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    db.get.return_value = None
    payload = MenuUpdate(empresa_id=FAKE_OTHER_ENTERPRISE_ID)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        with pytest.raises(EnterpriseNotFoundError):
            menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)


def test_given_same_empresa_id_when_update_then_skips_enterprise_lookup():
    db = _mock_db()
    menu = _make_menu(empresa_id=FAKE_ENTERPRISE_ID)
    payload = MenuUpdate(empresa_id=FAKE_ENTERPRISE_ID)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)

    db.get.assert_not_called()
    db.commit.assert_called_once()


def test_given_missing_menu_when_update_then_raises_domain_error():
    db = _mock_db()
    payload = MenuUpdate(preco=Decimal("12.00"))

    with patch(
        "app.services.menu_service.get_by_id",
        side_effect=MenuNotFoundError(FAKE_MENU_ID),
    ):
        with pytest.raises(MenuNotFoundError):
            menu_service.update(FAKE_MENU_ID, payload, foto=None, db=db)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_given_active_menu_when_delete_then_marks_status_false():
    db = _mock_db()
    menu = _make_menu(status=True)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.delete(FAKE_MENU_ID, db)

    assert menu.status is False
    db.commit.assert_called_once()


def test_given_missing_menu_when_delete_then_raises_domain_error():
    db = _mock_db()

    with patch(
        "app.services.menu_service.get_by_id",
        side_effect=MenuNotFoundError(FAKE_MENU_ID),
    ):
        with pytest.raises(MenuNotFoundError):
            menu_service.delete(FAKE_MENU_ID, db)

    db.commit.assert_not_called()


def test_given_already_inactive_menu_when_delete_then_raises_domain_error():
    db = _mock_db()
    menu = _make_menu(status=False)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.delete(FAKE_MENU_ID, db)

    assert menu.status is False
    db.commit.assert_called_once()


def test_given_active_menu_when_delete_then_does_not_remove_from_db():
    db = _mock_db()
    menu = _make_menu(status=True)

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        menu_service.delete(FAKE_MENU_ID, db)

    db.delete.assert_not_called()


def test_given_foto_when_create_and_upload_succeeds_then_sets_url():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Prato com foto",
        preco=Decimal("29.90"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )
    foto = MagicMock()
    foto.content_type = "image/jpeg"
    foto.filename = "prato.jpg"
    foto.file.read.return_value = b"fakebytes"

    fake_url = "https://mock-url.com/object/public/mandaca-bucket/cardapios/x.jpg"

    with patch("app.services.menu_service.supabase") as mock_supabase:
        mock_supabase.storage.from_().upload.return_value = {}
        mock_supabase.storage.from_().get_public_url.return_value = fake_url
        menu_service.create(payload, foto=foto, db=db)

    added: Menu = db.add.call_args[0][0]
    assert added.url_foto_item == fake_url


def test_given_foto_when_create_and_upload_fails_then_url_is_none():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Prato com foto",
        preco=Decimal("29.90"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )
    foto = MagicMock()
    foto.content_type = "image/jpeg"
    foto.filename = "prato.jpg"
    foto.file.read.return_value = b"fakebytes"

    with patch("app.services.menu_service.supabase") as mock_supabase:
        mock_supabase.storage.from_().upload.side_effect = Exception("Storage error")
        menu_service.create(payload, foto=foto, db=db)

    added: Menu = db.add.call_args[0][0]
    assert added.url_foto_item is None


def test_given_foto_when_update_then_removes_old_and_sets_new_url():
    db = _mock_db()
    old_url = "https://mock-url.com/object/public/mandaca-bucket/cardapios/old.jpg"
    menu = _make_menu(url_foto_item=old_url)
    new_url = "https://mock-url.com/object/public/mandaca-bucket/cardapios/new.jpg"
    payload = MenuUpdate()

    foto = MagicMock()
    foto.content_type = "image/jpeg"
    foto.filename = "novo.jpg"
    foto.file.read.return_value = b"fakebytes"

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        with patch("app.services.menu_service.supabase") as mock_supabase:
            mock_supabase.storage.from_().upload.return_value = {}
            mock_supabase.storage.from_().get_public_url.return_value = new_url
            menu_service.update(FAKE_MENU_ID, payload, foto=foto, db=db)

    mock_supabase.storage.from_().remove.assert_called_once_with(["cardapios/old.jpg"])
    assert menu.url_foto_item == new_url


def test_given_invalid_file_type_when_create_then_raises_invalid_image_type():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = MenuCreate(
        descricao="Prato teste",
        preco=Decimal("20.00"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )
    foto = MagicMock()
    foto.content_type = "application/pdf"
    foto.filename = "documento.pdf"

    with pytest.raises(InvalidImageTypeError):
        menu_service.create(payload, foto=foto, db=db)

    db.add.assert_not_called()


def test_given_invalid_file_type_when_update_then_raises_invalid_image_type():
    db = _mock_db()
    menu = _make_menu()
    payload = MenuUpdate()

    foto = MagicMock()
    foto.content_type = "application/pdf"
    foto.filename = "documento.pdf"

    with patch("app.services.menu_service.get_by_id", return_value=menu):
        with pytest.raises(InvalidImageTypeError):
            menu_service.update(FAKE_MENU_ID, payload, foto=foto, db=db)

    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# list_by_enterprise_paginated
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_paginated_then_returns_first_page():
    db = _mock_db()
    enterprise = _make_enterprise()
    menus = [_make_menu(), _make_menu(id_cardapio=uuid.uuid4())]
    db.get.return_value = enterprise
    db.scalars.return_value.all.return_value = menus

    result = menu_service.list_by_enterprise_paginated(
        FAKE_ENTERPRISE_ID, page=1, categoria=None, db=db
    )

    assert result.page == 1
    assert result.has_more is False
    assert len(result.items) == 2


def test_given_more_items_than_page_size_when_paginated_then_has_more_is_true():
    db = _mock_db()
    enterprise = _make_enterprise()
    menus = [_make_menu(id_cardapio=uuid.uuid4()) for _ in range(_PAGE_SIZE + 1)]
    db.get.return_value = enterprise
    db.scalars.return_value.all.return_value = menus

    result = menu_service.list_by_enterprise_paginated(
        FAKE_ENTERPRISE_ID, page=1, categoria=None, db=db
    )

    assert result.has_more is True
    assert len(result.items) == _PAGE_SIZE


def test_given_categoria_filter_when_paginated_then_returns_only_matching():
    db = _mock_db()
    enterprise = _make_enterprise()
    menus = [_make_menu(categoria=CategoriaCardapio.LANCHE)]
    db.get.return_value = enterprise
    db.scalars.return_value.all.return_value = menus

    result = menu_service.list_by_enterprise_paginated(
        FAKE_ENTERPRISE_ID, page=1, categoria=CategoriaCardapio.LANCHE, db=db
    )

    assert len(result.items) == 1
    assert result.items[0].categoria == CategoriaCardapio.LANCHE


def test_given_empty_page_beyond_first_when_paginated_then_raises_page_empty():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.scalars.return_value.all.return_value = []

    with pytest.raises(MenuPageEmptyError) as exc_info:
        menu_service.list_by_enterprise_paginated(FAKE_ENTERPRISE_ID, page=2, categoria=None, db=db)

    assert exc_info.value.page == 2


def test_given_empty_first_page_when_paginated_then_returns_empty_without_raising():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.scalars.return_value.all.return_value = []

    result = menu_service.list_by_enterprise_paginated(
        FAKE_ENTERPRISE_ID, page=1, categoria=None, db=db
    )

    assert result.page == 1
    assert result.has_more is False
    assert len(result.items) == 0


def test_given_missing_enterprise_when_paginated_then_raises_enterprise_not_found():
    db = _mock_db()
    db.get.return_value = None

    with pytest.raises(EnterpriseNotFoundError):
        menu_service.list_by_enterprise_paginated(FAKE_ENTERPRISE_ID, page=1, categoria=None, db=db)
