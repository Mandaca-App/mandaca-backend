from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateEnterpriseNameError,
    EnterpriseNotFoundError,
    UserAlreadyHasEnterpriseError,
    UserAlreadyLinkedError,
    UserNotFoundError,
)
from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.enterprises import (
    EnterpriseCreate,
    EnterpriseOverviewResponse,
    EnterprisePercentageResponse,
    EnterpriseUpdate,
    PhotoOverviewResponse,
)
from app.services.geocoding_service import geocode_address


def get_by_id(enterprise_id: UUID, db: Session) -> Enterprise:
    """Busca uma empresa ativa pelo ID ou lança EnterpriseNotFoundError."""
    enterprise = db.execute(
        select(Enterprise).where(
            Enterprise.id_empresa == enterprise_id,
            Enterprise.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not enterprise:
        raise EnterpriseNotFoundError(enterprise_id)
    return enterprise


def list_all(db: Session) -> list[Enterprise]:
    """Retorna todas as empresas ativas."""
    return list(
        db.execute(select(Enterprise).where(Enterprise.deleted_at.is_(None))).scalars().all()
    )


def get_overview(enterprise_id: UUID, db: Session) -> EnterpriseOverviewResponse:
    """Monta a visão geral de uma empresa com fotos e coordenadas."""
    enterprise = get_by_id(enterprise_id, db)
    return EnterpriseOverviewResponse(
        id_empresa=enterprise.id_empresa,
        endereco=enterprise.endereco,
        latitude=enterprise.latitude,
        longitude=enterprise.longitude,
        historia=enterprise.historia,
        fotos=[
            PhotoOverviewResponse(url_foto_empresa=photo.url_foto_empresa)
            for photo in enterprise.fotos
        ],
    )


async def create(payload: EnterpriseCreate, db: Session) -> Enterprise:
    """Cria uma nova empresa validando unicidade de nome, usuário e geocodificando o endereço."""
    existing = db.execute(
        select(Enterprise).where(
            Enterprise.nome == payload.nome,
            Enterprise.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing:
        raise DuplicateEnterpriseNameError(payload.nome)

    user = db.get(User, payload.usuario_id)
    if not user:
        raise UserNotFoundError(payload.usuario_id)
    if user.empresa is not None:
        raise UserAlreadyHasEnterpriseError(payload.usuario_id)

    lat, lng = None, None
    if payload.endereco:
        lat, lng = await geocode_address(payload.endereco)

    enterprise = Enterprise(
        nome=payload.nome,
        especialidade=payload.especialidade,
        endereco=payload.endereco,
        historia=payload.historia,
        hora_abrir=payload.hora_abrir,
        hora_fechar=payload.hora_fechar,
        telefone=payload.telefone,
        usuario_id=payload.usuario_id,
        latitude=lat,
        longitude=lng,
    )
    db.add(enterprise)
    db.commit()
    db.refresh(enterprise)
    return enterprise


async def update(enterprise_id: UUID, payload: EnterpriseUpdate, db: Session) -> Enterprise:
    """Atualiza os campos de uma empresa, geocodificando o endereço se alterado."""
    enterprise = get_by_id(enterprise_id, db)

    if payload.nome is not None and payload.nome != enterprise.nome:
        existing = db.execute(
            select(Enterprise).where(
                Enterprise.nome == payload.nome,
                Enterprise.id_empresa != enterprise_id,
                Enterprise.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing:
            raise DuplicateEnterpriseNameError(payload.nome)
        enterprise.nome = payload.nome

    if payload.usuario_id is not None and payload.usuario_id != enterprise.usuario_id:
        user = db.get(User, payload.usuario_id)
        if not user:
            raise UserNotFoundError(payload.usuario_id)
        if user.empresa is not None and user.empresa.id_empresa != enterprise.id_empresa:
            raise UserAlreadyLinkedError(payload.usuario_id)
        enterprise.usuario_id = payload.usuario_id

    if payload.especialidade is not None:
        enterprise.especialidade = payload.especialidade
    if payload.endereco is not None:
        enterprise.endereco = payload.endereco
        lat, lng = await geocode_address(payload.endereco)
        enterprise.latitude = lat
        enterprise.longitude = lng
    if payload.historia is not None:
        enterprise.historia = payload.historia
    if payload.hora_abrir is not None:
        enterprise.hora_abrir = payload.hora_abrir
    if payload.hora_fechar is not None:
        enterprise.hora_fechar = payload.hora_fechar
    if payload.telefone is not None:
        enterprise.telefone = payload.telefone

    db.commit()
    db.refresh(enterprise)
    return enterprise


def get_percentage(enterprise_id: UUID, db: Session) -> EnterprisePercentageResponse:
    """Calcula e retorna a porcentagem de preenchimento do perfil da empresa."""
    enterprise = get_by_id(enterprise_id, db)

    campos: dict[str, object] = {
        "especialidade": enterprise.especialidade,
        "endereco": enterprise.endereco,
        "historia": enterprise.historia,
        "hora_abrir": enterprise.hora_abrir,
        "hora_fechar": enterprise.hora_fechar,
        "telefone": enterprise.telefone,
        "fotos": enterprise.fotos or None,
        "cardapios": enterprise.cardapios or None,
    }

    preenchidos = [campo for campo, valor in campos.items() if valor is not None]
    faltando = [campo for campo, valor in campos.items() if valor is None]
    porcentagem = round(20 + len(preenchidos) / len(campos) * 80, 1)

    return EnterprisePercentageResponse(
        id_empresa=enterprise.id_empresa,
        nome=enterprise.nome,
        porcentagem=porcentagem,
        campos_preenchidos=preenchidos,
        campos_faltando=faltando,
    )
