from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.assessment import Assessment
from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.assessments import AssessmentCreate, AssessmentResponse, AssessmentUpdate

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    assessment_in: AssessmentCreate,
    db: Session = Depends(get_db),
):
    usuario = db.get(User, assessment_in.usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    empresa = db.get(Enterprise, assessment_in.empresa_id)
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada.",
        )

    assessment = Assessment(
        texto=assessment_in.texto,
        tipo_avaliacao=assessment_in.tipo_avaliacao,
        usuario_id=assessment_in.usuario_id,
        empresa_id=assessment_in.empresa_id,
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get(
    "",
    response_model=List[AssessmentResponse],
)
def list_assessments(
    db: Session = Depends(get_db),
):
    stmt = select(Assessment)
    assessments = db.scalars(stmt).all()
    return assessments


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def get_assessment_by_id(
    assessment_id: UUID,
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliação não encontrada.",
        )
    return assessment


@router.put(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def update_assessment(
    assessment_id: UUID,
    assessment_in: AssessmentUpdate,
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliação não encontrada.",
        )

    if assessment_in.usuario_id is not None:
        usuario = db.get(User, assessment_in.usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        assessment.usuario_id = assessment_in.usuario_id

    if assessment_in.empresa_id is not None:
        empresa = db.get(Enterprise, assessment_in.empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada.",
            )
        assessment.empresa_id = assessment_in.empresa_id

    if assessment_in.texto is not None:
        assessment.texto = assessment_in.texto

    if assessment_in.tipo_avaliacao is not None:
        assessment.tipo_avaliacao = assessment_in.tipo_avaliacao

    db.commit()
    db.refresh(assessment)
    return assessment


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliação não encontrada.",
        )

    db.delete(assessment)
    db.commit()
    return None