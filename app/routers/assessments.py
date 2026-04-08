from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.assessment import Assessment
from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.assessments import AssessmentCreate, AssessmentResponse, AssessmentUpdate
from app.services.assessment_service import classify_assessment_text

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

    try:
        tipo = classify_assessment_text(assessment_in.texto)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível classificar a avaliação no momento. Tente novamente.",
        )

    assessment = Assessment(
        texto=assessment_in.texto,
        tipo_avaliacao=tipo,
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
        try:
            novo_tipo = classify_assessment_text(assessment_in.texto)
        except RuntimeError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível classificar a avaliação no momento. Tente novamente.",
            )
        assessment.texto = assessment_in.texto
        assessment.tipo_avaliacao = novo_tipo

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

@router.get(
    "/by-enterprise/{empresa_id}",
    response_model=list[AssessmentResponse],
    status_code=status.HTTP_200_OK,
)
def get_assessments_by_enterprise(
    empresa_id: UUID,
    db: Session = Depends(get_db),
) -> list[AssessmentResponse]:
    """
    Retorna todas as avaliações associadas a uma empresa específica.
    """

    empresa = db.get(Enterprise, empresa_id)
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada.",
        )

    stmt = select(Assessment).where(Assessment.empresa_id == empresa_id)
    assessments = db.scalars(stmt).all()

    return assessments