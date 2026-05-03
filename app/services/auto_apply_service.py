from datetime import time
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AutoApplyPersistenceError,
    EnterpriseNotFoundError,
    FieldNotAllowedError,
    InvalidFieldValueError,
    MenuNotFoundError,
)
from app.models.enterprise import Enterprise
from app.models.menu import Menu
from app.schemas.auto_apply import (
    AutoApplyRequest,
    AutoApplyResponse,
    AutoApplyTarget,
    SuggestionStatus,
)

# Whitelist: campo lógico (enviado pela IA) -> coluna real no modelo.
# Os nomes coincidem com as colunas reais; o LLM emite exatamente esses nomes.
_ENTERPRISE_FIELD_MAP: dict[str, str] = {
    "historia": "historia",
    "telefone": "telefone",
    "endereco": "endereco",
    "hora_abrir": "hora_abrir",
    "hora_fechar": "hora_fechar",
}

_ENTERPRISE_TIME_FIELDS = {"hora_abrir", "hora_fechar"}

# Inversão intencional: o modelo Menu usa nomes históricos de coluna.
# "descricao" armazena o nome exibido do item; "historia" armazena a descrição longa.
_MENU_FIELD_MAP: dict[str, str] = {
    "nome": "descricao",
    "descricao": "historia",
    "preco": "preco",
}


class AutoApplyService:
    def apply(
        self,
        enterprise_id: UUID,
        payload: AutoApplyRequest,
        db: Session,
        *,
        commit: bool = True,
    ) -> AutoApplyResponse:
        if payload.target == AutoApplyTarget.ENTERPRISE:
            self._apply_to_enterprise(enterprise_id, payload, db)
        else:
            self._apply_to_menu_item(payload, db)

        if commit:
            self._persist(db)

        return AutoApplyResponse(
            campo_alterado=payload.campo_para_alterar,
            status=SuggestionStatus.APPLIED,
        )

    def _apply_to_enterprise(
        self, enterprise_id: UUID, payload: AutoApplyRequest, db: Session
    ) -> None:
        if payload.campo_para_alterar not in _ENTERPRISE_FIELD_MAP:
            raise FieldNotAllowedError(payload.campo_para_alterar)

        enterprise = self._get_enterprise(enterprise_id, db)
        coluna = _ENTERPRISE_FIELD_MAP[payload.campo_para_alterar]
        valor = self._coerce_enterprise_value(payload.campo_para_alterar, payload.novo_valor)
        setattr(enterprise, coluna, valor)

    def _apply_to_menu_item(self, payload: AutoApplyRequest, db: Session) -> None:
        if payload.campo_para_alterar not in _MENU_FIELD_MAP:
            raise FieldNotAllowedError(payload.campo_para_alterar)

        menu = self._get_menu(payload.menu_item_id, db)
        coluna = _MENU_FIELD_MAP[payload.campo_para_alterar]
        valor = self._coerce_menu_value(payload.campo_para_alterar, payload.novo_valor)
        setattr(menu, coluna, valor)

    def _get_enterprise(self, enterprise_id: UUID, db: Session) -> Enterprise:
        enterprise = db.get(Enterprise, enterprise_id)
        if not enterprise:
            raise EnterpriseNotFoundError(enterprise_id)
        return enterprise

    def _get_menu(self, menu_item_id: UUID | None, db: Session) -> Menu:
        menu = db.execute(
            select(Menu).where(
                Menu.id_cardapio == menu_item_id,
                Menu.status.is_(True),
            )
        ).scalar_one_or_none()
        if not menu:
            raise MenuNotFoundError(menu_item_id)
        return menu

    def _coerce_enterprise_value(self, campo_logico: str, novo_valor: str) -> str | time:
        if campo_logico in _ENTERPRISE_TIME_FIELDS:
            try:
                return time.fromisoformat(novo_valor)
            except ValueError as exc:
                raise InvalidFieldValueError(
                    campo_logico, "horário inválido, esperado HH:MM"
                ) from exc
        return novo_valor

    def _coerce_menu_value(self, campo_logico: str, novo_valor: str) -> str | Decimal:
        if campo_logico == "preco":
            try:
                return Decimal(novo_valor)
            except InvalidOperation as exc:
                raise InvalidFieldValueError(campo_logico, "preço inválido") from exc
        return novo_valor

    def _persist(self, db: Session) -> None:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise AutoApplyPersistenceError() from exc
