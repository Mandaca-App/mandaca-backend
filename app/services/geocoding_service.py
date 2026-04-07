import asyncio
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AddressNotFoundError, GeocodingUnavailableError

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_TIMEOUT_SECONDS = 10.0

# Nominatim ToS: máximo 1 requisição por segundo por IP.
# Semáforo previne chamadas simultâneas; sleep garante o intervalo mínimo.
# AVISO: _semaphore é estado de módulo — incompatível com pytest-xdist (workers paralelos).
# Para paralelismo de testes, converter para lazy init dentro de geocode_address.
_semaphore = asyncio.Semaphore(1)
_RATE_LIMIT_INTERVAL: float = 1.0  # patchável nos testes (patch para 0.0)


async def geocode_address(endereco: str) -> tuple[float, float]:
    """Geocodifica um endereço via Nominatim e retorna (latitude, longitude).

    Raises:
        AddressNotFoundError: endereço não encontrado pelo Nominatim.
        GeocodingUnavailableError: Nominatim indisponível (timeout ou falha de conexão).
    """
    params = {"q": endereco, "format": "json", "limit": 1, "addressdetails": 0}
    headers = {"User-Agent": settings.nominatim_user_agent}

    async with _semaphore:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_NOMINATIM_URL, params=params, headers=headers)
                response.raise_for_status()
                results = response.json()
        except httpx.TimeoutException:
            logger.warning("Nominatim timeout para endereco: %s", endereco)
            raise GeocodingUnavailableError()
        except httpx.ConnectError:
            logger.warning("Nominatim connection error para endereco: %s", endereco)
            raise GeocodingUnavailableError()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Nominatim HTTP error %s para endereco: %s",
                exc.response.status_code,
                endereco,
            )
            raise GeocodingUnavailableError()
        finally:
            await asyncio.sleep(_RATE_LIMIT_INTERVAL)

    if not results:
        raise AddressNotFoundError(endereco)

    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, ValueError) as exc:
        logger.warning("Nominatim resposta malformada para endereco '%s': %s", endereco, exc)
        raise GeocodingUnavailableError()
