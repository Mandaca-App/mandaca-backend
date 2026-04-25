from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.chat import ChatHistoryResponse, ChatMessageCreate, ChatMessageResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageCreate,
    db: Session = Depends(get_db),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    reply = await service.send_message(body.mensagem, body.empresa_id, db)
    return ChatMessageResponse(reply=reply)


@router.get("/history/{enterprise_id}", response_model=ChatHistoryResponse)
def get_history(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    historico = service.get_chat_history(enterprise_id, db)
    return ChatHistoryResponse(historico=historico)
