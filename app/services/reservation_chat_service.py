from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.reservation_service as reservation_service
from app.core.exceptions import SenderNotInReservationError
from app.models.enterprise import Enterprise
from app.models.reservation import Reservation
from app.models.reservation_message import ReservationMessage, TipoRemetente


def get_history(
    reserva_id: UUID,
    db: Session,
    limit: int = 100,
    before_id: UUID | None = None,
) -> list[ReservationMessage]:
    """Retorna mensagens de uma reserva ordenadas por data de envio (ASC).

    Com `before_id`, retorna as `limit` mensagens imediatamente anteriores à
    mensagem informada (paginação para carregar histórico mais antigo).
    """
    reservation_service.get_by_id(reserva_id, db)

    query = select(ReservationMessage).where(ReservationMessage.reserva_id == reserva_id)

    if before_id is not None:
        pivot = db.get(ReservationMessage, before_id)
        if pivot is not None:
            query = query.where(ReservationMessage.criado_em < pivot.criado_em)
        messages = list(
            db.execute(query.order_by(ReservationMessage.criado_em.desc()).limit(limit))
            .scalars()
            .all()
        )
        messages.reverse()
        return messages

    return list(
        db.execute(query.order_by(ReservationMessage.criado_em.asc()).limit(limit)).scalars().all()
    )


def send_message(
    reserva_id: UUID, remetente_id: UUID, conteudo: str, db: Session
) -> ReservationMessage:
    """Grava uma mensagem na reserva, derivando o tipo do remetente."""
    tipo_remetente = resolve_membership(reserva_id, remetente_id, db)

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


def resolve_membership(reserva_id: UUID, remetente_id: UUID, db: Session) -> TipoRemetente:
    """Valida que o remetente participa da reserva e retorna seu tipo."""
    reservation = reservation_service.get_by_id(reserva_id, db)
    return _resolve_sender_type(reservation, remetente_id, db)


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
