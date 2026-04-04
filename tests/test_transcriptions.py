"""
Testes unitários para TranscriptionService (SCRUM-84).

Foco: lógica do service isolada.
Estratégia: todas as dependências externas são mockadas:
  - Supabase Storage (upload + get_public_url)
  - AsyncGroq (Whisper + LLaMA)
  - SQLAlchemy Session (add, commit, refresh)

Não há HTTP layer, banco real nem chamadas de rede nestes testes.
"""

import json
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.services.transcription_service import (
    _extract_fields,
    _get_extension,
    _transcribe_audio,
    _upload_audio_to_storage,
    process_audio_registration,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_USUARIO_ID = uuid.uuid4()
FAKE_AUDIO_URL = "https://fake.supabase.co/audios/test.webm"
FAKE_TRANSCRIPTION = (
    "Meu nome é Dona Francisca, faço bordado de renda renascença aqui no Cariri, "
    "na rua do Cruzeiro número quinze. Minha família faz isso há três gerações."
)
FAKE_EXTRACTED = {
    "nome": "Dona Francisca",
    "especialidade": "Bordado de renda renascença",
    "endereco": "Rua do Cruzeiro, 15, Cariri",
    "historia": "Família faz bordado de renda renascença há três gerações",
    "telefone": None,
}

# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------


def _make_upload_file(
    content: bytes = b"fake-audio",
    content_type: str = "audio/webm",
    filename: str = "audio.webm",
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )


def _mock_supabase(url: str = FAKE_AUDIO_URL) -> MagicMock:
    mock = MagicMock()
    mock.storage.from_.return_value.upload.return_value = {}
    mock.storage.from_.return_value.get_public_url.return_value = url
    return mock


def _mock_groq_client(transcription: str = FAKE_TRANSCRIPTION, extracted: dict = FAKE_EXTRACTED):
    client = MagicMock()
    transcription_response = MagicMock()
    transcription_response.__str__ = lambda self: transcription
    client.audio.transcriptions.create = AsyncMock(return_value=transcription_response)
    chat_response = MagicMock()
    chat_response.choices[0].message.content = json.dumps(extracted)
    client.chat.completions.create = AsyncMock(return_value=chat_response)
    return client


def _mock_db(extracted: dict = FAKE_EXTRACTED) -> MagicMock:
    db = MagicMock()

    def _fake_refresh(obj):
        obj.id_transcricao = uuid.uuid4()
        obj.usuario_id = FAKE_USUARIO_ID
        obj.url_audio = FAKE_AUDIO_URL
        obj.texto_bruto = FAKE_TRANSCRIPTION
        obj.nome_extraido = extracted.get("nome")
        obj.especialidade_extraida = extracted.get("especialidade")
        obj.endereco_extraido = extracted.get("endereco")
        obj.historia_extraida = extracted.get("historia")
        obj.telefone_extraido = extracted.get("telefone")

    db.refresh.side_effect = _fake_refresh
    return db


# ---------------------------------------------------------------------------
# Testes de process_audio_registration (função principal)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dado_que_audio_valido_quando_processado_entao_retorna_record_com_campos():
    file = _make_upload_file()
    db = _mock_db()

    with (
        patch("app.services.transcription_service.supabase", _mock_supabase()),
        patch(
            "app.services.transcription_service.AsyncGroq",
            return_value=_mock_groq_client(),
        ),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert record.texto_bruto == FAKE_TRANSCRIPTION
    assert record.nome_extraido == "Dona Francisca"
    assert record.especialidade_extraida == "Bordado de renda renascença"
    assert record.url_audio == FAKE_AUDIO_URL
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.anyio
async def test_dado_que_content_type_invalido_quando_processado_entao_levanta_415():
    file = _make_upload_file(content_type="image/jpeg", filename="foto.jpg")
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 415
    assert "não suportado" in exc_info.value.detail
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_dado_que_arquivo_maior_25mb_quando_processado_entao_levanta_413():
    big_content = b"x" * (25 * 1024 * 1024 + 1)
    file = _make_upload_file(content=big_content)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 413
    assert "25 MB" in exc_info.value.detail
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_dado_que_supabase_falha_quando_upload_entao_levanta_502():
    file = _make_upload_file()
    db = MagicMock()
    mock_supa = MagicMock()
    mock_supa.storage.from_.return_value.upload.side_effect = Exception("connection error")

    with (
        patch("app.services.transcription_service.supabase", mock_supa),
        patch(
            "app.services.transcription_service.AsyncGroq",
            return_value=_mock_groq_client(),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 502
    assert "armazenar" in exc_info.value.detail
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_dado_que_extracao_falha_quando_whisper_ok_entao_persiste_com_campos_nulos():
    file = _make_upload_file()
    db = _mock_db(extracted={k: None for k in FAKE_EXTRACTED})

    mock_client = _mock_groq_client()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))

    with (
        patch("app.services.transcription_service.supabase", _mock_supabase()),
        patch("app.services.transcription_service.AsyncGroq", return_value=mock_client),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # Transcrição foi salva; extração falhou silenciosamente
    assert record.texto_bruto == FAKE_TRANSCRIPTION
    assert record.nome_extraido is None
    assert record.especialidade_extraida is None
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Testes de _upload_audio_to_storage
# ---------------------------------------------------------------------------


def test_dado_que_upload_ok_quando_chamado_entao_retorna_url_publica():
    file = _make_upload_file()
    mock_supa = _mock_supabase()

    with patch("app.services.transcription_service.supabase", mock_supa):
        url = _upload_audio_to_storage(b"bytes", file, FAKE_USUARIO_ID)

    assert url == FAKE_AUDIO_URL
    mock_supa.storage.from_.return_value.upload.assert_called_once()


def test_dado_que_supabase_upload_falha_quando_chamado_entao_levanta_502():
    file = _make_upload_file()
    mock_supa = MagicMock()
    mock_supa.storage.from_.return_value.upload.side_effect = Exception("network error")

    with patch("app.services.transcription_service.supabase", mock_supa):
        with pytest.raises(HTTPException) as exc_info:
            _upload_audio_to_storage(b"bytes", file, FAKE_USUARIO_ID)

    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Testes de _transcribe_audio
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dado_que_groq_whisper_ok_quando_chamado_entao_retorna_texto():
    file = _make_upload_file()

    with patch(
        "app.services.transcription_service.AsyncGroq",
        return_value=_mock_groq_client(),
    ):
        result = await _transcribe_audio(b"audio-bytes", file)

    assert result == FAKE_TRANSCRIPTION


@pytest.mark.anyio
async def test_dado_que_groq_whisper_falha_quando_chamado_entao_levanta_502():
    file = _make_upload_file()
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(side_effect=Exception("timeout"))

    with patch("app.services.transcription_service.AsyncGroq", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await _transcribe_audio(b"audio-bytes", file)

    assert exc_info.value.status_code == 502
    assert "transcrição" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Testes de _extract_fields
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dado_que_llama_retorna_json_valido_quando_chamado_entao_retorna_campos():
    with patch(
        "app.services.transcription_service.AsyncGroq",
        return_value=_mock_groq_client(),
    ):
        result = await _extract_fields(FAKE_TRANSCRIPTION)

    assert result["nome"] == "Dona Francisca"
    assert result["especialidade"] == "Bordado de renda renascença"


@pytest.mark.anyio
async def test_dado_que_llama_falha_quando_chamado_entao_retorna_dict_vazio():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("error"))

    with patch("app.services.transcription_service.AsyncGroq", return_value=mock_client):
        result = await _extract_fields(FAKE_TRANSCRIPTION)

    assert result == {}


# ---------------------------------------------------------------------------
# Testes de _get_extension
# ---------------------------------------------------------------------------


def test_get_extension_com_filename_retorna_extensao_do_nome():
    assert _get_extension("audio.webm", None) == "webm"
    assert _get_extension("gravacao.MP3", None) == "mp3"


def test_get_extension_sem_filename_usa_content_type():
    assert _get_extension(None, "audio/mpeg") == "mp3"
    assert _get_extension(None, "audio/wav") == "wav"
    assert _get_extension(None, "audio/ogg") == "ogg"


def test_get_extension_sem_filename_e_sem_content_type_retorna_fallback():
    assert _get_extension(None, None) == "audio"
    assert _get_extension(None, "audio/desconhecido") == "audio"
