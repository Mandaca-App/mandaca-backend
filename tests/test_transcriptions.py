"""
Testes unitários para TranscriptionService (SCRUM-84).

Foco: lógica do service isolada.
Estratégia: todas as dependências externas são mockadas:
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
from fastapi import UploadFile

from app.core.exceptions import (
    AudioRateLimitError,
    AudioServiceConnectionError,
    AudioServiceTimeoutError,
    AudioTooLargeError,
    AudioTranscriptionError,
    GeocodingUnavailableError,
    UnsupportedAudioFormatError,
)
from app.models.enterprise import Enterprise
from app.schemas.transcriptions import EnterpriseFromAudioResponse  # noqa: F401
from app.services.transcription_service import (
    _extract_fields,
    _get_extension,
    _transcribe_audio,
    process_audio_registration,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_USUARIO_ID = uuid.uuid4()
FAKE_EMPRESA_ID = uuid.uuid4()
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


def _mock_groq_client(transcription: str = FAKE_TRANSCRIPTION, extracted: dict = FAKE_EXTRACTED):
    client = MagicMock()
    transcription_response = MagicMock()
    transcription_response.__str__ = lambda _self: transcription
    client.audio.transcriptions.create = AsyncMock(return_value=transcription_response)
    chat_response = MagicMock()
    chat_response.choices[0].message.content = json.dumps(extracted)
    client.chat.completions.create = AsyncMock(return_value=chat_response)
    return client


def _mock_db(extracted: dict = FAKE_EXTRACTED, existing: Enterprise | None = None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = existing

    def _fake_refresh(obj):
        obj.id_empresa = FAKE_EMPRESA_ID
        obj.usuario_id = FAKE_USUARIO_ID
        obj.nome = extracted.get("nome") or "Empresa sem nome"
        obj.especialidade = extracted.get("especialidade")
        obj.endereco = extracted.get("endereco")
        obj.historia = extracted.get("historia")
        obj.telefone = extracted.get("telefone")

    db.refresh.side_effect = _fake_refresh
    return db


# ---------------------------------------------------------------------------
# Testes de process_audio_registration (função principal)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_audio_when_processed_then_creates_enterprise():
    # GIVEN
    file = _make_upload_file()
    db = _mock_db()

    # WHEN
    with (
        patch("app.services.transcription_service.AsyncGroq", return_value=_mock_groq_client()),
        patch(
            "app.services.transcription_service.geocode_address",
            new=AsyncMock(return_value=(-8.2827, -35.9756)),
        ),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN
    assert record.nome == "Dona Francisca"
    assert record.especialidade == "Bordado de renda renascença"
    assert record.usuario_id == FAKE_USUARIO_ID
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.anyio
async def test_given_invalid_content_type_when_processed_then_raises_415():
    # GIVEN
    file = _make_upload_file(content_type="image/jpeg", filename="foto.jpg")
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(UnsupportedAudioFormatError) as exc_info:
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    assert "não suportado" in str(exc_info.value)
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_file_over_25mb_when_processed_then_raises_413():
    # GIVEN — simula cliente sem Content-Length (size=None, leitura completa)
    big_content = b"x" * (25 * 1024 * 1024 + 1)
    file = _make_upload_file(content=big_content)
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(AudioTooLargeError):
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_size_header_over_25mb_when_processed_then_raises_413_before_read():
    # GIVEN — simula Content-Length presente: rejeição acontece antes de ler os bytes
    file = _make_upload_file(size=25 * 1024 * 1024 + 1)
    db = MagicMock()

    # WHEN / THEN
    with pytest.raises(AudioTooLargeError):
        await process_audio_registration(file, FAKE_USUARIO_ID, db)

    db.add.assert_not_called()


@pytest.mark.anyio
async def test_given_extraction_fails_when_whisper_ok_then_persists_with_null_fields():
    # GIVEN — sem empresa existente, extração falha
    file = _make_upload_file()
    db = _mock_db(extracted={k: None for k in FAKE_EXTRACTED}, existing=None)
    mock_client = _mock_groq_client()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))

    # WHEN
    with patch("app.services.transcription_service.AsyncGroq", return_value=mock_client):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN — empresa criada com campos nulos; extração falhou silenciosamente
    assert record.nome == "Empresa sem nome"
    assert record.especialidade is None
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_given_existing_enterprise_when_processed_then_updates_fields():
    # GIVEN — usuário já tem empresa; novo áudio deve atualizar os campos
    file = _make_upload_file()
    existing = Enterprise(
        usuario_id=FAKE_USUARIO_ID,
        nome="Nome antigo",
        especialidade=None,
        endereco=None,
        historia=None,
        telefone=None,
    )
    existing.id_empresa = FAKE_EMPRESA_ID
    db = _mock_db(existing=existing)

    # WHEN
    with (
        patch("app.services.transcription_service.AsyncGroq", return_value=_mock_groq_client()),
        patch(
            "app.services.transcription_service.geocode_address",
            new=AsyncMock(return_value=(-8.2827, -35.9756)),
        ),
    ):
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN — update, não insert
    db.add.assert_not_called()
    db.commit.assert_called_once()
    assert record.nome == "Dona Francisca"


@pytest.mark.anyio
async def test_given_geocoding_fails_when_audio_processed_then_persists_without_coords():
    # GIVEN — endereco extraido mas geocoder indisponivel; deve continuar sem coordenadas
    file = _make_upload_file()
    db = _mock_db()

    with (
        patch("app.services.transcription_service.AsyncGroq", return_value=_mock_groq_client()),
        patch(
            "app.services.transcription_service.geocode_address",
            new=AsyncMock(side_effect=GeocodingUnavailableError()),
        ),
    ):
        # WHEN
        record = await process_audio_registration(file, FAKE_USUARIO_ID, db)

    # THEN — empresa criada sem lat/lng, sem excecao propagada
    assert record.nome == "Dona Francisca"
    assert record.endereco == "Rua do Cruzeiro, 15, Cariri"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.latitude is None
    assert added.longitude is None


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
    with pytest.raises(AudioTranscriptionError) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert "transcrição" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_rate_limit_when_whisper_called_then_raises_429():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.RateLimitError("rate limit", response=MagicMock(), body=None)
    )

    # WHEN / THEN
    with pytest.raises(AudioRateLimitError) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert "Tente novamente" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_connection_error_when_whisper_called_then_raises_502():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.APIConnectionError(request=MagicMock())
    )

    # WHEN / THEN
    with pytest.raises(AudioServiceConnectionError) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert "conectar" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_timeout_when_whisper_called_then_raises_504():
    # GIVEN
    file = _make_upload_file()
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )

    # WHEN / THEN
    with pytest.raises(AudioServiceTimeoutError) as exc_info:
        await _transcribe_audio(b"audio-bytes", file, client)

    assert "demorou demais" in str(exc_info.value)


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
# Testes de EnterpriseFromAudioResponse (schema)
# ---------------------------------------------------------------------------


def test_given_full_record_when_schema_validated_then_maps_fields_correctly():
    # GIVEN
    record = Enterprise(
        usuario_id=FAKE_USUARIO_ID,
        nome="Dona Francisca",
        especialidade="Bordado de renda renascença",
        endereco="Rua do Cruzeiro, 15",
        historia=None,
        telefone="81 99999-0000",
    )
    record.id_empresa = FAKE_EMPRESA_ID

    # WHEN
    response = EnterpriseFromAudioResponse.model_validate(record)

    # THEN
    assert response.usuario_id == FAKE_USUARIO_ID
    assert response.nome == "Dona Francisca"
    assert response.especialidade == "Bordado de renda renascença"
    assert response.telefone == "81 99999-0000"
    assert response.historia is None


def test_given_record_with_no_optional_fields_when_schema_validated_then_nulls_ok():
    # GIVEN
    record = Enterprise(
        usuario_id=FAKE_USUARIO_ID,
        nome="Empresa sem nome",
        especialidade=None,
        endereco=None,
        historia=None,
        telefone=None,
    )
    record.id_empresa = FAKE_EMPRESA_ID

    # WHEN
    response = EnterpriseFromAudioResponse.model_validate(record)

    # THEN
    assert response.nome == "Empresa sem nome"
    assert response.especialidade is None
    assert response.endereco is None


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
