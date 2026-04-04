from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.transcriptions import AudioTranscriptionResponse
from app.services.transcription_service import process_audio_registration

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post(
    "/",
    response_model=AudioTranscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transcription(
    audio: UploadFile = File(..., description="Arquivo de áudio (mp3/wav/webm, máx 25 MB)"),
    usuario_id: UUID = Form(..., description="ID do usuário empreendedor"),
    db: Session = Depends(get_db),
) -> AudioTranscriptionResponse:
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
    return AudioTranscriptionResponse.from_record(record)
