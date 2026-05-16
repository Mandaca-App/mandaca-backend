from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.services.contact_service as contact_service
from app.core.session import get_db
from app.schemas.contacts import ContactCreate, ContactResponse, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=list[ContactResponse])
def list_contacts(db: Session = Depends(get_db)) -> list[ContactResponse]:
    return contact_service.list_all(db)


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
) -> ContactResponse:
    return contact_service.get_by_id(contact_id, db)


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
) -> ContactResponse:
    return contact_service.create(payload, db)


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
) -> ContactResponse:
    return contact_service.update(contact_id, payload, db)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    contact_service.delete(contact_id, db)
    return None
