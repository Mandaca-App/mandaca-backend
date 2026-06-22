import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.auth_provider import AuthProviderUser
from app.core.exceptions import (
    AuthEmailAlreadyExistsError,
    UserCpfAlreadyExistsError,
    UserRegistrationPersistenceError,
)
from app.models.user import TipoUsuario, User
from app.schemas.auth import UserRegisterRequest
from app.services.auth_registration_service import AuthRegistrationService


class FakeAuthProvider:
    def __init__(self, auth_user_id: uuid.UUID | None = None, email: str = "novo@email.com"):
        self.auth_user_id = auth_user_id or uuid.uuid4()
        self.email = email
        self.deleted_ids: list[uuid.UUID] = []

    def create_user(self, email: str, password: str) -> AuthProviderUser:
        return AuthProviderUser(id=self.auth_user_id, email=email)

    def delete_user(self, auth_user_id: uuid.UUID) -> None:
        self.deleted_ids.append(auth_user_id)


def _payload(**overrides) -> UserRegisterRequest:
    data = {
        "email": "novo@email.com",
        "password": "Senha@123",
        "tipo_usuario": TipoUsuario.EMPREENDEDOR,
        "nome": "Novo Usuario",
        "cpf": "12345678901",
    }
    data.update(overrides)
    return UserRegisterRequest(**data)


def _count_users(db) -> int:
    return db.scalar(select(func.count()).select_from(User))


def test_given_valid_payload_when_register_then_creates_auth_and_local_user(db):
    auth_user_id = uuid.uuid4()
    provider = FakeAuthProvider(auth_user_id=auth_user_id)
    service = AuthRegistrationService(auth_provider=provider)

    user = service.register(_payload(), db)

    assert user.auth_user_id == auth_user_id
    assert user.email == "novo@email.com"
    assert user.nome == "Novo Usuario"
    assert user.cpf == "12345678901"
    assert _count_users(db) == 1
    assert provider.deleted_ids == []


def test_given_email_already_exists_when_register_then_raises_and_does_not_persist(db):
    class DuplicateProvider(FakeAuthProvider):
        def create_user(self, email: str, password: str) -> AuthProviderUser:
            raise AuthEmailAlreadyExistsError(email)

    service = AuthRegistrationService(auth_provider=DuplicateProvider())

    with pytest.raises(AuthEmailAlreadyExistsError):
        service.register(_payload(), db)

    assert _count_users(db) == 0


def test_given_cpf_already_exists_when_register_then_does_not_call_auth_provider(db):
    db.add(
        User(
            tipo_usuario=TipoUsuario.TURISTA,
            nome="Usuario Existente",
            cpf="12345678901",
        )
    )
    db.commit()

    class UnexpectedCreateProvider(FakeAuthProvider):
        def create_user(self, email: str, password: str) -> AuthProviderUser:
            raise AssertionError("Auth provider nao deve ser chamado para CPF duplicado")

    service = AuthRegistrationService(auth_provider=UnexpectedCreateProvider())

    with pytest.raises(UserCpfAlreadyExistsError):
        service.register(_payload(), db)

    assert _count_users(db) == 1


def test_given_concurrent_cpf_conflict_when_register_then_rolls_back_auth_user(db):
    db.add(
        User(
            tipo_usuario=TipoUsuario.TURISTA,
            nome="Usuario Existente",
            cpf="12345678901",
        )
    )
    db.commit()
    provider = FakeAuthProvider()
    service = AuthRegistrationService(auth_provider=provider)

    with patch.object(db, "scalar", return_value=None):
        with pytest.raises(UserCpfAlreadyExistsError):
            service.register(_payload(), db)

    assert provider.deleted_ids == [provider.auth_user_id]
    assert _count_users(db) == 1


def test_given_local_persistence_failure_when_register_then_rolls_back_auth_user(db):
    auth_user_id = uuid.uuid4()
    provider = FakeAuthProvider(auth_user_id=auth_user_id)
    service = AuthRegistrationService(auth_provider=provider)

    with patch.object(db, "commit", side_effect=Exception("db down")):
        with pytest.raises(UserRegistrationPersistenceError):
            service.register(_payload(), db)

    assert provider.deleted_ids == [auth_user_id]
    assert _count_users(db) == 0


def test_given_auth_provider_failure_when_register_then_returns_registration_error(db):
    class BrokenProvider(FakeAuthProvider):
        def create_user(self, email: str, password: str) -> AuthProviderUser:
            raise RuntimeError("supabase down")

    service = AuthRegistrationService(auth_provider=BrokenProvider())

    with pytest.raises(UserRegistrationPersistenceError):
        service.register(_payload(), db)

    assert _count_users(db) == 0
