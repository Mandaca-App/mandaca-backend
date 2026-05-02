import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, TipoAvaliacao
from app.models.enterprise import Enterprise
from app.models.menu import Menu

_MAX_ASSESSMENTS = 5


class ChatContextService:
    def build_context(self, empresa_id: uuid.UUID, db: Session) -> str:
        empresa = db.get(Enterprise, empresa_id)
        if not empresa or empresa.deleted_at is not None:
            return ""

        parts: list[str] = ["=== CONTEXTO DO ESTABELECIMENTO ==="]

        parts.append(f"Nome: {empresa.nome}")
        if empresa.especialidade:
            parts.append(f"Especialidade: {empresa.especialidade}")
        if empresa.historia:
            parts.append(f"Historia: {empresa.historia}")
        if empresa.hora_abrir and empresa.hora_fechar:
            parts.append(f"Horario: {empresa.hora_abrir} - {empresa.hora_fechar}")

        assessments = self._fetch_assessments(empresa_id, db)
        if assessments:
            parts.append("")
            parts.append("Avaliacoes recentes dos clientes:")
            for a in assessments:
                parts.append(f'- [{TipoAvaliacao(a.tipo_avaliacao).name.lower()}] "{a.texto}"')

        menu_items = self._fetch_active_menu(empresa_id, db)
        if menu_items:
            parts.append("")
            parts.append("Cardapio ativo:")
            for item in menu_items:
                descricao = item.descricao or "Item sem descricao"
                parts.append(f"- [{item.categoria.value}] {descricao} - R$ {item.preco:.2f}")

        parts.append("===================================")
        return "\n".join(parts)

    def _fetch_assessments(self, empresa_id: uuid.UUID, db: Session) -> list[Assessment]:
        # Assessment nao possui criado_em; LIMIT sem ORDER BY retorna registros arbitrarios.
        # Para garantir "mais recentes", adicionar criado_em ao modelo numa migration futura.
        stmt = select(Assessment).where(Assessment.empresa_id == empresa_id).limit(_MAX_ASSESSMENTS)
        return list(db.scalars(stmt).all())

    def _fetch_active_menu(self, empresa_id: uuid.UUID, db: Session) -> list[Menu]:
        stmt = select(Menu).where(
            Menu.empresa_id == empresa_id,
            Menu.status.is_(True),
        )
        return list(db.scalars(stmt).all())
