from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    EnterpriseNotFoundError,
    InvalidImageTypeError,
    MenuNotFoundError,
    MenuPageEmptyError,
)
from app.core.supabase_client import supabase
from app.models.enterprise import Enterprise
from app.models.menu import CategoriaCardapio, Menu
from app.schemas.menus import MenuBulkCreate, MenuCreate, MenuPaginatedResponse, MenuUpdate

_PAGE_SIZE = 10


def _extract_storage_path(public_url: str) -> Optional[str]:
    """Extrai o storage_path relativo ao bucket a partir da URL pública do Supabase."""
    try:
        marker = "/object/public/mandaca-bucket/"
        idx = public_url.index(marker)
        return public_url[idx + len(marker) :]
    except (ValueError, AttributeError):
        return None


def _upload_photo(foto: UploadFile) -> str:
    """Faz upload de uma foto para o Supabase Storage e retorna a URL pública."""
    if not foto.content_type or not foto.content_type.startswith("image/"):
        raise InvalidImageTypeError()
    file_ext = foto.filename.split(".")[-1] if foto.filename and "." in foto.filename else "jpg"
    storage_path = f"cardapios/{uuid4()}.{file_ext}"
    file_content = foto.file.read()
    supabase.storage.from_("mandaca-bucket").upload(
        file=file_content,
        path=storage_path,
        file_options={"content-type": foto.content_type, "upsert": "false"},
    )
    return supabase.storage.from_("mandaca-bucket").get_public_url(storage_path)


def get_by_enterprise(enterprise_id: UUID, db: Session) -> list[Menu]:
    """Retorna todos os menus de uma empresa."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise EnterpriseNotFoundError(enterprise_id)

    return list(
        db.execute(
            select(Menu).where(
                Menu.empresa_id == enterprise_id,
            )
        )
        .scalars()
        .all()
    )


def get_by_id(menu_id: UUID, db: Session) -> Menu:
    """Busca um cardápio ativo pelo ID ou lança MenuNotFoundError."""
    menu = db.execute(
        select(Menu).where(
            Menu.id_cardapio == menu_id,
        )
    ).scalar_one_or_none()

    if not menu:
        raise MenuNotFoundError(menu_id)

    return menu


def list_all(db: Session) -> list[Menu]:
    """Retorna todos os cardápios."""
    stmt = select(Menu).order_by(Menu.descricao.asc())
    return list(db.scalars(stmt).all())


def create(payload: MenuCreate, foto: Optional[UploadFile], db: Session) -> Menu:
    """Cria um novo cardápio validando a empresa vinculada."""
    enterprise = db.get(Enterprise, payload.empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(payload.empresa_id)

    url_foto_item = None
    if foto is not None:
        try:
            url_foto_item = _upload_photo(foto)
        except InvalidImageTypeError:
            raise
        except Exception:
            url_foto_item = None

    menu = Menu(
        descricao=payload.descricao,
        historia=payload.historia,
        preco=payload.preco,
        categoria=payload.categoria,
        status=payload.status,
        empresa_id=payload.empresa_id,
        url_foto_item=url_foto_item,
    )

    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def update(menu_id: UUID, payload: MenuUpdate, foto: Optional[UploadFile], db: Session) -> Menu:
    """Atualiza os campos de um cardápio."""
    menu = get_by_id(menu_id, db)

    if payload.empresa_id is not None and payload.empresa_id != menu.empresa_id:
        enterprise = db.get(Enterprise, payload.empresa_id)
        if not enterprise:
            raise EnterpriseNotFoundError(payload.empresa_id)
        menu.empresa_id = payload.empresa_id

    if payload.descricao is not None:
        menu.descricao = payload.descricao
    if payload.historia is not None:
        menu.historia = payload.historia
    if payload.preco is not None:
        menu.preco = payload.preco
    if payload.categoria is not None:
        menu.categoria = payload.categoria
    if payload.status is not None:
        menu.status = payload.status

    if foto is not None:
        try:
            new_url = _upload_photo(foto)
            if menu.url_foto_item:
                old_path = _extract_storage_path(menu.url_foto_item)
                if old_path:
                    try:
                        supabase.storage.from_("mandaca-bucket").remove([old_path])
                    except Exception:
                        pass
            menu.url_foto_item = new_url
        except InvalidImageTypeError:
            raise
        except Exception:
            pass

    db.commit()
    db.refresh(menu)
    return menu


def delete(menu_id: UUID, db: Session) -> None:
    """Remove logicamente um cardápio, marcando status como False."""
    menu = get_by_id(menu_id, db)
    menu.status = False
    db.commit()


def list_by_enterprise_paginated(
    empresa_id: UUID,
    page: int,
    categoria: Optional[CategoriaCardapio],
    db: Session,
) -> MenuPaginatedResponse:
    enterprise = db.get(Enterprise, empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(empresa_id)

    offset = (page - 1) * _PAGE_SIZE

    stmt = select(Menu).where(
        Menu.empresa_id == empresa_id,
    )

    if categoria is not None:
        stmt = stmt.where(Menu.categoria == categoria)

    stmt = stmt.order_by(Menu.descricao.asc()).offset(offset).limit(_PAGE_SIZE + 1)

    rows = list(db.scalars(stmt).all())

    if not rows and page > 1:
        raise MenuPageEmptyError(page)

    has_more = len(rows) > _PAGE_SIZE

    return MenuPaginatedResponse(
        page=page,
        items=rows[:_PAGE_SIZE],
        has_more=has_more,
    )


def bulk_create(payload: MenuBulkCreate, db: Session) -> list[Menu]:
    """Insere múltiplos itens em lote, validando todas as empresas antes de persistir."""
    unique_enterprise_ids = {item.empresa_id for item in payload.items}
    for enterprise_id in unique_enterprise_ids:
        if not db.get(Enterprise, enterprise_id):
            raise EnterpriseNotFoundError(enterprise_id)

    menus = [
        Menu(
            descricao=item.descricao,
            historia=item.historia,
            preco=item.preco,
            categoria=item.categoria,
            status=item.status,
            empresa_id=item.empresa_id,
            url_foto_item=item.url_foto_item,
        )
        for item in payload.items
    ]

    db.add_all(menus)
    db.commit()
    for menu in menus:
        db.refresh(menu)
    return menus
