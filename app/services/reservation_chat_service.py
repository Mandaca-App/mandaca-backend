from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.reservation_service as reservation_service
from app.core.exceptions import SenderNotInReservationError
from app.models.enterprise import Enterprise
from app.models.reservation import Reservation
from app.models.reservation_message import ReservationMessage, TipoRemetente


def get_history(reserva_id: UUID, db: Session) -> list[ReservationMessage]:
    """Retorna as mensagens de uma reserva ordenadas por data de envio."""
    reservation_service.get_by_id(reserva_id, db)

    return list(
        db.execute(
            select(ReservationMessage)
            .where(ReservationMessage.reserva_id == reserva_id)
            .order_by(ReservationMessage.criado_em.asc())
        )
        .scalars()
        .all()
    )


def send_message(
    reserva_id: UUID, remetente_id: UUID, conteudo: str, db: Session
) -> ReservationMessage:
    """Grava uma mensagem na reserva, derivando o tipo do remetente."""
    reservation = reservation_service.get_by_id(reserva_id, db)
    tipo_remetente = _resolve_sender_type(reservation, remetente_id, db)

    message = ReservationMessage(
        reserva_id=reserva_id,
        remetente_id=remetente_id,
        tipo_remetente=tipo_remetente,
        conteudo=conteudo,
    )

    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def _resolve_sender_type(
    reservation: Reservation, remetente_id: UUID, db: Session
) -> TipoRemetente:
    """Identifica se o remetente é o turista da reserva ou o dono da empresa."""
    if remetente_id == reservation.usuario_id:
        return TipoRemetente.TURISTA

    enterprise = db.get(Enterprise, reservation.empresa_id)
    if enterprise is not None and enterprise.usuario_id == remetente_id:
        return TipoRemetente.EMPREENDEDOR

    raise SenderNotInReservationError(remetente_id)
