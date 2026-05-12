from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.tutorial import CategoriaTutorial, Tutorial
from app.schemas.tutorial import TutorialIn, TutorialOut, TutorialUpdate
from app.services.tutorial_service import TutorialService

router = APIRouter(prefix="/api/tutoriais", tags=["tutoriais"])


def get_tutorial_service() -> TutorialService:
    return TutorialService()


def require_admin(x_user_type: str | None = Header(default=None, alias="X-User-Type")) -> None:
    if x_user_type is None or x_user_type.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")


@router.get("", response_model=list[TutorialOut])
def list_tutoriais(
    categoria: CategoriaTutorial | None = None,
    db: Session = Depends(get_db),
    service: TutorialService = Depends(get_tutorial_service),
) -> list[Tutorial]:
    return service.list_active(db, categoria)


@router.post(
    "",
    response_model=TutorialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_tutorial(
    payload: TutorialIn,
    db: Session = Depends(get_db),
    service: TutorialService = Depends(get_tutorial_service),
) -> Tutorial:
    return service.create(db, payload)


@router.put(
    "/{tutorial_id}",
    response_model=TutorialOut,
    dependencies=[Depends(require_admin)],
)
def update_tutorial(
    tutorial_id: UUID,
    payload: TutorialUpdate,
    db: Session = Depends(get_db),
    service: TutorialService = Depends(get_tutorial_service),
) -> Tutorial:
    tutorial = service.update(db, tutorial_id, payload)
    if tutorial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial não encontrado",
        )
    return tutorial


@router.delete(
    "/{tutorial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_tutorial(
    tutorial_id: UUID,
    db: Session = Depends(get_db),
    service: TutorialService = Depends(get_tutorial_service),
):
    deleted = service.delete(db, tutorial_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial não encontrado",
        )
    return None
