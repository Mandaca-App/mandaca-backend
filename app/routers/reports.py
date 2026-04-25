from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.report import AIReport
from app.schemas.auto_apply import ReportAutoApplyResponse
from app.schemas.reports import AIReportDetail, AIReportSummary
from app.services.report_auto_apply_service import ReportAutoApplyService
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def get_report_service() -> ReportService:
    return ReportService()


def get_report_auto_apply_service() -> ReportAutoApplyService:
    return ReportAutoApplyService()


@router.post(
    "/generate/{empresa_id}",
    response_model=AIReportDetail,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    empresa_id: UUID,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> AIReport:
    return service.generate_report(empresa_id, db)


@router.get("/by-enterprise/{empresa_id}", response_model=list[AIReportSummary])
async def list_reports_by_enterprise(
    empresa_id: UUID,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> list[AIReport]:
    return service.list_by_enterprise(empresa_id, db)


@router.get("/{report_id}", response_model=AIReportDetail)
async def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
) -> AIReport:
    return service.get_by_id(report_id, db)


@router.post(
    "/{report_id}/auto-apply",
    response_model=ReportAutoApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def auto_apply_from_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    service: ReportAutoApplyService = Depends(get_report_auto_apply_service),
) -> ReportAutoApplyResponse:
    return service.apply_from_report(report_id, db)
