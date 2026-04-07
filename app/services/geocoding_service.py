import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AddressNotFoundError, GeocodingUnavailableError

logger = logging.getLogger(__name__)

_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_TIMEOUT_SECONDS = 10.0

# Statuses da Google Geocoding API que indicam serviço indisponível ou limite atingido
_UNAVAILABLE_STATUSES = frozenset(
    {"OVER_DAILY_LIMIT", "OVER_QUERY_LIMIT", "REQUEST_DENIED", "UNKNOWN_ERROR"}
)


async def geocode_address(endereco: str) -> tuple[float, float]:
    """Geocodifica um endereço via Google Maps Geocoding API e retorna (latitude, longitude).

    Raises:
        AddressNotFoundError: endereço não encontrado pelo Google.
        GeocodingUnavailableError: API indisponível, chave inválida ou limite atingido.
    """
    params = {
        "address": endereco,
        "key": settings.google_maps_api_key,
        "language": "pt-BR",
        "region": "BR",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(_GEOCODING_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.warning("Google Maps Geocoding timeout para endereco: %s", endereco)
        raise GeocodingUnavailableError()
    except httpx.ConnectError:
        logger.warning("Google Maps Geocoding connection error para endereco: %s", endereco)
        raise GeocodingUnavailableError()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Google Maps Geocoding HTTP error %s para endereco: %s",
            exc.response.status_code,
            endereco,
        )
        raise GeocodingUnavailableError()

    status = data.get("status")

    if status == "ZERO_RESULTS":
        raise AddressNotFoundError(endereco)

    if status in _UNAVAILABLE_STATUSES:
        logger.warning("Google Maps Geocoding status %s para endereco: %s", status, endereco)
        raise GeocodingUnavailableError()

    if status != "OK":
        logger.warning(
            "Google Maps Geocoding status inesperado '%s' para endereco: %s",
            status,
            endereco,
        )
        raise GeocodingUnavailableError()

    try:
        location = data["results"][0]["geometry"]["location"]
        return float(location["lat"]), float(location["lng"])
    except (KeyError, ValueError, IndexError) as exc:
        logger.warning(
            "Google Maps Geocoding resposta malformada para endereco '%s': %s",
            endereco,
            exc,
        )
        raise GeocodingUnavailableError()
