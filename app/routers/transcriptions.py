from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.transcriptions import EnterpriseFromAudioResponse
from app.services.transcription_service import process_audio_registration

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post(
    "/",
    response_model=EnterpriseFromAudioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_enterprise_from_audio(
    audio: UploadFile = File(..., description="Arquivo de áudio (mp3/wav/webm, máx 25 MB)"),
    usuario_id: UUID = Form(..., description="ID do usuário empreendedor"),
    db: Session = Depends(get_db),
) -> EnterpriseFromAudioResponse:
    """
    Recebe um arquivo de áudio, transcreve com Whisper e extrai os campos
    (nome, especialidade, endereço, história, telefone) para criar a empresa
    do usuário diretamente na tabela de empresas.
    """
    record = await process_audio_registration(
        file=audio,
        usuario_id=usuario_id,
        db=db,
    )
    return EnterpriseFromAudioResponse.model_validate(record)
