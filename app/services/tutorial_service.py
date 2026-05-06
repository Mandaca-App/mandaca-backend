from uuid import UUID

from pydantic import HttpUrl, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.models.tutorial import CategoriaTutorial, Tutorial
from app.repositories.tutorial_repository import TutorialRepository
from app.schemas.tutorial import TutorialIn, TutorialUpdate

_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class TutorialService:
    def __init__(self, repository: TutorialRepository | None = None) -> None:
        self._repository = repository or TutorialRepository()

    def list_active(
        self, db: Session, categoria: CategoriaTutorial | None = None
    ) -> list[Tutorial]:
        return self._repository.list_active(db, categoria)

    def create(self, db: Session, payload: TutorialIn) -> Tutorial:
        self._validate_url(payload.url)
        return self._repository.create(db, payload)

    def update(self, db: Session, tutorial_id: UUID, payload: TutorialUpdate) -> Tutorial | None:
        tutorial = self._repository.get_by_id(db, tutorial_id)
        if tutorial is None:
            return None

        if payload.url is not None:
            self._validate_url(payload.url)

        return self._repository.update(db, tutorial, payload)

    def delete(self, db: Session, tutorial_id: UUID) -> bool:
        tutorial = self._repository.get_by_id(db, tutorial_id)
        if tutorial is None:
            return False

        self._repository.delete(db, tutorial)
        return True

    def _validate_url(self, url: str) -> None:
        try:
            _HTTP_URL_ADAPTER.validate_python(url)
        except ValidationError as exc:
            raise ValueError("URL inválida") from exc
