"""
Testes unitários para enterprise_service (refactor SCRUM-87).

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session e geocoding_service completamente mockados.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.enterprises import EnterpriseCreate, EnterpriseUpdate
from app.services import enterprise_service

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_USER_ID = uuid.uuid4()
FAKE_LAT, FAKE_LNG = -8.2827, -35.9756
FAKE_ENDERECO = "Rua das Flores, 10, Caruaru, PE"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_enterprise(**kwargs) -> Enterprise:
    e = Enterprise(
        id_empresa=FAKE_ENTERPRISE_ID,
        nome=kwargs.get("nome", "Empresa Teste"),
        especialidade=kwargs.get("especialidade"),
        endereco=kwargs.get("endereco"),
        historia=kwargs.get("historia"),
        hora_abrir=None,
        hora_fechar=None,
        telefone=None,
        latitude=kwargs.get("latitude"),
        longitude=kwargs.get("longitude"),
        usuario_id=FAKE_USER_ID,
    )
    e.fotos = kwargs.get("fotos", [])
    e.cardapios = kwargs.get("cardapios", [])
    e.reservas = []
    e.avaliacoes = []
    return e


def _make_user(has_empresa: bool = False) -> User:
    user = MagicMock(spec=User)
    user.id_usuario = FAKE_USER_ID
    user.empresa = _make_enterprise() if has_empresa else None
    return user


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


def test_given_existing_enterprise_when_get_by_id_then_returns_it():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise

    # WHEN
    result = enterprise_service.get_by_id(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result is enterprise
    db.get.assert_called_once_with(Enterprise, FAKE_ENTERPRISE_ID)


def test_given_missing_enterprise_when_get_by_id_then_raises_404():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        enterprise_service.get_by_id(FAKE_ENTERPRISE_ID, db)

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_given_enterprises_when_list_all_then_returns_list():
    # GIVEN
    db = _mock_db()
    enterprises = [_make_enterprise(), _make_enterprise(nome="Outra")]
    db.execute.return_value.scalars.return_value.all.return_value = enterprises

    # WHEN
    result = enterprise_service.list_all(db)

    # THEN
    assert len(result) == 2


# ---------------------------------------------------------------------------
# get_overview
# ---------------------------------------------------------------------------


def test_given_enterprise_when_get_overview_then_builds_response():
    # GIVEN
    db = _mock_db()
    photo = MagicMock()
    photo.url_foto_empresa = "https://example.com/foto.jpg"
    enterprise = _make_enterprise(
        endereco=FAKE_ENDERECO, latitude=FAKE_LAT, longitude=FAKE_LNG, fotos=[photo]
    )
    db.get.return_value = enterprise

    # WHEN
    result = enterprise_service.get_overview(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result.latitude == FAKE_LAT
    assert result.longitude == FAKE_LNG
    assert result.endereco == FAKE_ENDERECO
    assert len(result.fotos) == 1
    assert result.fotos[0].url_foto_empresa == "https://example.com/foto.jpg"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_payload_when_create_then_persists_with_lat_lng():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_user()
    payload = EnterpriseCreate(
        nome="Nova Empresa",
        endereco=FAKE_ENDERECO,
        usuario_id=FAKE_USER_ID,
    )

    with patch(
        "app.services.enterprise_service.geocode_address",
        new=AsyncMock(return_value=(FAKE_LAT, FAKE_LNG)),
    ):
        # WHEN
        await enterprise_service.create(payload, db)

    # THEN
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Enterprise = db.add.call_args[0][0]
    assert added.latitude == FAKE_LAT
    assert added.longitude == FAKE_LNG


@pytest.mark.anyio
async def test_given_payload_without_address_when_create_then_skips_geocoding():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_user()
    payload = EnterpriseCreate(nome="Sem Endereco", usuario_id=FAKE_USER_ID)

    with patch(
        "app.services.enterprise_service.geocode_address",
        new=AsyncMock(),
    ) as mock_geo:
        # WHEN
        await enterprise_service.create(payload, db)

    # THEN
    mock_geo.assert_not_called()


@pytest.mark.anyio
async def test_given_duplicate_name_when_create_then_raises_400():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _make_enterprise()
    payload = EnterpriseCreate(nome="Existente", usuario_id=FAKE_USER_ID)

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        await enterprise_service.create(payload, db)

    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_given_unknown_user_when_create_then_raises_404():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None
    payload = EnterpriseCreate(nome="Empresa X", usuario_id=FAKE_USER_ID)

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        await enterprise_service.create(payload, db)

    assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_given_user_with_enterprise_when_create_then_raises_400():
    # GIVEN
    db = _mock_db()
    db.get.return_value = _make_user(has_empresa=True)
    payload = EnterpriseCreate(nome="Empresa Y", usuario_id=FAKE_USER_ID)

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        await enterprise_service.create(payload, db)

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_new_address_when_update_then_geocodes_and_persists():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    payload = EnterpriseUpdate(endereco=FAKE_ENDERECO)

    with patch(
        "app.services.enterprise_service.geocode_address",
        new=AsyncMock(return_value=(FAKE_LAT, FAKE_LNG)),
    ):
        # WHEN
        await enterprise_service.update(FAKE_ENTERPRISE_ID, payload, db)

    # THEN
    assert enterprise.latitude == FAKE_LAT
    assert enterprise.longitude == FAKE_LNG
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_given_no_address_in_payload_when_update_then_skips_geocoding():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise(latitude=FAKE_LAT, longitude=FAKE_LNG)
    db.get.return_value = enterprise
    payload = EnterpriseUpdate(historia="Nova historia")

    with patch(
        "app.services.enterprise_service.geocode_address",
        new=AsyncMock(),
    ) as mock_geo:
        # WHEN
        await enterprise_service.update(FAKE_ENTERPRISE_ID, payload, db)

    # THEN
    mock_geo.assert_not_called()
    assert enterprise.latitude == FAKE_LAT


@pytest.mark.anyio
async def test_given_missing_enterprise_when_update_then_raises_404():
    # GIVEN
    db = _mock_db()
    db.get.return_value = None
    payload = EnterpriseUpdate(historia="Qualquer")

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        await enterprise_service.update(FAKE_ENTERPRISE_ID, payload, db)

    assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_given_duplicate_name_when_update_then_raises_400():
    # GIVEN
    db = _mock_db()
    other_enterprise = _make_enterprise(nome="Outro")
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.execute.return_value.scalar_one_or_none.return_value = other_enterprise
    payload = EnterpriseUpdate(nome="Outro")

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc:
        await enterprise_service.update(FAKE_ENTERPRISE_ID, payload, db)

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_percentage
# ---------------------------------------------------------------------------


def test_given_fully_filled_enterprise_when_get_percentage_then_returns_high():
    # GIVEN
    db = _mock_db()
    foto = MagicMock()
    cardapio = MagicMock()
    enterprise = _make_enterprise(
        especialidade="Bordado",
        endereco=FAKE_ENDERECO,
        historia="Historia",
        fotos=[foto],
        cardapios=[cardapio],
    )
    enterprise.hora_abrir = "08:00"
    enterprise.hora_fechar = "18:00"
    enterprise.telefone = "81999999999"
    db.get.return_value = enterprise

    # WHEN
    result = enterprise_service.get_percentage(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result.porcentagem == 100.0
    assert len(result.campos_faltando) == 0


def test_given_empty_enterprise_when_get_percentage_then_returns_base():
    # GIVEN
    db = _mock_db()
    enterprise = _make_enterprise()
    enterprise.hora_abrir = None
    enterprise.hora_fechar = None
    enterprise.telefone = None
    db.get.return_value = enterprise

    # WHEN
    result = enterprise_service.get_percentage(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result.porcentagem == 20.0
    assert len(result.campos_preenchidos) == 0
