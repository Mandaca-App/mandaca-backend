import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.orm import Session

import app.services.reservation_chat_service as reservation_chat_service
from app.core.connection_manager import ConnectionManager
from app.core.exceptions import ReservationNotFoundError, SenderNotInReservationError
from app.core.session import get_db
from app.schemas.reservation_chat import (
    ReservationChatIncoming,
    ReservationMessageCreate,
    ReservationMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["reservation-chat"])

manager = ConnectionManager()


@router.get(
    "/{reservation_id}/messages",
    response_model=list[ReservationMessageResponse],
    status_code=status.HTTP_200_OK,
)
def list_messages(
    reservation_id: UUID,
    limit: int = Query(100, ge=1, le=200),
    before_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> list[ReservationMessageResponse]:
    return reservation_chat_service.get_history(reservation_id, db, limit, before_id)


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


@router.websocket("/{reservation_id}/ws")
async def reservation_chat_ws(
    websocket: WebSocket,
    reservation_id: UUID,
    remetente_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    try:
        reservation_chat_service.resolve_membership(reservation_id, remetente_id, db)
    except (ReservationNotFoundError, SenderNotInReservationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(reservation_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            try:
                incoming = ReservationChatIncoming.model_validate(data)
            except ValidationError:
                continue
            message = await run_in_threadpool(
                reservation_chat_service.send_message,
                reservation_id,
                remetente_id,
                incoming.conteudo,
                db,
            )
            payload = ReservationMessageResponse.model_validate(message).model_dump(mode="json")
            await manager.broadcast(reservation_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(reservation_id, websocket)
        logger.info("WS chat reserva %s: client desconectado", reservation_id)
