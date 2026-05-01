"""
Testes unitários para AssessmentService.

Foco: lógica de negócio da camada de service isolada.
Estratégia: cliente Gemini completamente mockado.
Não há chamadas de rede nestes testes.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AssessmentClassificationError
from app.models.assessment import TipoAvaliacao
from app.services.assessment_service import AssessmentService

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_TEXT_POSITIVO = "Adorei o atendimento, muito bom!"
FAKE_TEXT_NEGATIVO = "Achei péssimo, demorou muito."
FAKE_TEXT_NEUTRO = "Foi normal, nada demais."
FAKE_TEXT_SUGESTAO = "Seria bom ter mais opções no cardápio."
FAKE_TEXT_DUVIDA = "Vocês funcionam aos domingos?"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_text: str) -> MagicMock:
    response = MagicMock()
    response.text = json_text
    return response


def _mock_gemini_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = _mock_response(response_text)
    return client


# ---------------------------------------------------------------------------
# classify_assessment_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "tipo_avaliacao"),
    [
        (FAKE_TEXT_POSITIVO, TipoAvaliacao.POSITIVA),
        (FAKE_TEXT_NEGATIVO, TipoAvaliacao.NEGATIVA),
        (FAKE_TEXT_NEUTRO, TipoAvaliacao.NEUTRA),
        (FAKE_TEXT_SUGESTAO, TipoAvaliacao.SUGESTAO),
        (FAKE_TEXT_DUVIDA, TipoAvaliacao.DUVIDA),
    ],
)
def test_given_valid_model_output_when_classify_then_returns_enum(texto, tipo_avaliacao):
    # GIVEN
    service = AssessmentService()
    client = _mock_gemini_client(f'{{"tipo_avaliacao": "{tipo_avaliacao.name.lower()}"}}')

    with patch(
        "app.services.assessment_service.AssessmentService._get_gemini_client",
        return_value=client,
    ) as mock_get_client:
        # WHEN
        result = service.classify_assessment_text(texto)

    # THEN
    mock_get_client.assert_called_once()
    client.models.generate_content.assert_called_once()
    assert result == tipo_avaliacao


def test_given_invalid_json_when_classify_then_raises_domain_error():
    # GIVEN
    service = AssessmentService()
    client = _mock_gemini_client("isso nao e json")

    with patch(
        "app.services.assessment_service.AssessmentService._get_gemini_client",
        return_value=client,
    ):
        # WHEN / THEN
        with pytest.raises(AssessmentClassificationError, match="Não foi possível classificar"):
            service.classify_assessment_text(FAKE_TEXT_POSITIVO)


def test_given_client_error_when_classify_then_raises_domain_error():
    # GIVEN
    service = AssessmentService()
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("erro da api")

    with patch(
        "app.services.assessment_service.AssessmentService._get_gemini_client",
        return_value=client,
    ):
        # WHEN / THEN
        with pytest.raises(AssessmentClassificationError, match="Não foi possível classificar"):
            service.classify_assessment_text(FAKE_TEXT_POSITIVO)