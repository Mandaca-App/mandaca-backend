from typing import Literal
from uuid import UUID

from google import genai
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AssessmentClassificationError,
    AssessmentNotFoundError,
    EnterpriseNotFoundError,
    UserNotFoundError,
)
from app.models.assessment import Assessment, TipoAvaliacao
from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.assessments import AssessmentCreate, AssessmentUpdate


class AssessmentClassification(BaseModel):
    tipo_avaliacao: Literal["positiva", "negativa", "neutra", "sugestao", "duvida"]


class AssessmentService:
    @staticmethod
    def _get_gemini_client():
        return genai.Client(api_key=settings.gemini_api_key)

    def classify_assessment_text(self, texto: str) -> TipoAvaliacao:
        client = self._get_gemini_client()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=texto,
                config={
                    "system_instruction": (
                        "Classifique o texto em apenas uma categoria: "
                        "positiva, negativa, neutra, sugestao ou duvida. "
                        "Retorne somente JSON compatível com o schema."
                    ),
                    "response_mime_type": "application/json",
                    "response_json_schema": AssessmentClassification.model_json_schema(),
                    "temperature": 0,
                },
            )

            data = AssessmentClassification.model_validate_json(response.text)
            return TipoAvaliacao(data.tipo_avaliacao)

        except Exception as exc:
            raise AssessmentClassificationError(
                "Não foi possível classificar a avaliação no momento. Tente novamente."
            ) from exc

    def get_by_id(self, assessment_id: UUID, db: Session) -> Assessment:
        assessment = db.get(Assessment, assessment_id)
        if not assessment:
            raise AssessmentNotFoundError(assessment_id)
        return assessment

    def list_all(self, db: Session) -> list[Assessment]:
        stmt = select(Assessment).order_by(Assessment.created_at.desc())
        return list(db.scalars(stmt).all())

    def create(self, assessment_in: AssessmentCreate, db: Session) -> Assessment:
        usuario = db.get(User, assessment_in.usuario_id)
        if not usuario:
            raise UserNotFoundError(assessment_in.usuario_id)

        empresa = db.get(Enterprise, assessment_in.empresa_id)
        if not empresa:
            raise EnterpriseNotFoundError(assessment_in.empresa_id)

        tipo = self.classify_assessment_text(assessment_in.texto)

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

    def update(
        self,
        assessment_id: UUID,
        assessment_in: AssessmentUpdate,
        db: Session,
    ) -> Assessment:
        assessment = self.get_by_id(assessment_id, db)

        if assessment_in.usuario_id is not None:
            usuario = db.get(User, assessment_in.usuario_id)
            if not usuario:
                raise UserNotFoundError(assessment_in.usuario_id)
            assessment.usuario_id = assessment_in.usuario_id

        if assessment_in.empresa_id is not None:
            empresa = db.get(Enterprise, assessment_in.empresa_id)
            if not empresa:
                raise EnterpriseNotFoundError(assessment_in.empresa_id)
            assessment.empresa_id = assessment_in.empresa_id

        if assessment_in.texto is not None:
            novo_tipo = self.classify_assessment_text(assessment_in.texto)
            assessment.texto = assessment_in.texto
            assessment.tipo_avaliacao = novo_tipo

        db.commit()
        db.refresh(assessment)
        return assessment

    def delete(self, assessment_id: UUID, db: Session) -> None:
        assessment = self.get_by_id(assessment_id, db)
        db.delete(assessment)
        db.commit()

    def list_by_enterprise(self, empresa_id: UUID, db: Session) -> list[Assessment]:
        empresa = db.get(Enterprise, empresa_id)
        if not empresa:
            raise EnterpriseNotFoundError(empresa_id)

        stmt = (
            select(Assessment)
            .where(Assessment.empresa_id == empresa_id)
            .order_by(Assessment.created_at.desc())
        )
        return list(db.scalars(stmt).all())
