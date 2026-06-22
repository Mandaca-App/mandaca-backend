import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_provider import AuthProvider, SupabaseAuthProvider
from app.core.exceptions import (
    AuthEmailAlreadyExistsError,
    UserCpfAlreadyExistsError,
    UserRegistrationPersistenceError,
)
from app.models.user import User
from app.schemas.auth import UserRegisterRequest

logger = logging.getLogger(__name__)


class AuthRegistrationService:
    def __init__(self, auth_provider: AuthProvider | None = None) -> None:
        self._auth_provider = auth_provider or SupabaseAuthProvider()

    def register(self, payload: UserRegisterRequest, db: Session) -> User:
        try:
            existing_user_id = db.scalar(select(User.id_usuario).where(User.cpf == payload.cpf))
        except Exception as exc:
            raise UserRegistrationPersistenceError() from exc

        if existing_user_id is not None:
            raise UserCpfAlreadyExistsError(payload.cpf)

        try:
            auth_user = self._auth_provider.create_user(payload.email, payload.password)
        except AuthEmailAlreadyExistsError:
            raise
        except Exception as exc:
            raise UserRegistrationPersistenceError() from exc

        user = User(
            auth_user_id=auth_user.id,
            email=auth_user.email,
            tipo_usuario=payload.tipo_usuario,
            nome=payload.nome,
            cpf=payload.cpf,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception as exc:
            db.rollback()
            self._rollback_auth_user(auth_user.id)
            if isinstance(exc, IntegrityError) and _is_cpf_unique_violation(exc):
                raise UserCpfAlreadyExistsError(payload.cpf) from exc
            raise UserRegistrationPersistenceError() from exc

        return user

    def _rollback_auth_user(self, auth_user_id: UUID) -> None:
        try:
            self._auth_provider.delete_user(auth_user_id)
        except Exception:
            logger.exception("Falha ao remover usuario do Supabase Auth durante rollback.")


def _is_cpf_unique_violation(exc: IntegrityError) -> bool:
    original_error = exc.orig
    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name is not None:
        return constraint_name == "usuarios_cpf_key"
    return "usuarios.cpf" in str(original_error).lower()
