import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessContextNotFoundError,
    EnterpriseNotFoundError,
)
from app.models.business_context import BusinessContext
from app.models.enterprise import Enterprise
from app.schemas.business_contexts import BusinessContextUpdate
from app.services.business_context_builder_service import BusinessContextBuilderService


class BusinessContextService:

    def _compute_hash(self, dados: Any) -> str:
        """Serializa os dados de forma determinística e retorna o SHA-256 hex."""
        serialized = json.dumps(dados, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def compute_hash(self, dados: Any) -> str:
        """Retorna o hash SHA-256 deterministico de um contexto."""
        return self._compute_hash(dados)

    def _persist(self, empresa_id: UUID, dados: Any, db: Session) -> BusinessContext:
        """Persiste um BusinessContext a partir de um dict já validado."""
        context = BusinessContext(
            empresa_id=empresa_id,
            dados_contexto=dados,
            hash_contexto=self._compute_hash(dados),
        )
        db.add(context)
        db.commit()
        db.refresh(context)
        return context

    def get_by_id(self, context_id: UUID, db: Session) -> BusinessContext:
        """Busca um contexto de negócio pelo ID ou lança BusinessContextNotFoundError."""
        context = db.get(BusinessContext, context_id)
        if not context:
            raise BusinessContextNotFoundError(context_id)
        return context

    def list_by_enterprise(self, enterprise_id: UUID, db: Session) -> list[BusinessContext]:
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

    def create_from_enterprise(self, empresa_id: UUID, db: Session) -> BusinessContext:
        """Monta automaticamente o snapshot do negócio via builder e persiste como novo contexto."""
        enterprise = db.get(Enterprise, empresa_id)
        if not enterprise:
            raise EnterpriseNotFoundError(empresa_id)

        dados = BusinessContextBuilderService().build_snapshot(empresa_id, db)
        return self._persist(empresa_id, dados, db)

    def create_from_snapshot(
        self, empresa_id: UUID, dados_contexto: Any, db: Session
    ) -> BusinessContext:
        """Persiste um snapshot de contexto ja montado."""
        enterprise = db.get(Enterprise, empresa_id)
        if not enterprise:
            raise EnterpriseNotFoundError(empresa_id)

        return self._persist(empresa_id, dados_contexto, db)

    def update(
        self, context_id: UUID, payload: BusinessContextUpdate, db: Session
    ) -> BusinessContext:
        """Atualiza os dados do contexto e recalcula o hash SHA-256."""
        context = self.get_by_id(context_id, db)

        if payload.dados_contexto is not None:
            context.dados_contexto = payload.dados_contexto
            context.hash_contexto = self._compute_hash(payload.dados_contexto)

        db.commit()
        db.refresh(context)
        return context

    def delete(self, context_id: UUID, db: Session) -> None:
        """Remove permanentemente um contexto de negócio."""
        context = self.get_by_id(context_id, db)
        db.delete(context)
        db.commit()
