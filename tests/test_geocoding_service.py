"""
Testes unitários para geocoding_service (SCRUM-87) — Google Maps Geocoding API.

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

FAKE_ENDERECO = "Caruaru, Pernambuco, Brasil"

_GOOGLE_SUCCESS = {
    "status": "OK",
    "results": [
        {
            "geometry": {"location": {"lat": -8.2827, "lng": -35.9756}},
            "formatted_address": "Caruaru, PE, Brasil",
        }
    ],
}

_GOOGLE_ZERO_RESULTS = {"status": "ZERO_RESULTS", "results": []}
_GOOGLE_OVER_LIMIT = {"status": "OVER_QUERY_LIMIT", "results": []}
_GOOGLE_DENIED = {"status": "REQUEST_DENIED", "results": []}
_GOOGLE_MALFORMED = {"status": "OK", "results": [{"geometry": {}}]}


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
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
# Testes — caminho feliz
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_address_when_geocoded_then_returns_lat_lng():
    # GIVEN
    response = _mock_httpx_response(_GOOGLE_SUCCESS)
    with _patch_client(response):
        # WHEN
        lat, lng = await geocode_address(FAKE_ENDERECO)

    # THEN
    assert lat == pytest.approx(-8.2827)
    assert lng == pytest.approx(-35.9756)


@pytest.mark.anyio
async def test_given_valid_address_when_geocoded_then_returns_floats():
    # GIVEN
    response = _mock_httpx_response(_GOOGLE_SUCCESS)
    with _patch_client(response):
        # WHEN
        lat, lng = await geocode_address(FAKE_ENDERECO)

    # THEN
    assert isinstance(lat, float)
    assert isinstance(lng, float)


# ---------------------------------------------------------------------------
# Testes — endereço não encontrado
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_zero_results_when_geocoded_then_raises_address_not_found():
    # GIVEN
    response = _mock_httpx_response(_GOOGLE_ZERO_RESULTS)
    with _patch_client(response):
        # WHEN / THEN
        with pytest.raises(AddressNotFoundError) as exc_info:
            await geocode_address("Rua Inventada 999, Cidade Ficticia, ZZ")

    assert "encontrado" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Testes — serviço indisponível / limite atingido
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_over_query_limit_when_geocoded_then_raises_unavailable():
    # GIVEN
    response = _mock_httpx_response(_GOOGLE_OVER_LIMIT)
    with _patch_client(response):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_request_denied_when_geocoded_then_raises_unavailable():
    # GIVEN — chave de API inválida ou restrição de domínio
    response = _mock_httpx_response(_GOOGLE_DENIED)
    with _patch_client(response):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_timeout_when_geocoded_then_raises_geocoding_unavailable():
    # GIVEN
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client):
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

    with patch("app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client):
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

    with patch("app.services.geocoding_service.httpx.AsyncClient", return_value=mock_client):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_unexpected_status_when_geocoded_then_raises_unavailable():
    # GIVEN — status desconhecido retornado pela API
    response = _mock_httpx_response({"status": "UNKNOWN_STATUS_XYZ", "results": []})
    with _patch_client(response):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)


@pytest.mark.anyio
async def test_given_malformed_response_when_geocoded_then_raises_unavailable():
    # GIVEN — Google retorna status OK mas sem location no resultado
    response = _mock_httpx_response(_GOOGLE_MALFORMED)
    with _patch_client(response):
        # WHEN / THEN
        with pytest.raises(GeocodingUnavailableError):
            await geocode_address(FAKE_ENDERECO)
