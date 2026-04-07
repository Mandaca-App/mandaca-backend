from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.models
from app.core.config import settings
from app.core.exceptions import (
    AddressNotFoundError,
    DuplicateEnterpriseNameError,
    EnterpriseNotFoundError,
    GeocodingUnavailableError,
    MandacaError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
    UserNotFoundError,
)
from app.routers import enterprises, photos, transcriptions, users

app = FastAPI(title="Meu Projeto", version="0.1.0")

app.include_router(users.router)
app.include_router(enterprises.router)
app.include_router(photos.router)
app.include_router(transcriptions.router)


# ---------------------------------------------------------------------------
# Handlers de exceções de domínio — conversão domínio → HTTP única e central
# ---------------------------------------------------------------------------

_NOT_FOUND_TYPES = (EnterpriseNotFoundError, UserNotFoundError)
_BAD_REQUEST_TYPES = (
    DuplicateEnterpriseNameError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
)


def _register_handlers(fastapi_app: FastAPI) -> None:
    for exc_class in _NOT_FOUND_TYPES:

        @fastapi_app.exception_handler(exc_class)
        async def _404(request: Request, exc: MandacaError) -> JSONResponse:
            return JSONResponse(status_code=404, content={"detail": str(exc)})

    for exc_class in _BAD_REQUEST_TYPES:

        @fastapi_app.exception_handler(exc_class)
        async def _400(request: Request, exc: MandacaError) -> JSONResponse:
            return JSONResponse(status_code=400, content={"detail": str(exc)})

    @fastapi_app.exception_handler(AddressNotFoundError)
    async def _422(request: Request, exc: AddressNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @fastapi_app.exception_handler(GeocodingUnavailableError)
    async def _503(request: Request, exc: GeocodingUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})


_register_handlers(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"])
def health_check() -> dict[str, str]:
    """Endpoint de health check — usado pelo Render para verificar se a app está viva."""
    return {"status": "ok", "env": settings.app_env}
