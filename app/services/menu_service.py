from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EnterpriseNotFoundError
from app.models.enterprise import Enterprise
from app.models.menu import Menu
from app.schemas.menus import MenuCreate, MenuUpdate


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
    """Busca um cardápio ativo pelo ID ou lança 404."""
    menu = db.execute(
        select(Menu).where(
            Menu.id_cardapio == menu_id,
            Menu.status.is_(True),
        )
    ).scalar_one_or_none()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cardápio {menu_id} não encontrado.",
        )

    return menu


def list_all(db: Session) -> list[Menu]:
    """Retorna todos os cardápios ativos."""
    return list(db.execute(select(Menu).where(Menu.status.is_(True))).scalars().all())


def create(payload: MenuCreate, db: Session) -> Menu:
    """Cria um novo cardápio validando a empresa vinculada."""
    enterprise = db.get(Enterprise, payload.empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(payload.empresa_id)

    menu = Menu(
        descricao=payload.descricao,
        historia=payload.historia,
        preco=payload.preco,
        categoria=payload.categoria,
        status=payload.status,
        empresa_id=payload.empresa_id,
    )

    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def update(menu_id: UUID, payload: MenuUpdate, db: Session) -> Menu:
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

    db.commit()
    db.refresh(menu)
    return menu


def delete(menu_id: UUID, db: Session) -> None:
    """Remove logicamente um cardápio, marcando status como False."""
    menu = db.get(Menu, menu_id)
    if not menu or menu.status is False:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cardápio não encontrado",
        )

    menu.status = False
    db.commit()
