from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    enterprise_id: UUID
    message: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    reply: str
