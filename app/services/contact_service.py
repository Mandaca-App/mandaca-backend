from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ContactNotFoundError
from app.models.contact import Contact
from app.schemas.contacts import ContactCreate, ContactUpdate


def get_by_id(contact_id: UUID, db: Session) -> Contact:
    """Busca um contato pelo ID ou lança ContactNotFoundError."""
    contact = db.execute(
        select(Contact).where(Contact.id_contato == contact_id)
    ).scalar_one_or_none()
    if not contact:
        raise ContactNotFoundError(contact_id)
    return contact


def list_all(db: Session) -> list[Contact]:
    """Retorna todos os contatos cadastrados."""
    return list(db.execute(select(Contact)).scalars().all())


def create(payload: ContactCreate, db: Session) -> Contact:
    """Cria um novo contato."""
    contact = Contact(
        telefone=payload.telefone,
        email=payload.email,
        whatsapp=payload.whatsapp,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update(contact_id: UUID, payload: ContactUpdate, db: Session) -> Contact:
    """Atualiza os campos de um contato existente."""
    contact = get_by_id(contact_id, db)

    if payload.telefone is not None:
        contact.telefone = payload.telefone
    if payload.email is not None:
        contact.email = payload.email
    if payload.whatsapp is not None:
        contact.whatsapp = payload.whatsapp

    db.commit()
    db.refresh(contact)
    return contact


def delete(contact_id: UUID, db: Session) -> None:
    """Remove um contato pelo ID."""
    contact = get_by_id(contact_id, db)
    db.delete(contact)
    db.commit()
