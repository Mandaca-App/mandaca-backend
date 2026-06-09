from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.services.reservation_service as reservation_service
from app.core.session import get_db
from app.schemas.reservations import (
    ReservationCreate,
    ReservationResponse,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get(
    "/by-enterprise/{empresa_id}",
    response_model=list[ReservationResponse],
    status_code=status.HTTP_200_OK,
)
def list_reservations_by_enterprise(
    empresa_id: UUID,
    db: Session = Depends(get_db),
) -> list[ReservationResponse]:
    return reservation_service.list_by_enterprise(empresa_id, db)


@router.get(
    "/by-user/{usuario_id}",
    response_model=list[ReservationResponse],
    status_code=status.HTTP_200_OK,
)
def list_reservations_by_user(
    usuario_id: UUID,
    db: Session = Depends(get_db),
) -> list[ReservationResponse]:
    return reservation_service.list_by_user(usuario_id, db)


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
)
def get_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    return reservation_service.get_by_id(reservation_id, db)


@router.post(
    "/",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    return reservation_service.create(payload, db)


@router.patch(
    "/{reservation_id}/accept",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
)
def accept_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
) -> ReservationResponse:
    return reservation_service.accept(reservation_id, db)


@router.delete(
    "/{reservation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
):
    reservation_service.delete(reservation_id, db)
    return None
