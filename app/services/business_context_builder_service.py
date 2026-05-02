import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, TipoAvaliacao
from app.models.enterprise import Enterprise
from app.models.menu import Menu

_MAX_ASSESSMENTS = 5

_TIPO_AVALIACAO_LABEL: dict[int, str] = {
    TipoAvaliacao.POSITIVA: "positiva",
    TipoAvaliacao.NEGATIVA: "negativa",
    TipoAvaliacao.NEUTRA: "neutra",
    TipoAvaliacao.SUGESTAO: "sugestao",
    TipoAvaliacao.DUVIDA: "duvida",
}


class BusinessContextBuilderService:
    """Monta um snapshot estruturado (dict) do negócio para ser persistido
    como dados_contexto em BusinessContext."""

    def build_snapshot(self, empresa_id: uuid.UUID, db: Session) -> dict[str, Any]:
        """Coleta dados da empresa, avaliações e cardápio e retorna um dict JSON-serializável."""
        empresa = db.get(Enterprise, empresa_id)
        if not empresa or empresa.deleted_at is not None:
            return {}

        snapshot: dict[str, Any] = {"nome": empresa.nome}

        if empresa.especialidade:
            snapshot["especialidade"] = empresa.especialidade
        if empresa.historia:
            snapshot["historia"] = empresa.historia
        if empresa.endereco:
            snapshot["endereco"] = empresa.endereco
        if empresa.telefone:
            snapshot["telefone"] = empresa.telefone
        if empresa.hora_abrir and empresa.hora_fechar:
            snapshot["horario"] = {
                "abrir": empresa.hora_abrir.strftime("%H:%M"),
                "fechar": empresa.hora_fechar.strftime("%H:%M"),
            }
        if empresa.latitude is not None and empresa.longitude is not None:
            snapshot["localizacao"] = {
                "latitude": empresa.latitude,
                "longitude": empresa.longitude,
            }

        assessments = self._fetch_assessments(empresa_id, db)
        if assessments:
            snapshot["avaliacoes"] = [
                {
                    "tipo": _TIPO_AVALIACAO_LABEL.get(a.tipo_avaliacao, str(a.tipo_avaliacao)),
                    "texto": a.texto,
                }
                for a in assessments
            ]

        menu_items = self._fetch_active_menu(empresa_id, db)
        if menu_items:
            snapshot["cardapio"] = [
                {
                    "id": str(item.id_cardapio),
                    "categoria": item.categoria.value,
                    "descricao": item.descricao or "Item sem descrição",
                    "preco": str(item.preco),
                }
                for item in menu_items
            ]

        return snapshot

    def _fetch_assessments(self, empresa_id: uuid.UUID, db: Session) -> list[Assessment]:
        # Assessment não possui criado_em; LIMIT sem ORDER BY retorna registros arbitrários.
        # Para garantir "mais recentes", adicionar criado_em ao modelo numa migration futura.
        stmt = select(Assessment).where(Assessment.empresa_id == empresa_id).limit(_MAX_ASSESSMENTS)
        return list(db.scalars(stmt).all())

    def _fetch_active_menu(self, empresa_id: uuid.UUID, db: Session) -> list[Menu]:
        stmt = select(Menu).where(
            Menu.empresa_id == empresa_id,
            Menu.status.is_(True),
        )
        return list(db.scalars(stmt).all())
