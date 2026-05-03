"""
Testes da serializacao de AssessmentResponse (SCRUM-224).

Foco: garantir que o nome do usuario (relationship usuario.nome) seja
exposto em usuario_nome quando o ORM carrega a relacao, e cair em None
quando a relacao nao esta disponivel (compatibilidade com mocks/fixtures).
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.assessment import TipoAvaliacao
from app.schemas.assessments import AssessmentResponse


def _orm_like(usuario=None) -> SimpleNamespace:
    obj = SimpleNamespace(
        id_avaliacao=uuid.uuid4(),
        texto="Comida excelente",
        tipo_avaliacao=TipoAvaliacao.POSITIVA,
        usuario_id=uuid.uuid4(),
        empresa_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    if usuario is not None:
        obj.usuario = usuario
    return obj


def test_given_assessment_with_user_when_serialized_then_returns_user_name():
    # GIVEN
    usuario = SimpleNamespace(nome="Maria das Dores")
    orm = _orm_like(usuario=usuario)

    # WHEN
    response = AssessmentResponse.model_validate(orm)

    # THEN
    assert response.usuario_nome == "Maria das Dores"


def test_given_assessment_without_loaded_user_when_serialized_then_user_name_none():
    # GIVEN
    orm = _orm_like(usuario=None)

    # WHEN
    response = AssessmentResponse.model_validate(orm)

    # THEN
    assert response.usuario_nome is None


def test_given_assessment_with_user_when_serialized_then_keeps_user_id():
    # GIVEN
    usuario = SimpleNamespace(nome="João")
    orm = _orm_like(usuario=usuario)

    # WHEN
    response = AssessmentResponse.model_validate(orm)

    # THEN
    assert response.usuario_id == orm.usuario_id
