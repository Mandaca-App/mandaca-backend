from uuid import UUID, uuid4
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.core.supabase_client import supabase
from app.models.user import User, TipoUsuario

router = APIRouter(prefix="/users", tags=["users"])

class UserUpdate(BaseModel):
    tipo_usuario: Optional[TipoUsuario] = None
    nome: Optional[str] = None
    cpf: Optional[str] = None
    url_foto_usuario: Optional[str] = None

class UserResponse(BaseModel):
    id_usuario: UUID
    tipo_usuario: TipoUsuario
    nome: str
    cpf: str
    url_foto_usuario: Optional[str] = None
    empresa_id: Optional[UUID] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: User):
        return cls(
            id_usuario=user.id_usuario,
            tipo_usuario=user.tipo_usuario,
            nome=user.nome,
            cpf=user.cpf,
            url_foto_usuario=user.url_foto_usuario,
            empresa_id=user.empresa.id_empresa if user.empresa else None,
        )


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """Endpoint que retorna uma lista de todos os objetos da entidade usuario no formato 'UserResponse' """
    users = db.query(User).all()
    return [UserResponse.from_user(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Endpoint que retorna um objeto de um usuario específico pelo ID no formato 'UserResponse'. """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return UserResponse.from_user(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    tipo_usuario: TipoUsuario = Form(TipoUsuario.TURISTA),
    nome: str = Form(...),
    cpf: str = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Cria um novo usuário. Se um arquivo de imagem for enviado, tenta salvá-lo no Supabase."""
    existing = db.query(User).filter(User.cpf == cpf).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado",
        )

    url_foto_usuario = None

    if foto is not None:
        if not foto.content_type or not foto.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado não é uma imagem válida",
            )

        try:
            file_ext = foto.filename.split(".")[-1] if foto.filename and "." in foto.filename else "jpg"
            storage_path = f"usuarios/{uuid4()}.{file_ext}"

            file_content = await foto.read()

            supabase.storage.from_("mandaca-bucket").upload(
                file=file_content,
                path=storage_path,
                file_options={
                    "content-type": foto.content_type,
                    "upsert": "false",
                },
            )

            url_foto_usuario = supabase.storage.from_("mandaca-bucket").get_public_url(storage_path)

        except Exception:
            url_foto_usuario = None

    user = User(
        tipo_usuario=tipo_usuario,
        nome=nome,
        cpf=cpf,
        url_foto_usuario=url_foto_usuario,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.from_user(user)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID,payload: UserUpdate,db: Session = Depends(get_db),):
    """Endpoint que atualiza os dados de um usuário específico informando o ID."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    if payload.cpf is not None and payload.cpf != user.cpf:
        existing_cpf = (
            db.query(User)
            .filter(
                User.cpf == payload.cpf,
                User.id_usuario != user_id,
            )
            .first()
        )
        if existing_cpf:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF já em uso",
            )
        user.cpf = payload.cpf

    if payload.tipo_usuario is not None:
        user.tipo_usuario = payload.tipo_usuario
    if payload.nome is not None:
        user.nome = payload.nome
    if payload.url_foto_usuario is not None:
        user.url_foto_usuario = payload.url_foto_usuario

    db.commit()
    db.refresh(user)

    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """Endpoint que remove um usuário específico pelo ID."""
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    db.delete(user)
    db.commit()
    return None