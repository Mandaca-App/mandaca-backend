from fastapi import APIRouter, Depends

from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    # body.enterprise_id sera usado pelo SCRUM-49 (persistencia do historico)
    reply = await service.send_message(body.message)
    return ChatMessageResponse(reply=reply)
