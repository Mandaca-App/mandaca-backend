from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.auto_apply import AutoApplyRequest, AutoApplyResponse
from app.services.auto_apply_service import AutoApplyService

router = APIRouter(prefix="/auto-apply", tags=["auto-apply"])


def get_auto_apply_service() -> AutoApplyService:
    return AutoApplyService()


@router.post(
    "",
    response_model=AutoApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def auto_apply(
    payload: AutoApplyRequest,
    db: Session = Depends(get_db),
    service: AutoApplyService = Depends(get_auto_apply_service),
) -> AutoApplyResponse:
    return service.apply(payload, db)
