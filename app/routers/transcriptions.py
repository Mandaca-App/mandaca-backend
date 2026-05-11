from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.transcriptions import AudioTranscriptionResponse, EnterpriseFromAudioResponse
from app.services.transcription_service import process_audio_registration, transcribe_audio_only

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


@router.post(
    "/chat",
    response_model=AudioTranscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Arquivo de áudio (máx 25 MB)"),
) -> AudioTranscriptionResponse:
    """Transcreve um arquivo de áudio e retorna apenas o texto — sem persistência no BD.
    Usado pelo chatbot para converter a mensagem de voz do usuário em texto"""
    texto = await transcribe_audio_only(file=audio)
    return AudioTranscriptionResponse(transcription=texto)
