from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.assessments import (
    AssessmentCreate,
    AssessmentPaginatedResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["assessments"])
assessment_service = AssessmentService()


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    assessment_in: AssessmentCreate,
    db: Session = Depends(get_db),
):
    return assessment_service.create(assessment_in, db)


@router.get(
    "",
    response_model=list[AssessmentResponse],
)
def list_assessments(
    db: Session = Depends(get_db),
):
    return assessment_service.list_all(db)


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def get_assessment_by_id(
    assessment_id: UUID,
    db: Session = Depends(get_db),
):
    return assessment_service.get_by_id(assessment_id, db)


@router.put(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def update_assessment(
    assessment_id: UUID,
    assessment_in: AssessmentUpdate,
    db: Session = Depends(get_db),
):
    return assessment_service.update(assessment_id, assessment_in, db)


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
):
    return assessment_service.delete(assessment_id, db)


@router.get(
    "/by-enterprise/{empresa_id}/paginated",
    response_model=AssessmentPaginatedResponse,
    status_code=status.HTTP_200_OK,
)
def get_assessments_by_enterprise_paginated(
    empresa_id: UUID,
    page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
    db: Session = Depends(get_db),
) -> AssessmentPaginatedResponse:
    return assessment_service.list_by_enterprise_paginated(empresa_id, page, db)


@router.get(
    "/by-enterprise/{empresa_id}",
    response_model=list[AssessmentResponse],
    status_code=status.HTTP_200_OK,
)
def get_assessments_by_enterprise(
    empresa_id: UUID,
    db: Session = Depends(get_db),
) -> list[AssessmentResponse]:
    return assessment_service.list_by_enterprise(empresa_id, db)
