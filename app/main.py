from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.models
from app.core.config import settings
from app.core.exceptions import (
    AddressNotFoundError,
    AIReportGenerationError,
    AIReportNotFoundError,
    AssessmentClassificationError,
    AssessmentNotFoundError,
    AssessmentPageEmptyError,
    AudioRateLimitError,
    AudioServiceConnectionError,
    AudioServiceTimeoutError,
    AudioTooLargeError,
    AudioTranscriptionError,
    BusinessContextNotFoundError,
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
    DuplicateEnterpriseNameError,
    EnterpriseNotFoundError,
    GeocodingUnavailableError,
    InvalidContextDataError,
    MandacaError,
    UnsupportedAudioFormatError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
    UserNotFoundError,
)
from app.routers import (
    assessments,
    business_context,
    chat,
    enterprises,
    menus,
    notifications,
    photos,
    reports,
    transcriptions,
    users,
)

app = FastAPI(title="Meu Projeto", version="0.1.0")

app.include_router(users.router)
app.include_router(enterprises.router)
app.include_router(photos.router)
app.include_router(notifications.router)
app.include_router(transcriptions.router)
app.include_router(assessments.router)
app.include_router(chat.router)
app.include_router(menus.router)
app.include_router(business_context.router)
app.include_router(reports.router)


# ---------------------------------------------------------------------------
# Handlers de exceções de domínio — conversão domínio → HTTP única e central
# ---------------------------------------------------------------------------

_NOT_FOUND_TYPES = (
    EnterpriseNotFoundError,
    UserNotFoundError,
    AIReportNotFoundError,
    AssessmentNotFoundError,
)
_BAD_REQUEST_TYPES = (
    DuplicateEnterpriseNameError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
)
_BAD_GATEWAY_TYPES = (
    AudioServiceConnectionError,
    AudioTranscriptionError,
    ChatServiceConnectionError,
    ChatServiceError,
    AIReportGenerationError,
)
_SERVICE_UNAVAILABLE_TYPES = (AssessmentClassificationError,)


async def _handle_400(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _handle_404(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _handle_413(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


async def _handle_415(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=415, content={"detail": str(exc)})


async def _handle_422(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def _handle_429(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


async def _handle_502(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


async def _handle_503(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def _handle_504(request: Request, exc: MandacaError) -> JSONResponse:
    return JSONResponse(status_code=504, content={"detail": str(exc)})


def _register_handlers(fastapi_app: FastAPI) -> None:
    for exc_class in _NOT_FOUND_TYPES:
        fastapi_app.add_exception_handler(exc_class, _handle_404)
    for exc_class in _BAD_REQUEST_TYPES:
        fastapi_app.add_exception_handler(exc_class, _handle_400)
    for exc_class in _BAD_GATEWAY_TYPES:
        fastapi_app.add_exception_handler(exc_class, _handle_502)
    for exc_class in _SERVICE_UNAVAILABLE_TYPES:
        fastapi_app.add_exception_handler(exc_class, _handle_503)
    fastapi_app.add_exception_handler(AddressNotFoundError, _handle_422)
    fastapi_app.add_exception_handler(GeocodingUnavailableError, _handle_503)
    fastapi_app.add_exception_handler(AudioTooLargeError, _handle_413)
    fastapi_app.add_exception_handler(UnsupportedAudioFormatError, _handle_415)
    fastapi_app.add_exception_handler(AudioRateLimitError, _handle_429)
    fastapi_app.add_exception_handler(AudioServiceTimeoutError, _handle_504)
    fastapi_app.add_exception_handler(ChatRateLimitError, _handle_429)
    fastapi_app.add_exception_handler(ChatServiceTimeoutError, _handle_504)
    fastapi_app.add_exception_handler(BusinessContextNotFoundError, _handle_404)
    fastapi_app.add_exception_handler(AssessmentPageEmptyError, _handle_404)
    fastapi_app.add_exception_handler(InvalidContextDataError, _handle_422)


_register_handlers(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"])
def health_check() -> dict[str, str]:
    """Endpoint de health check — usado pelo Render para verificar se a app está viva."""
    return {"status": "ok", "env": settings.app_env}
