from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EnterpriseNotFoundError, MenuNotFoundError
from app.core.supabase_client import supabase
from app.models.enterprise import Enterprise
from app.models.menu import Menu
from app.schemas.menus import MenuCreate, MenuUpdate


def _extract_storage_path(public_url: str) -> Optional[str]:
    """Extrai o storage_path relativo ao bucket a partir da URL pública do Supabase."""
    try:
        marker = "/object/public/mandaca-bucket/"
        idx = public_url.index(marker)
        return public_url[idx + len(marker) :]
    except (ValueError, AttributeError):
        return None


def get_by_enterprise(enterprise_id: UUID, db: Session) -> list[Menu]:
    """Retorna todos os menus de uma empresa."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise EnterpriseNotFoundError(enterprise_id)

    return list(
        db.execute(
            select(Menu).where(
                Menu.empresa_id == enterprise_id,
                Menu.status.is_(True),
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
            Menu.status.is_(True),
        )
    ).scalar_one_or_none()

    if not menu:
        raise MenuNotFoundError(menu_id)

    return menu


def list_all(db: Session) -> list[Menu]:
    """Retorna todos os cardápios ativos."""
    return list(db.execute(select(Menu).where(Menu.status.is_(True))).scalars().all())


def create(payload: MenuCreate, foto: Optional[UploadFile], db: Session) -> Menu:
    """Cria um novo cardápio validando a empresa vinculada."""
    enterprise = db.get(Enterprise, payload.empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(payload.empresa_id)

    url_foto_item = None
    if foto is not None:
        if not foto.content_type or not foto.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="O arquivo enviado não é uma imagem válida",
            )
        try:
            file_ext = (
                foto.filename.split(".")[-1] if foto.filename and "." in foto.filename else "jpg"
            )
            storage_path = f"cardapios/{uuid4()}.{file_ext}"
            file_content = foto.file.read()
            supabase.storage.from_("mandaca-bucket").upload(
                file=file_content,
                path=storage_path,
                file_options={"content-type": foto.content_type, "upsert": "false"},
            )
            url_foto_item = supabase.storage.from_("mandaca-bucket").get_public_url(storage_path)
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
        if not foto.content_type or not foto.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="O arquivo enviado não é uma imagem válida",
            )
        try:
            file_ext = (
                foto.filename.split(".")[-1] if foto.filename and "." in foto.filename else "jpg"
            )
            new_storage_path = f"cardapios/{uuid4()}.{file_ext}"
            file_content = foto.file.read()
            supabase.storage.from_("mandaca-bucket").upload(
                file=file_content,
                path=new_storage_path,
                file_options={"content-type": foto.content_type, "upsert": "false"},
            )
            if menu.url_foto_item:
                old_path = _extract_storage_path(menu.url_foto_item)
                if old_path:
                    supabase.storage.from_("mandaca-bucket").remove([old_path])
            menu.url_foto_item = supabase.storage.from_("mandaca-bucket").get_public_url(
                new_storage_path
            )
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
