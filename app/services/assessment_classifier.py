from typing import Literal

from google import genai
from pydantic import BaseModel, ValidationError

from app.models.assessment import TipoAvaliacao

client = genai.Client()


class AssessmentClassification(BaseModel):
    tipo_avaliacao: Literal["positiva", "negativa", "neutra", "sugestao", "duvida"]


def classify_assessment_text(texto: str) -> TipoAvaliacao:
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

    except (ValidationError, ValueError, Exception) as exc:
        raise RuntimeError("Falha ao classificar a avaliação.") from exc