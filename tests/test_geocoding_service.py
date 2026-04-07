"""
Testes unitários para geocoding_service (SCRUM-87).

Foco: lógica do service isolada.
Estratégia: httpx.AsyncClient é completamente mockado.
Não há chamadas de rede reais nestes testes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AddressNotFoundError, GeocodingUnavailableError
from app.services.geocoding_service import geocode_address

# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

FAKE_ENDERECO = "Rua Doutor Carneiro Leao, Caruaru, Pernambuco, Brasil"

NOMINATIM_SUCCESS = [{"lat": "-8.2827", "lon": "-35.9756", "display_name": FAKE_ENDERECO}]

_RATE_PATCH = patch("app.services.geocoding_service._RATE_LIMIT_INTERVAL", 0.0)


def _mock_httpx_response(json_data: list, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


def _patch_client(response: MagicMock) -> patch:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_address_when_geocoded_then_returns_lat_lng():
    # GIVEN
    response = _mock_httpx_response(NOMINATIM_SUCCESS)
    with _RATE_PATCH, _patch_client(response):
        # WHEN
        lat, lng = await geocode_address(FAKE_ENDERECO)

    # THEN
    assert lat == pytest.approx(-8.2827)
    assert lng == pytest.approx(-35.9756)


@pytest.mark.anyio
async def test_given_empty_result_when_geocoded_then_raises_address_not_found():
    # GIVEN
    response = _mock_httpx_response([])
    with _RATE_PATCH, _patch_client(response):
        # WHEN / THEN
        with pytest.raises(AddressNotFoundError) as exc_info:
            await geocode_address("Rua Inventada 999, Cidade Ficticia, ZZ")

    assert (
        "geocodific" in str(exc_info.value).lower() or "encontrado" in str(exc_info.value).lower()
    )


@pytest.mark.anyio
async def test_given_timeout_when_geocoded_then_raises_geocoding_unavailable():
    # GIVEN
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with _RATE_PATCH, patch(
        "app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client
    ):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_connect_error_when_geocoded_then_raises_geocoding_unavailable():
    # GIVEN
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with _RATE_PATCH, patch(
        "app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client
    ):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_http_error_when_geocoded_then_raises_geocoding_unavailable():
    # GIVEN
    mock_client = AsyncMock()
    http_err = httpx.HTTPStatusError(
        "502", request=MagicMock(), response=MagicMock(status_code=502)
    )
    mock_client.get = AsyncMock(side_effect=http_err)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with _RATE_PATCH, patch(
        "app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client
    ):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_valid_address_when_geocoded_then_returns_floats():
    # GIVEN - garante que lat/lng retornam como float, nao string
    response = _mock_httpx_response(NOMINATIM_SUCCESS)
    with _RATE_PATCH, _patch_client(response):
        # WHEN
        lat, lng = await geocode_address(FAKE_ENDERECO)

    # THEN
    assert isinstance(lat, float)
    assert isinstance(lng, float)
