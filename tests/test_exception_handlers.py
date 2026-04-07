"""
Testes de smoke para os exception handlers centrais (app/main.py).

Foco: verificar que cada exceção de domínio é convertida ao status HTTP correto.
Estratégia: TestClient com serviços mockados para forçar cada tipo de exceção.
"""

from io import BytesIO
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import (
    AddressNotFoundError,
    AudioRateLimitError,
    AudioServiceConnectionError,
    AudioServiceTimeoutError,
    AudioTooLargeError,
    AudioTranscriptionError,
    DuplicateEnterpriseNameError,
    EnterpriseNotFoundError,
    GeocodingUnavailableError,
    UnsupportedAudioFormatError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
    UserNotFoundError,
)
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FAKE_UUID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 404 handlers
# ---------------------------------------------------------------------------


def test_given_enterprise_not_found_when_get_then_returns_404():
    # GIVEN
    with patch(
        "app.services.enterprise_service.get_by_id",
        side_effect=EnterpriseNotFoundError(FAKE_UUID),
    ):
        # WHEN
        response = client.get(f"/enterprises/{FAKE_UUID}")

    # THEN
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"].lower()


def test_given_user_not_found_when_creating_enterprise_then_returns_404():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=UserNotFoundError(FAKE_UUID)),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa X", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 400 handlers
# ---------------------------------------------------------------------------


def test_given_duplicate_name_when_creating_enterprise_then_returns_400():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=DuplicateEnterpriseNameError("Empresa X")),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa X", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 400
    assert "empresa" in response.json()["detail"].lower()


def test_given_user_already_has_enterprise_when_creating_then_returns_400():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=UserAlreadyHasEnterpriseError(FAKE_UUID)),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa Y", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 400


def test_given_user_already_linked_when_updating_then_returns_400():
    # GIVEN
    with patch(
        "app.services.enterprise_service.update",
        new=AsyncMock(side_effect=UserAlreadyLinkedError(FAKE_UUID)),
    ):
        # WHEN
        response = client.put(
            f"/enterprises/{FAKE_UUID}",
            json={"usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 422 handler
# ---------------------------------------------------------------------------


def test_given_address_not_found_when_creating_enterprise_then_returns_422():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=AddressNotFoundError("Rua Inventada, 999")),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa Z", "usuario_id": FAKE_UUID, "endereco": "Rua Inventada, 999"},
        )

    # THEN
    assert response.status_code == 422
    assert "geocodific" in response.json()["detail"].lower() or (
        "encontrado" in response.json()["detail"].lower()
    )


# ---------------------------------------------------------------------------
# 503 handler
# ---------------------------------------------------------------------------


def test_given_geocoding_unavailable_when_creating_enterprise_then_returns_503():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=GeocodingUnavailableError()),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa W", "usuario_id": FAKE_UUID, "endereco": "Qualquer Rua"},
        )

    # THEN
    assert response.status_code == 503
    assert "indispon" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Handlers de áudio (413, 415, 429, 502, 504)
# ---------------------------------------------------------------------------

_AUDIO_POST = "/transcriptions/"
_AUDIO_FILES = {"audio": ("test.mp3", BytesIO(b"fake"), "audio/mpeg")}
_AUDIO_DATA = {"usuario_id": FAKE_UUID}


def test_given_unsupported_format_when_transcribing_then_returns_415():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=UnsupportedAudioFormatError("audio/ogg")),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 415
    assert "não suportado" in response.json()["detail"].lower()


def test_given_audio_too_large_when_transcribing_then_returns_413():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=AudioTooLargeError()),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 413
    assert "25 mb" in response.json()["detail"].lower()


def test_given_rate_limit_when_transcribing_then_returns_429():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=AudioRateLimitError()),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 429
    assert "tente novamente" in response.json()["detail"].lower()


def test_given_connection_error_when_transcribing_then_returns_502():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=AudioServiceConnectionError()),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 502
    assert "conectar" in response.json()["detail"].lower()


def test_given_transcription_error_when_transcribing_then_returns_502():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=AudioTranscriptionError("falha interna")),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 502
    assert "transcrição" in response.json()["detail"].lower()


def test_given_timeout_when_transcribing_then_returns_504():
    # GIVEN
    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(side_effect=AudioServiceTimeoutError()),
    ):
        # WHEN
        response = client.post(_AUDIO_POST, files=_AUDIO_FILES, data=_AUDIO_DATA)

    # THEN
    assert response.status_code == 504
    assert "demorou demais" in response.json()["detail"].lower()
