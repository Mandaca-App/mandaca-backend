import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessContextNotFoundError,
    EnterpriseNotFoundError,
    InvalidContextDataError,
)
from app.models.business_context import BusinessContext
from app.models.enterprise import Enterprise
from app.schemas.business_contexts import BusinessContextCreate, BusinessContextUpdate
from app.services.business_context_builder_service import BusinessContextBuilderService

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _parse_dados(raw: str) -> Any:
    """Faz o parse do texto JSON recebido ou lança InvalidContextDataError."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidContextDataError(str(exc))


def _compute_hash(dados: Any) -> str:
    """Serializa os dados de forma determinística e retorna o SHA-256 hex."""
    serialized = json.dumps(dados, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _persist(empresa_id: UUID, dados: Any, db: Session) -> BusinessContext:
    """Persiste um BusinessContext a partir de um dict já validado."""
    context = BusinessContext(
        empresa_id=empresa_id,
        dados_contexto=dados,
        hash_contexto=_compute_hash(dados),
    )
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def get_by_id(context_id: UUID, db: Session) -> BusinessContext:
    """Busca um contexto de negócio pelo ID ou lança BusinessContextNotFoundError."""
    context = db.get(BusinessContext, context_id)
    if not context:
        raise BusinessContextNotFoundError(context_id)
    return context


def list_by_enterprise(enterprise_id: UUID, db: Session) -> list[BusinessContext]:
    """Retorna todos os contextos de uma empresa, do mais recente ao mais antigo."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise EnterpriseNotFoundError(enterprise_id)

    return list(
        db.execute(
            select(BusinessContext)
            .where(BusinessContext.empresa_id == enterprise_id)
            .order_by(BusinessContext.criado_em.desc())
        )
        .scalars()
        .all()
    )


def create(payload: BusinessContextCreate, db: Session) -> BusinessContext:
    """Cria um contexto de negócio a partir de um JSON enviado manualmente pelo cliente."""
    enterprise = db.get(Enterprise, payload.empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(payload.empresa_id)

    dados = _parse_dados(payload.dados_contexto)
    return _persist(payload.empresa_id, dados, db)


def create_from_enterprise(empresa_id: UUID, db: Session) -> BusinessContext:
    """Monta automaticamente o snapshot do negócio via builder e persiste como novo contexto."""
    enterprise = db.get(Enterprise, empresa_id)
    if not enterprise:
        raise EnterpriseNotFoundError(empresa_id)

    dados = BusinessContextBuilderService().build_snapshot(empresa_id, db)
    return _persist(empresa_id, dados, db)


def update(context_id: UUID, payload: BusinessContextUpdate, db: Session) -> BusinessContext:
    context = get_by_id(context_id, db)

    if payload.dados_contexto is not None:
        context.dados_contexto = payload.dados_contexto
        context.hash_contexto = _compute_hash(payload.dados_contexto)  # já é dict

    db.commit()
    db.refresh(context)
    return context


def delete(context_id: UUID, db: Session) -> None:
    """Remove permanentemente um contexto de negócio."""
    context = get_by_id(context_id, db)
    db.delete(context)
    db.commit()
