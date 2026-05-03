from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AIReportNotFoundError, AutoApplyPersistenceError, MandacaError
from app.models.report import AIReport
from app.schemas.auto_apply import (
    AutoApplyRequest,
    AutoApplySuggestion,
    AutoApplySuggestionResult,
    ReportAutoApplyResponse,
    SuggestionStatus,
)
from app.schemas.reports import ReportItem
from app.services.auto_apply_service import AutoApplyService


class ReportAutoApplyService:
    def __init__(
        self,
        auto_apply_service: AutoApplyService | None = None,
    ) -> None:
        self._auto_apply_service = auto_apply_service or AutoApplyService()

    def apply_from_report(self, report_id: UUID, db: Session) -> ReportAutoApplyResponse:
        report = self._load_report(report_id, db)

        raw_items = (
            (report.pontos_positivos or [])
            + (report.melhorias or [])
            + (report.recomendacoes or [])
        )
        candidates = [
            ReportItem(**item)
            for item in raw_items
            if item.get("pode_auto_aplicar") and item.get("sugestao")
        ]

        resultados = [self._apply_one(report.empresa_id, item.sugestao, db) for item in candidates]
        aplicadas = sum(1 for r in resultados if r.status == SuggestionStatus.APPLIED)

        if aplicadas > 0:
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                raise AutoApplyPersistenceError() from exc

        return ReportAutoApplyResponse(
            report_id=report_id,
            total=len(resultados),
            aplicadas=aplicadas,
            rejeitadas=len(resultados) - aplicadas,
            resultados=resultados,
        )

    def _load_report(self, report_id: UUID, db: Session) -> AIReport:
        report = db.get(AIReport, report_id)
        if not report:
            raise AIReportNotFoundError(report_id)
        return report

    def _apply_one(
        self,
        empresa_id: UUID,
        sugestao: AutoApplySuggestion,
        db: Session,
    ) -> AutoApplySuggestionResult:
        try:
            request = AutoApplyRequest(
                enterprise_id=empresa_id,
                target=sugestao.target,
                menu_item_id=sugestao.menu_item_id,
                campo_para_alterar=sugestao.campo_para_alterar,
                novo_valor=sugestao.novo_valor,
            )
            self._auto_apply_service.apply(request, db, commit=False)
            return AutoApplySuggestionResult(
                sugestao=sugestao,
                status=SuggestionStatus.APPLIED,
            )
        except (MandacaError, ValueError) as exc:
            return AutoApplySuggestionResult(
                sugestao=sugestao,
                status=SuggestionStatus.REJECTED,
                erro=str(exc),
            )
