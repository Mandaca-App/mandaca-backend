from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.services.reservation_chat_service as reservation_chat_service
from app.core.session import get_db
from app.schemas.reservation_chat import (
    ReservationMessageCreate,
    ReservationMessageResponse,
)

router = APIRouter(prefix="/chat", tags=["reservation-chat"])


@router.get(
    "/{reservation_id}/messages",
    response_model=list[ReservationMessageResponse],
    status_code=status.HTTP_200_OK,
)
def list_messages(
    reservation_id: UUID,
    db: Session = Depends(get_db),
) -> list[ReservationMessageResponse]:
    return reservation_chat_service.get_history(reservation_id, db)


@router.post(
    "/{reservation_id}/messages",
    response_model=ReservationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    reservation_id: UUID,
    payload: ReservationMessageCreate,
    db: Session = Depends(get_db),
) -> ReservationMessageResponse:
    return reservation_chat_service.send_message(
        reservation_id, payload.remetente_id, payload.conteudo, db
    )
