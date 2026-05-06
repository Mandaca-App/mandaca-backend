from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.models.tutorial import CategoriaTutorial, Tutorial
from app.schemas.tutorial import TutorialIn, TutorialUpdate


class TutorialRepository:
    def list_active(
        self, db: Session, categoria: CategoriaTutorial | None = None
    ) -> list[Tutorial]:
        stmt = select(Tutorial).where(Tutorial.ativo.is_(True))
        if categoria is not None:
            stmt = stmt.where(Tutorial.categoria == categoria)

        return list(
            db.execute(stmt.order_by(cast(Tutorial.categoria, String).asc(), Tutorial.ordem.asc()))
            .scalars()
            .all()
        )

    def get_by_id(self, db: Session, tutorial_id: UUID) -> Tutorial | None:
        return db.get(Tutorial, tutorial_id)

    def create(self, db: Session, payload: TutorialIn) -> Tutorial:
        tutorial = Tutorial(**payload.model_dump())
        db.add(tutorial)
        db.commit()
        db.refresh(tutorial)
        return tutorial

    def update(self, db: Session, tutorial: Tutorial, payload: TutorialUpdate) -> Tutorial:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(tutorial, field, value)

        db.commit()
        db.refresh(tutorial)
        return tutorial

    def delete(self, db: Session, tutorial: Tutorial) -> None:
        db.delete(tutorial)
        db.commit()
