from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    EnterpriseNotFoundError,
    ReservationNotFoundError,
    UserNotFoundError,
)
from app.models.enterprise import Enterprise
from app.models.reservation import Reservation, StatusReserva
from app.models.user import User
from app.schemas.reservations import ReservationCreate


def get_by_id(reservation_id: UUID, db: Session) -> Reservation:
    """Busca uma reserva pelo ID ou lança ReservationNotFoundError."""
    reservation = db.execute(
        select(Reservation).where(Reservation.id_reserva == reservation_id)
    ).scalar_one_or_none()

    if not reservation:
        raise ReservationNotFoundError(reservation_id)

    return reservation


def list_by_enterprise(empresa_id: UUID, db: Session) -> list[Reservation]:
    """Retorna todas as reservas de uma empresa."""
    enterprise = db.get(Enterprise, empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(empresa_id)

    return list(
        db.execute(
            select(Reservation)
            .where(Reservation.empresa_id == empresa_id)
            .order_by(Reservation.status.asc())
        )
        .scalars()
        .all()
    )


def list_by_user(usuario_id: UUID, db: Session) -> list[Reservation]:
    """Retorna todas as reservas de um usuário."""
    user = db.get(User, usuario_id)
    if not user:
        raise UserNotFoundError(usuario_id)

    return list(
        db.execute(
            select(Reservation)
            .where(Reservation.usuario_id == usuario_id)
            .order_by(Reservation.status.asc())
        )
        .scalars()
        .all()
    )


def create(payload: ReservationCreate, db: Session) -> Reservation:
    """Cria uma reserva com status inicial AGUARDANDO."""
    if payload.empresa_id is not None:
        enterprise = db.get(Enterprise, payload.empresa_id)
        if not enterprise:
            raise EnterpriseNotFoundError(payload.empresa_id)

    if payload.usuario_id is not None:
        user = db.get(User, payload.usuario_id)
        if not user:
            raise UserNotFoundError(payload.usuario_id)

    reservation = Reservation(
        num_mesas=payload.num_mesas,
        num_pessoas=payload.num_pessoas,
        mensagem=payload.mensagem,
        status=StatusReserva.AGUARDANDO,
        usuario_id=payload.usuario_id,
        empresa_id=payload.empresa_id,
    )

    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def accept(reservation_id: UUID, db: Session) -> Reservation:
    """Aceita uma reserva, alterando o status para ACEITO."""
    reservation = get_by_id(reservation_id, db)
    reservation.status = StatusReserva.ACEITO
    db.commit()
    db.refresh(reservation)
    return reservation


def delete(reservation_id: UUID, db: Session) -> None:
    """Remove fisicamente uma reserva do banco de dados (cancelamento)."""
    reservation = get_by_id(reservation_id, db)
    db.delete(reservation)
    db.commit()
