from typing import Annotated, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.core.supabase_client import supabase
from app.models.enterprise import Enterprise
from app.models.photo import Photo

router = APIRouter(prefix="/photos", tags=["photos"])


class PhotoUpdate(BaseModel):
    url_foto_empresa: Optional[str] = None
    empresa_id: Optional[UUID] = None


class PhotoResponse(BaseModel):
    id_foto: UUID
    url_foto_empresa: Optional[str] = None
    empresa_id: UUID

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[PhotoResponse])
def list_photos(db: Session = Depends(get_db)):
    """Retorna uma lista de todos os objetos da entidade foto no formato 'PhotoResponse'."""
    return db.query(Photo).all()


@router.get("/{photo_id}", response_model=PhotoResponse)
def get_photo(photo_id: UUID, db: Session = Depends(get_db)):
    """Endpoint que retorna um objeto de uma foto específica pelo ID no formato 'PhotoResponse'."""
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto não encontrada",
        )
    return photo


@router.get("/enterprise/{enterprise_id}", response_model=list[PhotoResponse])
def list_photos_by_enterprise(enterprise_id: UUID, db: Session = Depends(get_db)):
    """Endpoint que retorna todas as fotos de uma empresa específica pelo ID."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )

    return db.query(Photo).filter(Photo.empresa_id == enterprise_id).all()


@router.post("/", response_model=list[PhotoResponse], status_code=status.HTTP_201_CREATED)
async def create_photos(
    files: Annotated[list[UploadFile], File()],
    empresa_id: UUID = Form(...),
    db: Session = Depends(get_db),
):
    """Cria novas fotos vinculadas a uma empresa a partir dos arquivos enviados."""

    enterprise = db.get(Enterprise, empresa_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa vinculada não encontrada",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum arquivo foi enviado",
        )

    photos_created = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O arquivo '{file.filename}' não é uma imagem válida",
            )

        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        storage_path = f"empresas/{empresa_id}/{uuid4()}.{file_ext}"

        try:
            file_content = await file.read()

            supabase.storage.from_("mandaca-bucket").upload(
                file=file_content,
                path=storage_path,
                file_options={
                    "content-type": file.content_type,
                    "upsert": "false",
                },
            )

            public_url = supabase.storage.from_("mandaca-bucket").get_public_url(storage_path)

            photo = Photo(
                url_foto_empresa=public_url,
                empresa_id=empresa_id,
            )

            db.add(photo)
            photos_created.append(photo)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao enviar a imagem '{file.filename}': {str(e)}",
            )

    db.commit()

    for photo in photos_created:
        db.refresh(photo)

    return photos_created


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(photo_id: UUID, db: Session = Depends(get_db)):
    """Endpoint que remove uma foto específica informada pelo ID."""
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto não encontrada",
        )

    db.delete(photo)
    db.commit()

    return None
