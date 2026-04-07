"""
Testes smoke para o endpoint de transcrições (app/routers/transcriptions.py).

Foco: verificar wire-up HTTP correto (roteamento, serialização da response).
Estratégia: process_audio_registration completamente mockado; lógica de negócio
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
