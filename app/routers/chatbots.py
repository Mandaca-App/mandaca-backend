from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.chatbot import Chatbot, ChatbotKind, ChatbotKnowledgeModule
from app.schemas.chat import ChatMessageResponse
from app.schemas.chatbot import (
    ChatbotCreate,
    ChatbotMessageCreate,
    ChatbotOut,
    ChatbotUpdate,
    KnowledgeModuleCreate,
    KnowledgeModuleOut,
)
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


def get_chatbot_service() -> ChatbotService:
    return ChatbotService()


@router.get("", response_model=list[ChatbotOut])
def list_chatbots(
    tipo: ChatbotKind | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> list[Chatbot]:
    return service.list_chatbots(db, tipo=tipo, active_only=active_only)


@router.post("", response_model=ChatbotOut, status_code=status.HTTP_201_CREATED)
def create_chatbot(
    payload: ChatbotCreate,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> Chatbot:
    return service.create_chatbot(db, payload)


@router.get("/{tipo}", response_model=ChatbotOut)
def get_chatbot(
    tipo: ChatbotKind,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> Chatbot:
    return service.get_by_type(db, tipo)


@router.put("/{chatbot_id}", response_model=ChatbotOut)
def update_chatbot(
    chatbot_id: UUID,
    payload: ChatbotUpdate,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> Chatbot:
    return service.update_chatbot(db, chatbot_id, payload)


@router.get("/{chatbot_id}/modules", response_model=list[KnowledgeModuleOut])
def list_modules(
    chatbot_id: UUID,
    active_only: bool = False,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> list[ChatbotKnowledgeModule]:
    return service.list_modules(db, chatbot_id, active_only=active_only)


@router.post(
    "/{chatbot_id}/modules",
    response_model=KnowledgeModuleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_module(
    chatbot_id: UUID,
    payload: KnowledgeModuleCreate,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> ChatbotKnowledgeModule:
    return service.create_module(db, chatbot_id, payload)


@router.post("/{tipo}/message", response_model=ChatMessageResponse)
def send_chatbot_message(
    tipo: ChatbotKind,
    payload: ChatbotMessageCreate,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(get_chatbot_service),
) -> ChatMessageResponse:
    reply = service.send_message(db, tipo, payload)
    return ChatMessageResponse(reply=reply)
