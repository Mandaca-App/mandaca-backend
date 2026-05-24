from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import app.services.menu_service as menu_service
from app.core.exceptions import InvalidImageTypeError
from app.core.session import get_db
from app.schemas.menus import MenuCreate, MenuResponse, MenuUpdate

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("/by-enterprise/{enterprise_id}", response_model=list[MenuResponse])
def list_menus_by_enterprise(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> list[MenuResponse]:
    return menu_service.get_by_enterprise(enterprise_id, db)


@router.get("/", response_model=list[MenuResponse])
def list_menus(db: Session = Depends(get_db)) -> list[MenuResponse]:
    return menu_service.list_all(db)


@router.get("/{menu_id}", response_model=MenuResponse)
def get_menu(
    menu_id: UUID,
    db: Session = Depends(get_db),
) -> MenuResponse:
    return menu_service.get_by_id(menu_id, db)


@router.post("/", response_model=MenuResponse, status_code=status.HTTP_201_CREATED)
def create_menu(
    payload: MenuCreate = Depends(),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> MenuResponse:
    try:
        return menu_service.create(payload, foto=foto, db=db)
    except InvalidImageTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: UUID,
    payload: MenuUpdate = Depends(),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> MenuResponse:
    try:
        return menu_service.update(menu_id, payload, foto=foto, db=db)
    except InvalidImageTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: UUID,
    db: Session = Depends(get_db),
):
    menu_service.delete(menu_id, db)
    return None
