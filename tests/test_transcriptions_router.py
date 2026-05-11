"""
Testes smoke para o endpoint de transcrições (app/routers/transcriptions.py).

Foco: verificar wire-up HTTP correto (roteamento, serialização da response).
Estratégia: funções de service completamente mockadas; lógica de negócio
é coberta em test_transcriptions.py.
"""

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.transcriptions import EnterpriseFromAudioResponse

client = TestClient(app, raise_server_exceptions=False)

FAKE_EMPRESA_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
FAKE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

_RESPONSE = EnterpriseFromAudioResponse(
    id_empresa=FAKE_EMPRESA_ID,
    usuario_id=FAKE_USER_ID,
    nome="Dona Francisca",
    especialidade="Bordado de renda renascença",
)

_AUDIO_FILES = {"audio": ("gravacao.webm", BytesIO(b"fake-audio"), "audio/webm")}
_FORM_DATA = {"usuario_id": str(FAKE_USER_ID)}

FAKE_TRANSCRIPTION_TEXT = (
    "Quero saber o horário de funcionamento e se vocês aceitam cartão."
)


# ---------------------------------------------------------------------------
# Testes do endpoint POST /transcriptions/ (criação de empresa)
# ---------------------------------------------------------------------------


def test_given_valid_audio_when_transcribed_then_returns_201():
    # GIVEN
    mock_enterprise = MagicMock()
    mock_enterprise.id_empresa = FAKE_EMPRESA_ID
    mock_enterprise.usuario_id = FAKE_USER_ID
    mock_enterprise.nome = "Dona Francisca"
    mock_enterprise.especialidade = "Bordado de renda renascença"
    mock_enterprise.endereco = None
    mock_enterprise.historia = None
    mock_enterprise.telefone = None

    with patch(
        "app.routers.transcriptions.process_audio_registration",
        new=AsyncMock(return_value=mock_enterprise),
    ):
        # WHEN
        response = client.post("/transcriptions/", files=_AUDIO_FILES, data=_FORM_DATA)

    # THEN
    assert response.status_code == 201
    assert response.json()["nome"] == "Dona Francisca"
    assert response.json()["usuario_id"] == str(FAKE_USER_ID)


# ---------------------------------------------------------------------------
# Testes do endpoint POST /transcriptions/chat (transcrição pura)
# ---------------------------------------------------------------------------


def test_given_valid_audio_when_transcribe_endpoint_called_then_returns_200():
    # GIVEN
    with patch(
        "app.routers.transcriptions.transcribe_audio_only",
        new=AsyncMock(return_value=FAKE_TRANSCRIPTION_TEXT),
    ):
        # WHEN
        response = client.post(
            "/transcriptions/chat",
            files={"audio": ("pergunta.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )

    # THEN
    assert response.status_code == 200
    assert response.json()["transcription"] == FAKE_TRANSCRIPTION_TEXT


def test_given_transcribe_endpoint_when_called_then_response_has_only_transcription_field():
    # GIVEN — garante que o contrato do endpoint não vaza campos de empresa
    with patch(
        "app.routers.transcriptions.transcribe_audio_only",
        new=AsyncMock(return_value=FAKE_TRANSCRIPTION_TEXT),
    ):
        # WHEN
        response = client.post(
            "/transcriptions/chat",
            files={"audio": ("pergunta.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )

    # THEN
    body = response.json()
    assert set(body.keys()) == {"transcription"}


def test_given_transcribe_endpoint_when_called_then_no_usuario_id_required():
    # GIVEN — endpoint de transcrição pura NÃO deve exigir usuario_id no form
    with patch(
        "app.routers.transcriptions.transcribe_audio_only",
        new=AsyncMock(return_value=FAKE_TRANSCRIPTION_TEXT),
    ):
        # WHEN — chamada sem nenhum campo de form além do arquivo
        response = client.post(
            "/transcriptions/chat",
            files={"audio": ("pergunta.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )

    # THEN
    assert response.status_code == 200


def test_given_missing_audio_when_transcribe_endpoint_called_then_returns_422():
    # GIVEN / WHEN — chama sem enviar o arquivo
    response = client.post("/transcriptions/chat")

    # THEN
    assert response.status_code == 422