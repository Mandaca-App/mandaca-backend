from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_context import BusinessContext
from app.models.report import AIReport
from app.services.business_context_builder_service import BusinessContextBuilderService
from app.services.business_context_service import BusinessContextService


@dataclass(frozen=True)
class ContextValidationResult:
    context_changed: bool
    saved_context: BusinessContext | None
    current_context_data: dict[str, Any]
    current_context_hash: str
    reusable_report: AIReport | None = None


class ContextValidationService:
    def __init__(
        self,
        context_service: BusinessContextService | None = None,
        context_builder: BusinessContextBuilderService | None = None,
    ) -> None:
        self._context_service = context_service or BusinessContextService()
        self._context_builder = context_builder or BusinessContextBuilderService()

    def validate_for_report(self, empresa_id: UUID, db: Session) -> ContextValidationResult:
        saved_contexts = self._context_service.list_by_enterprise(empresa_id, db)
        saved_context = saved_contexts[0] if saved_contexts else None
        current_context_data = self._context_builder.build_snapshot(empresa_id, db)
        current_context_hash = self._context_service.compute_hash(current_context_data)
        context_changed = (
            saved_context is None or current_context_hash != saved_context.hash_contexto
        )

        reusable_report = None
        if not context_changed and saved_context is not None:
            reusable_report = self._get_latest_report_for_context(saved_context.id_contexto, db)

        return ContextValidationResult(
            context_changed=context_changed,
            saved_context=saved_context,
            current_context_data=current_context_data,
            current_context_hash=current_context_hash,
            reusable_report=reusable_report,
        )

    def _get_latest_report_for_context(self, contexto_id: UUID, db: Session) -> AIReport | None:
        return db.execute(
            select(AIReport)
            .where(AIReport.contexto_id == contexto_id)
            .order_by(AIReport.criado_em.desc())
            .limit(1)
        ).scalar_one_or_none()
