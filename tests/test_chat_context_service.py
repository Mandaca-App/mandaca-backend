"""
Testes unitários para ChatContextService (SCRUM-48).

Foco: construção do contexto RAG a partir dos dados do banco.
Estratégia:
  - DB usa SQLite in-memory via fixture db (conftest.py).
  - User e Enterprise criados como pré-requisito de FK.
  - Assessment e Menu criados conforme o cenário de cada teste.
"""

import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from app.models.assessment import Assessment, TipoAvaliacao
from app.models.enterprise import Enterprise
from app.models.menu import CategoriaCardapio, Menu
from app.models.user import TipoUsuario, User
from app.services.chat_context_service import ChatContextService


def _create_enterprise(
    db,
    nome: str = "Barraca da Dona Maria",
    especialidade: str | None = "Comida típica nordestina",
    historia: str | None = "Fundada em 2010 no sertão pernambucano.",
) -> Enterprise:
    """Cria User + Enterprise no banco para satisfazer as FK."""
    user = User(
        tipo_usuario=TipoUsuario.EMPREENDEDOR,
        nome="Empreendedor Teste",
        cpf=str(uuid.uuid4().int)[:11],
    )
    db.add(user)
    db.flush()

    empresa = Enterprise(
        nome=nome,
        especialidade=especialidade,
        historia=historia,
        usuario_id=user.id_usuario,
    )
    db.add(empresa)
    db.commit()
    return empresa


def _create_assessment(
    db,
    empresa: Enterprise,
    texto: str,
    tipo: TipoAvaliacao = TipoAvaliacao.POSITIVA,
) -> Assessment:
    user = User(
        tipo_usuario=TipoUsuario.TURISTA,
        nome="Turista Teste",
        cpf=str(uuid.uuid4().int)[:11],
    )
    db.add(user)
    db.flush()
    assessment = Assessment(
        texto=texto,
        tipo_avaliacao=tipo,
        usuario_id=user.id_usuario,
        empresa_id=empresa.id_empresa,
    )
    db.add(assessment)
    db.commit()
    return assessment


def _create_menu(
    db,
    empresa: Enterprise,
    descricao: str = "Carne de Sol com Macaxeira",
    categoria: CategoriaCardapio = CategoriaCardapio.PRATO_PRINCIPAL,
    preco: Decimal = Decimal("35.00"),
    status: bool = True,
) -> Menu:
    item = Menu(
        descricao=descricao,
        categoria=categoria,
        preco=preco,
        status=status,
        empresa_id=empresa.id_empresa,
    )
    db.add(item)
    db.commit()
    return item


# ---------------------------------------------------------------------------
# Dados do perfil da empresa
# ---------------------------------------------------------------------------


def test_given_enterprise_with_data_when_context_built_then_includes_enterprise_name(db):
    # GIVEN
    empresa = _create_enterprise(db, nome="Barraca da Dona Maria")
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Barraca da Dona Maria" in context


def test_given_enterprise_with_especialidade_when_context_built_then_included(db):
    # GIVEN
    empresa = _create_enterprise(db, especialidade="Comida típica nordestina")
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Comida típica nordestina" in context


def test_given_enterprise_with_historia_when_context_built_then_included(db):
    # GIVEN
    empresa = _create_enterprise(db, historia="Fundada em 2010 no sertão pernambucano.")
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Fundada em 2010" in context


def test_given_no_enterprise_when_context_built_then_returns_empty_string(db):
    # GIVEN
    fake_id = uuid.uuid4()
    service = ChatContextService()

    # WHEN
    context = service.build_context(fake_id, db)

    # THEN
    assert context == ""


# ---------------------------------------------------------------------------
# Avaliações
# ---------------------------------------------------------------------------


def test_given_assessments_when_context_built_then_includes_assessment_text(db):
    # GIVEN
    empresa = _create_enterprise(db)
    _create_assessment(db, empresa, "Atendimento excelente e comida gostosa")
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Atendimento excelente e comida gostosa" in context


def test_given_assessments_when_context_built_then_includes_tipo(db):
    # GIVEN
    empresa = _create_enterprise(db)
    _create_assessment(db, empresa, "Fila demorada no almoço", TipoAvaliacao.NEGATIVA)
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "negativa" in context.lower()


def test_given_no_assessments_when_context_built_then_still_returns_enterprise_info(db):
    # GIVEN
    empresa = _create_enterprise(db, nome="Restaurante Vazio")
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Restaurante Vazio" in context
    assert context != ""


def test_given_two_enterprises_when_context_built_then_isolates_by_enterprise(db):
    # GIVEN
    empresa_a = _create_enterprise(db, nome="Empresa Alpha")
    empresa_b = _create_enterprise(db, nome="Empresa Beta")
    _create_assessment(db, empresa_b, "Avaliacao exclusiva da empresa B")
    service = ChatContextService()

    # WHEN
    context_a = service.build_context(empresa_a.id_empresa, db)

    # THEN
    assert "Avaliacao exclusiva da empresa B" not in context_a


# ---------------------------------------------------------------------------
# Cardápio
# ---------------------------------------------------------------------------


def test_given_active_menu_item_when_context_built_then_included(db):
    # GIVEN
    empresa = _create_enterprise(db)
    _create_menu(db, empresa, descricao="Carne de Sol com Macaxeira", status=True)
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Carne de Sol com Macaxeira" in context


def test_given_inactive_menu_item_when_context_built_then_not_included(db):
    # GIVEN
    empresa = _create_enterprise(db)
    _create_menu(db, empresa, descricao="Item Inativo", status=False)
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "Item Inativo" not in context


def test_given_menu_item_when_context_built_then_includes_preco(db):
    # GIVEN
    empresa = _create_enterprise(db)
    _create_menu(db, empresa, descricao="Tapioca", preco=Decimal("12.50"), status=True)
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert "12.50" in context


def test_given_enterprise_with_hours_when_context_built_then_includes_horario(db):
    # GIVEN
    user = User(
        tipo_usuario=TipoUsuario.EMPREENDEDOR,
        nome="Empreendedor Horario",
        cpf=str(uuid.uuid4().int)[:11],
    )
    db.add(user)
    db.flush()
    empresa = Enterprise(
        nome="Restaurante com Horario",
        hora_abrir=time(8, 0),
        hora_fechar=time(18, 0),
        usuario_id=user.id_usuario,
    )
    db.add(empresa)
    db.commit()
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert str(time(8, 0)) in context
    assert str(time(18, 0)) in context


def test_given_soft_deleted_enterprise_when_context_built_then_returns_empty(db):
    # GIVEN
    empresa = _create_enterprise(db)
    empresa.deleted_at = datetime.now(timezone.utc)
    db.commit()
    service = ChatContextService()

    # WHEN
    context = service.build_context(empresa.id_empresa, db)

    # THEN
    assert context == ""
