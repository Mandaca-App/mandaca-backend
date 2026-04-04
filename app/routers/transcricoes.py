from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.audio_transcription import AudioTranscription
from app.services.transcription_service import process_audio_registration

router = APIRouter(prefix="/transcricoes", tags=["transcricoes"])


class CamposExtaidosResponse(BaseModel):
    nome: str | None = None
    especialidade: str | None = None
    endereco: str | None = None
    historia: str | None = None
    telefone: str | None = None


class AudioTranscricaoResponse(BaseModel):
    id_transcricao: UUID
    usuario_id: UUID
    url_audio: str | None = None
    texto_bruto: str | None = None
    campos_extraidos: CamposExtaidosResponse
    sucesso: bool

    model_config = {"from_attributes": False}

    @classmethod
    def from_record(cls, record: AudioTranscription) -> "AudioTranscricaoResponse":
        return cls(
            id_transcricao=record.id_transcricao,
            usuario_id=record.usuario_id,
            url_audio=record.url_audio,
            texto_bruto=record.texto_bruto,
            campos_extraidos=CamposExtaidosResponse(
                nome=record.nome_extraido,
                especialidade=record.especialidade_extraida,
                endereco=record.endereco_extraido,
                historia=record.historia_extraida,
                telefone=record.telefone_extraido,
            ),
            sucesso=bool(
                record.nome_extraido
                or record.especialidade_extraida
                or record.endereco_extraido
            ),
        )


@router.post(
    "/",
    response_model=AudioTranscricaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_transcricao(
    audio: UploadFile = File(..., description="Arquivo de áudio (mp3/wav/webm, máx 25 MB)"),
    usuario_id: UUID = Form(..., description="ID do usuário empreendedor"),
    db: Session = Depends(get_db),
) -> AudioTranscricaoResponse:
    """
    Recebe um arquivo de áudio, transcreve e extrai campos estruturados
    (nome, especialidade, endereço, história, telefone) para pré-preencher
    o formulário de cadastro da empresa.
    """
    record = await process_audio_registration(
        file=audio,
        usuario_id=usuario_id,
        db=db,
    )
    return AudioTranscricaoResponse.from_record(record)
