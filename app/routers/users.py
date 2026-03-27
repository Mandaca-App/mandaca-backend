from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.user import User, TipoUsuario

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    tipo_usuario: Optional[TipoUsuario] = TipoUsuario.TURISTA
    nome: str
    cpf: str
    empresa_id: Optional[UUID] = None
    url_foto_usuario: Optional[str] = None


class UserResponse(BaseModel):
    id_usuario: UUID
    tipo_usuario: TipoUsuario
    nome: str
    cpf: str
    empresa_id: Optional[UUID] = None
    url_foto_usuario: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.cpf == payload.cpf).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado",
        )

    user = User(
        tipo_usuario=payload.tipo_usuario,
        nome=payload.nome,
        cpf=payload.cpf,
        empresa_id=payload.empresa_id,
        url_foto_usuario=payload.url_foto_usuario,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user