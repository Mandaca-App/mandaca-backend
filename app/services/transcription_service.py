import io
import json
import logging
import uuid
from typing import Any

import groq as groq_sdk
from fastapi import HTTPException, UploadFile, status
from groq import AsyncGroq
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enterprise import Enterprise

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/wav",
    "audio/webm",
    "audio/ogg",
    "audio/m4a",
    "audio/x-m4a",
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB — limite do Whisper API

# Vocabulário nordestino como hint para o Whisper melhorar o reconhecimento
# de termos regionais que raramente aparecem em datasets de treinamento
WHISPER_HINT = (
    "renda renascença, bordado, cariri, agreste, sertão, nordeste, "
    "carne de sol, bolo de rolo, tapioca, buchada, sarapatel, pamonha, "
    "empreendedor, microempreendedor, artesanato, gastronomia, pernambuco"
)

_EXTRACTION_SYSTEM_PROMPT = """
Você é um assistente especializado em extrair informações de empreendedores do interior de
Pernambuco. A partir do texto transcrito de um áudio, extraia os campos abaixo em JSON.
Retorne APENAS o JSON, sem explicações. Se um campo não for mencionado, retorne null.

Campos:
- nome: nome do empreendedor ou da empresa (string ou null)
- especialidade: ramo de atividade ou produto principal (string ou null, máx 100 chars)
- endereco: endereço físico mencionado (string ou null, máx 255 chars)
- historia: história pessoal ou do negócio (string ou null, máx 500 chars)
- telefone: número de telefone (string ou null, somente dígitos, espaços e hífens)
"""

_SIZE_EXCEEDED_MSG = "O arquivo de áudio excede o limite de 25 MB."


class _ExtractedFields(BaseModel):
    """Schema interno para validar a saída do LLM antes de persistir."""

    nome: str | None = None
    especialidade: str | None = None
    endereco: str | None = None
    historia: str | None = None
    telefone: str | None = None


async def process_audio_registration(
    file: UploadFile,
    usuario_id: uuid.UUID,
    db: Session,
) -> Enterprise:
    """Transcreve áudio, extrai campos e cria a empresa do usuário em empresas."""
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato de áudio não suportado: {file.content_type}. "
            "Use mp3, wav, webm, ogg ou m4a.",
        )

    if file.size is not None and file.size > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=_SIZE_EXCEEDED_MSG,
        )

    file_content = await file.read()

    if len(file_content) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=_SIZE_EXCEEDED_MSG,
        )

    client = AsyncGroq(api_key=settings.groq_api_key)
    texto_bruto = await _transcribe_audio(file_content, file, client)
    campos = await _extract_fields(texto_bruto, client)

    enterprise = db.query(Enterprise).filter(Enterprise.usuario_id == usuario_id).first()

    if enterprise:
        enterprise.nome = campos.get("nome") or enterprise.nome
        enterprise.especialidade = campos.get("especialidade") or enterprise.especialidade
        enterprise.endereco = campos.get("endereco") or enterprise.endereco
        enterprise.historia = campos.get("historia") or enterprise.historia
        enterprise.telefone = campos.get("telefone") or enterprise.telefone
    else:
        enterprise = Enterprise(
            id_empresa=uuid.uuid4(),
            usuario_id=usuario_id,
            nome=campos.get("nome") or "Empresa sem nome",
            especialidade=campos.get("especialidade"),
            endereco=campos.get("endereco"),
            historia=campos.get("historia"),
            telefone=campos.get("telefone"),
        )
        db.add(enterprise)

    db.commit()
    db.refresh(enterprise)
    return enterprise


async def _transcribe_audio(
    file_content: bytes,
    file: UploadFile,
    client: AsyncGroq,
) -> str:
    """Transcreve o áudio usando Groq Whisper large-v3."""
    file_ext = _get_extension(file.filename, file.content_type)
    filename = file.filename or f"audio.{file_ext}"

    try:
        transcription = await client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename, io.BytesIO(file_content), file.content_type),
            language="pt",
            prompt=WHISPER_HINT,
            response_format="text",
        )
        return str(transcription)
    except groq_sdk.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de requisições da API de transcrição atingido. Tente novamente.",
        )
    except groq_sdk.APITimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="A API de transcrição demorou demais para responder. Tente novamente.",
        )
    except groq_sdk.APIConnectionError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar à API de transcrição. Tente novamente.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha na transcrição do áudio: {exc}",
        )


async def _extract_fields(texto_bruto: str, client: AsyncGroq) -> dict[str, Any]:
    """Extrai campos estruturados do texto transcrito usando Groq LLaMA 3.1 8B."""
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": texto_bruto},
            ],
            max_tokens=512,
            temperature=0,
        )
        raw = json.loads(response.choices[0].message.content)
        return _ExtractedFields.model_validate(raw).model_dump()
    except ValidationError as exc:
        logger.warning("LLM output failed Pydantic validation: %s", exc)
        return {}
    except Exception as exc:
        logger.warning("Field extraction failed, persisting raw text only: %s", exc)
        return {}


def _get_extension(filename: str | None, content_type: str | None) -> str:
    """Determina a extensão do arquivo a partir do nome ou content-type."""
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    _map = {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "audio/x-m4a": "m4a",
    }
    return _map.get(content_type or "", "audio")
