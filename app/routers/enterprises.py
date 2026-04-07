from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.services.enterprise_service as enterprise_service
from app.core.session import get_db
from app.schemas.enterprises import (
    EnterpriseCreate,
    EnterpriseOverviewResponse,
    EnterprisePercentageResponse,
    EnterpriseResponse,
    EnterpriseUpdate,
)

router = APIRouter(prefix="/enterprises", tags=["enterprises"])


@router.get("/overview", response_model=EnterpriseOverviewResponse)
def get_enterprise_overview(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> EnterpriseOverviewResponse:
    return enterprise_service.get_overview(enterprise_id, db)


@router.get("/", response_model=list[EnterpriseResponse])
def list_enterprises(db: Session = Depends(get_db)) -> list[EnterpriseResponse]:
    return enterprise_service.list_all(db)


@router.get("/percentage/{enterprise_id}", response_model=EnterprisePercentageResponse)
def enterprise_percentage(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> EnterprisePercentageResponse:
    return enterprise_service.get_percentage(enterprise_id, db)


@router.get("/{enterprise_id}", response_model=EnterpriseResponse)
def get_enterprise(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> EnterpriseResponse:
    return enterprise_service.get_by_id(enterprise_id, db)


@router.post("/", response_model=EnterpriseResponse, status_code=status.HTTP_201_CREATED)
async def create_enterprise(
    payload: EnterpriseCreate,
    db: Session = Depends(get_db),
) -> EnterpriseResponse:
    return await enterprise_service.create(payload, db)


@router.put("/{enterprise_id}", response_model=EnterpriseResponse)
async def update_enterprise(
    enterprise_id: UUID,
    payload: EnterpriseUpdate,
    db: Session = Depends(get_db),
) -> EnterpriseResponse:
    return await enterprise_service.update(enterprise_id, payload, db)
