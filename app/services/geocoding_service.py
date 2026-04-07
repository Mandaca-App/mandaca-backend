import logging

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "mandaca-backend/1.0 (mandacaapp@ufrpe.br)"
_TIMEOUT_SECONDS = 10.0

_NOT_FOUND_MSG = "Endereço não encontrado ou não geocodificável."
_UNAVAILABLE_MSG = "Serviço de geolocalização temporariamente indisponível."


async def geocode_address(endereco: str) -> tuple[float, float]:
    """Geocodifica um endereço via Nominatim e retorna (latitude, longitude).

    Raises:
        HTTPException 422: endereço não encontrado pelo Nominatim.
        HTTPException 503: Nominatim indisponível (timeout ou falha de conexão).
    """
    params = {
        "q": endereco,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {"User-Agent": _USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(_NOMINATIM_URL, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()
    except httpx.TimeoutException:
        logger.warning("Nominatim timeout para endereco: %s", endereco)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNAVAILABLE_MSG,
        )
    except httpx.ConnectError:
        logger.warning("Nominatim connection error para endereco: %s", endereco)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNAVAILABLE_MSG,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Nominatim HTTP error %s para endereco: %s", exc.response.status_code, endereco
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNAVAILABLE_MSG,
        )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_NOT_FOUND_MSG,
        )

    return float(results[0]["lat"]), float(results[0]["lon"])
