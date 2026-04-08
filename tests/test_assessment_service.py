"""
Testes unitários para assessment_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: cliente Gemini completamente mockado.
Não há chamadas de rede nestes testes.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.assessment import TipoAvaliacao
from app.services import assessment_service

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
    response = _mock_response(f'{{"tipo_avaliacao": "{tipo_avaliacao.value}"}}')

    with patch(
        "app.services.assessment_service.client.models.generate_content",
        return_value=response,
    ) as mock_generate:
        # WHEN
        result = assessment_service.classify_assessment_text(texto)

    # THEN
    mock_generate.assert_called_once()
    assert result == tipo_avaliacao


def test_given_invalid_json_when_classify_then_raises_runtime_error():
    # GIVEN
    response = _mock_response("isso nao e json")

    with patch(
        "app.services.assessment_service.client.models.generate_content",
        return_value=response,
    ):
        # WHEN / THEN
        with pytest.raises(RuntimeError, match="Falha ao classificar a avaliação."):
            assessment_service.classify_assessment_text(FAKE_TEXT_POSITIVO)


def test_given_client_error_when_classify_then_raises_runtime_error():
    # GIVEN
    with patch(
        "app.services.assessment_service.client.models.generate_content",
        side_effect=Exception("erro da api"),
    ):
        # WHEN / THEN
        with pytest.raises(RuntimeError, match="Falha ao classificar a avaliação."):
            assessment_service.classify_assessment_text(FAKE_TEXT_POSITIVO)
