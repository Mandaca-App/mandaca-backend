"""
Testes unitários para AssessmentService.

Foco: lógica de negócio da camada de service isolada.
Estratégia: cliente Gemini completamente mockado.
Não há chamadas de rede nestes testes.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    AssessmentClassificationError,
    AssessmentPageEmptyError,
    EnterpriseNotFoundError,
)
from app.models.assessment import Assessment, TipoAvaliacao
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


def _make_assessment(empresa_id: uuid.UUID, offset_seconds: int = 0) -> Assessment:
    a = Assessment()
    a.id_avaliacao = uuid.uuid4()
    a.texto = "Texto de teste"
    a.tipo_avaliacao = TipoAvaliacao.NEUTRA
    a.usuario_id = uuid.uuid4()
    a.empresa_id = empresa_id
    a.created_at = datetime(2024, 1, 1, 12, 0, offset_seconds, tzinfo=timezone.utc)
    return a


def test_given_enterprise_not_found_when_paginated_then_raises():
    service = AssessmentService()
    db = MagicMock()
    db.get.return_value = None  # empresa não existe

    with pytest.raises(EnterpriseNotFoundError):
        service.list_by_enterprise_paginated(uuid.uuid4(), page=1, db=db)


def test_given_empty_page_when_paginated_then_raises_page_empty():
    service = AssessmentService()
    db = MagicMock()
    db.get.return_value = MagicMock()  # empresa existe

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []  # página vazia
    db.scalars.return_value = scalars_mock

    with pytest.raises(AssessmentPageEmptyError) as exc_info:
        service.list_by_enterprise_paginated(uuid.uuid4(), page=5, db=db)

    assert exc_info.value.page == 5


def test_given_exactly_10_assessments_when_paginated_then_has_more_false():
    service = AssessmentService()
    empresa_id = uuid.uuid4()
    db = MagicMock()
    db.get.return_value = MagicMock()

    items = [_make_assessment(empresa_id, i) for i in range(10)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items  # exatamente 10, sem o extra
    db.scalars.return_value = scalars_mock

    result = service.list_by_enterprise_paginated(empresa_id, page=1, db=db)

    assert result["page"] == 1
    assert len(result["items"]) == 10
    assert result["has_more"] is False


def test_given_11_assessments_when_paginated_page_1_then_has_more_true():
    service = AssessmentService()
    empresa_id = uuid.uuid4()
    db = MagicMock()
    db.get.return_value = MagicMock()

    # 11 itens retornados do banco (PAGE_SIZE + 1 = sinal de que há mais)
    items = [_make_assessment(empresa_id, i) for i in range(11)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    db.scalars.return_value = scalars_mock

    result = service.list_by_enterprise_paginated(empresa_id, page=1, db=db)

    assert result["has_more"] is True
    assert len(result["items"]) == 10
