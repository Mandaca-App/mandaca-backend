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

import groq as groq_sdk
import pytest
from fastapi import HTTPException, UploadFile

from app.models.audio_transcription import AudioTranscription
from app.schemas.transcriptions import AudioTranscriptionResponse, ExtractedFieldsResponse
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
    size: int | None = None,
) -> UploadFile:
    f = UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )
    if size is not None:
        f.size = size
    return f


def _mock_supabase(url: str = FAKE_AUDIO_URL) -> MagicMock:
    mock = MagicMock()
    mock.storage.from_.return_value.upload.return_value = {}
    mock.storage.from_.return_value.get_public_url.return_value = url
    return mock


def _mock_groq_client(transcription: str = FAKE_TRANSCRIPTION, extracted: dict = FAKE_EXTRACTED):
    client = MagicMock()
    transcription_response = MagicMock()
    transcription_response.__str__ = lambda _self: transcription
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
async def test_given_valid_audio_when_processed_then_returns_record():
    # GIVEN
    file = _make_upload_file()
    db = _mock_db()

    # WHEN
    with (
        patch("app.services.transcription_service.supabase", _mock_supabase()),
        patch("app.services.transcription_service.AsyncGroq", return_value=_mock_groq_client()),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN
    assert record.texto_bruto == FAKE_TRANSCRIPTION
    assert record.nome_extraido == "Dona Francisca"
    assert record.especialidade_extraida == "Bordado de renda renascença"
    assert record.url_audio == FAKE_AUDIO_URL
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.anyio
async def test_given_invalid_content_type_when_processed_then_raises_415():
    # GIVEN
    file = _make_upload_file(content_type="image/jpeg", filename="foto.jpg")
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 415
    assert "não suportado" in exc_info.value.detail
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_file_over_25mb_when_processed_then_raises_413():
    # GIVEN — simula cliente sem Content-Length (size=None, leitura completa)
    big_content = b"x" * (25 * 1024 * 1024 + 1)
    file = _make_upload_file(content=big_content)
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 413
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_size_header_over_25mb_when_processed_then_raises_413_before_read():
    # GIVEN — simula Content-Length presente: rejeição acontece antes de ler os bytes
    file = _make_upload_file(size=25 * 1024 * 1024 + 1)
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 413
    # file.read() não deve ter sido chamado
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_supabase_fails_when_upload_then_raises_502():
    # GIVEN
    file = _make_upload_file()
    db = MagicMock()
    mock_supa = MagicMock()
    mock_supa.storage.from_.return_value.upload.side_effect = Exception("connection error")

    # WHEN / THEN
    with (
        patch("app.services.transcription_service.supabase", mock_supa),
        patch("app.services.transcription_service.AsyncGroq", return_value=_mock_groq_client()),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert exc_info.value.status_code == 502
    assert "armazenar" in exc_info.value.detail
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_extraction_fails_when_whisper_ok_then_persists_with_null_fields():
    # GIVEN
    file = _make_upload_file()
    db = _mock_db(extracted={k: None for k in FAKE_EXTRACTED})
    mock_client = _mock_groq_client()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))

    # WHEN
    with (
        patch("app.services.transcription_service.supabase", _mock_supabase()),
        patch("app.services.transcription_service.AsyncGroq", return_value=mock_client),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN — transcrição salva; extração falhou silenciosamente
    assert record.texto_bruto == FAKE_TRANSCRIPTION
    assert record.nome_extraido is None
    assert record.especialidade_extraida is None
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Testes de _upload_audio_to_storage
# ---------------------------------------------------------------------------


def test_given_valid_upload_when_called_then_returns_public_url():
    # GIVEN
    file = _make_upload_file()
    mock_supa = _mock_supabase()

    # WHEN
    with patch("app.services.transcription_service.supabase", mock_supa):
        url = _upload_audio_to_storage(b"bytes", file, FAKE_USUARIO_ID)

    # THEN
    assert url == FAKE_AUDIO_URL
    mock_supa.storage.from_.return_value.upload.assert_called_once()


def test_given_supabase_upload_fails_when_called_then_raises_502():
    # GIVEN
    file = _make_upload_file()
    mock_supa = MagicMock()
    mock_supa.storage.from_.return_value.upload.side_effect = Exception("network error")

    # WHEN / THEN
    with patch("app.services.transcription_service.supabase", mock_supa):
        with pytest.raises(HTTPException) as exc_info:
            _upload_audio_to_storage(b"bytes", file, FAKE_USUARIO_ID)

    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Testes de _transcribe_audio
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_audio_when_whisper_called_then_returns_text():
    # GIVEN
    file = _make_upload_file()
    client = _mock_groq_client()

    # WHEN
    result = await _transcribe_audio(b"audio-bytes", file, client)

    # THEN
    assert result == FAKE_TRANSCRIPTION


@pytest.mark.anyio
async def test_given_whisper_fails_when_called_then_raises_502():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(side_effect=Exception("unknown error"))

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert exc_info.value.status_code == 502
    assert "transcrição" in exc_info.value.detail


@pytest.mark.anyio
async def test_given_rate_limit_when_whisper_called_then_raises_429():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.RateLimitError("rate limit", response=MagicMock(), body=None)
    )

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert exc_info.value.status_code == 429
    assert "Tente novamente" in exc_info.value.detail


@pytest.mark.anyio
async def test_given_connection_error_when_whisper_called_then_raises_502():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.APIConnectionError(request=MagicMock())
    )

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert exc_info.value.status_code == 502
    assert "conectar" in exc_info.value.detail


@pytest.mark.anyio
async def test_given_timeout_when_whisper_called_then_raises_504():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )

    # WHEN / THEN
    with pytest.raises(HTTPException) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert exc_info.value.status_code == 504
    assert "demorou demais" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Testes de _extract_fields
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_response_when_llama_called_then_returns_fields():
    # GIVEN
    client = _mock_groq_client()

    # WHEN
    result = await _extract_fields(FAKE_TRANSCRIPTION, client)

    # THEN
    assert result["nome"] == "Dona Francisca"
    assert result["especialidade"] == "Bordado de renda renascença"


@pytest.mark.anyio
async def test_given_llama_fails_when_called_then_returns_empty_dict():
    # GIVEN
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=Exception("error"))

    # WHEN
    result = await _extract_fields(FAKE_TRANSCRIPTION, client)

    # THEN
    assert result == {}


@pytest.mark.anyio
async def test_given_llm_returns_invalid_types_when_extracted_then_returns_empty_dict():
    # GIVEN — LLM retorna tipos errados (ex: lista no lugar de string)
    client = MagicMock()
    bad_payload = {"nome": ["lista", "invalida"], "telefone": 99999}
    client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(bad_payload)))]
        )
    )

    # WHEN
    result = await _extract_fields(FAKE_TRANSCRIPTION, client)

    # THEN — ValidationError capturado, retorna dict vazio sem quebrar o fluxo
    assert result == {}


# ---------------------------------------------------------------------------
# Testes de AudioTranscriptionResponse (schema)
# ---------------------------------------------------------------------------


def test_given_full_record_when_from_record_called_then_maps_fields_correctly():
    # GIVEN
    record = AudioTranscription(
        usuario_id=FAKE_USUARIO_ID,
        url_audio=FAKE_AUDIO_URL,
        texto_bruto=FAKE_TRANSCRIPTION,
        nome_extraido="Dona Francisca",
        especialidade_extraida="Bordado de renda renascença",
        endereco_extraido="Rua do Cruzeiro, 15",
        historia_extraida=None,
        telefone_extraido="81 99999-0000",
    )
    record.id_transcricao = uuid.uuid4()

    # WHEN
    response = AudioTranscriptionResponse.from_record(record)

    # THEN
    assert response.usuario_id == FAKE_USUARIO_ID
    assert response.texto_bruto == FAKE_TRANSCRIPTION
    assert response.campos_extraidos.nome == "Dona Francisca"
    assert response.campos_extraidos.telefone == "81 99999-0000"
    assert response.sucesso is True


def test_given_record_with_no_extracted_fields_when_from_record_called_then_sucesso_is_false():
    # GIVEN
    record = AudioTranscription(
        usuario_id=FAKE_USUARIO_ID,
        url_audio=None,
        texto_bruto="texto qualquer",
        nome_extraido=None,
        especialidade_extraida=None,
        endereco_extraido=None,
        historia_extraida=None,
        telefone_extraido=None,
    )
    record.id_transcricao = uuid.uuid4()

    # WHEN
    response = AudioTranscriptionResponse.from_record(record)

    # THEN
    assert response.sucesso is False
    assert response.campos_extraidos == ExtractedFieldsResponse()


# ---------------------------------------------------------------------------
# Testes de _get_extension
# ---------------------------------------------------------------------------


def test_given_filename_with_ext_when_called_then_returns_file_extension():
    # GIVEN / WHEN / THEN
    assert _get_extension("audio.webm", None) == "webm"
    assert _get_extension("gravacao.MP3", None) == "mp3"


def test_given_no_filename_when_called_then_uses_content_type():
    # GIVEN / WHEN / THEN
    assert _get_extension(None, "audio/mpeg") == "mp3"
    assert _get_extension(None, "audio/wav") == "wav"
    assert _get_extension(None, "audio/ogg") == "ogg"


def test_given_no_filename_and_no_type_when_called_then_returns_fallback():
    # GIVEN / WHEN / THEN
    assert _get_extension(None, None) == "audio"
    assert _get_extension(None, "audio/desconhecido") == "audio"
