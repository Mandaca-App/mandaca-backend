import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, TipoAvaliacao
from app.models.business_context import BusinessContext
from app.models.enterprise import Enterprise
from app.models.menu import Menu
from app.models.user import User
from app.schemas.chat import EnterpriseContext
from app.services.conversation_summary_service import _CONVERSATION_NOTES_HASH

_MAX_ASSESSMENTS = 5


class ChatContextService:
    def build_context(
        self,
        empresa_id: uuid.UUID,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> str:
        empresa = db.get(Enterprise, empresa_id)
        if not empresa or empresa.deleted_at is not None:
            return ""

        parts: list[str] = []

        if user_id is not None:
            usuario = db.get(User, user_id)
            if usuario is not None:
                parts.append("=== USUÁRIO ===")
                parts.append(f"Nome: {usuario.nome}")
                parts.append("Dirija-se ao usuário pelo nome quando apropriado.")
                parts.append("")

        parts.append("=== CONTEXTO DO ESTABELECIMENTO ===")

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

        notas_conversa = self._fetch_conversation_notes(empresa_id, db)
        if notas_conversa:
            parts.append("")
            parts.append("=== HISTÓRICO RESUMIDO DA CONVERSA ===")
            parts.append(notas_conversa)

        parts.append("===================================")
        return "\n".join(parts)

    def build_enterprise_context(
        self,
        empresa_id: uuid.UUID,
        db: Session,
    ) -> EnterpriseContext | None:
        empresa = db.get(Enterprise, empresa_id)
        if not empresa:
            return None

        city, state = self._extract_city_state(empresa.endereco)
        return EnterpriseContext(
            enterprise_name=empresa.nome,
            category=empresa.especialidade,
            city=city,
            state=state,
        )

    def _fetch_assessments(self, empresa_id: uuid.UUID, db: Session) -> list[Assessment]:
        # Assessment nao possui criado_em; LIMIT sem ORDER BY retorna registros arbitrarios.
        # Para garantir "mais recentes", adicionar criado_em ao modelo numa migration futura.
        stmt = select(Assessment).where(Assessment.empresa_id == empresa_id).limit(_MAX_ASSESSMENTS)
        return list(db.scalars(stmt).all())

    def _fetch_conversation_notes(self, empresa_id: uuid.UUID, db: Session) -> str | None:
        stmt = select(BusinessContext.notas_conversa).where(
            BusinessContext.empresa_id == empresa_id,
            BusinessContext.hash_contexto == _CONVERSATION_NOTES_HASH,
        )
        return db.scalar(stmt)

    def _fetch_active_menu(self, empresa_id: uuid.UUID, db: Session) -> list[Menu]:
        stmt = select(Menu).where(
            Menu.empresa_id == empresa_id,
            Menu.status.is_(True),
        )
        return list(db.scalars(stmt).all())

    def _extract_city_state(self, endereco: str | None) -> tuple[str | None, str | None]:
        if not endereco:
            return None, None

        parts = [part.strip() for part in endereco.replace("-", ",").split(",") if part.strip()]
        if len(parts) < 2:
            return None, None

        state = parts[-1].upper()
        city = parts[-2]
        if len(state) != 2:
            return city, None
        return city, state
