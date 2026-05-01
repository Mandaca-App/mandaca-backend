from uuid import UUID

from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIReportGenerationError,
    AIReportNotFoundError,
)
from app.models.business_context import BusinessContext
from app.models.report import AIReport
from app.services.business_context_service import BusinessContextService
from app.services.context_validation_service import (
    ContextValidationResult,
    ContextValidationService,
)


class ReportService:
    def __init__(
        self,
        gemini_client: genai.Client | None = None,
        context_service: BusinessContextService | None = None,
        context_validation_service: ContextValidationService | None = None,
    ) -> None:
        self._gemini_client = gemini_client or genai.Client(api_key=settings.gemini_api_key)
        self._context_service = context_service or BusinessContextService()
        self._context_validation_service = context_validation_service or ContextValidationService(
            context_service=self._context_service
        )

    def generate_report(self, empresa_id: UUID, db: Session) -> AIReport:
        validation = self._context_validation_service.validate_for_report(empresa_id, db)
        if not validation.context_changed and validation.reusable_report is not None:
            return validation.reusable_report

        contexto = self._resolve_context(validation, empresa_id, db)

        report = AIReport(
            empresa_id=empresa_id,
            contexto_id=contexto.id_contexto,
            pontos_positivos=[],
            melhorias=[],
            recomendacoes=[],
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def _resolve_context(
        self, validation: ContextValidationResult, empresa_id: UUID, db: Session
    ) -> BusinessContext:
        if not validation.context_changed:
            if validation.saved_context is None:
                raise AIReportGenerationError("contexto salvo ausente para contexto inalterado")
            return validation.saved_context

        return self._context_service.create_from_snapshot(
            empresa_id,
            validation.current_context_data,
            validation.current_context_hash,
            db,
        )

    def get_by_id(self, report_id: UUID, db: Session) -> AIReport:
        report = db.get(AIReport, report_id)
        if not report:
            raise AIReportNotFoundError(report_id)
        return report

    def list_by_enterprise(self, empresa_id: UUID, db: Session) -> list[AIReport]:
        return list(
            db.execute(
                select(AIReport)
                .where(AIReport.empresa_id == empresa_id)
                .order_by(AIReport.criado_em.desc())
            )
            .scalars()
            .all()
        )
