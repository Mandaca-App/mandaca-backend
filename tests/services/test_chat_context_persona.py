import uuid

from app.models.enterprise import Enterprise
from app.models.user import TipoUsuario, User
from app.services.chat_context_service import ChatContextService


def _create_enterprise(db, endereco: str | None = "Rua do Centro, Triunfo, PE") -> Enterprise:
    user = User(
        tipo_usuario=TipoUsuario.EMPREENDEDOR,
        nome="Empreendedor Teste",
        cpf=str(uuid.uuid4().int)[:11],
    )
    db.add(user)
    db.flush()

    empresa = Enterprise(
        nome="Pousada Raiz",
        especialidade="Hospedagem familiar",
        endereco=endereco,
        usuario_id=user.id_usuario,
    )
    db.add(empresa)
    db.commit()
    return empresa


def test_given_enterprise_when_enterprise_context_built_then_returns_prompt_context(db):
    # GIVEN
    empresa = _create_enterprise(db)
    service = ChatContextService()

    # WHEN
    context = service.build_enterprise_context(empresa.id_empresa, db)

    # THEN
    assert context is not None
    assert context.enterprise_name == "Pousada Raiz"
    assert context.category == "Hospedagem familiar"
    assert context.city == "Triunfo"
    assert context.state == "PE"


def test_given_enterprise_without_city_when_enterprise_context_built_then_keeps_optional_fields(db):
    # GIVEN
    empresa = _create_enterprise(db, endereco="Zona rural")
    service = ChatContextService()

    # WHEN
    context = service.build_enterprise_context(empresa.id_empresa, db)

    # THEN
    assert context is not None
    assert context.enterprise_name == "Pousada Raiz"
    assert context.city is None
    assert context.state is None


def test_given_missing_enterprise_when_enterprise_context_built_then_returns_none(db):
    # GIVEN
    service = ChatContextService()

    # WHEN
    context = service.build_enterprise_context(uuid.uuid4(), db)

    # THEN
    assert context is None
