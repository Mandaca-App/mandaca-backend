import uuid

from app.core.exceptions import AuthEmailAlreadyExistsError, UserRegistrationPersistenceError
from app.main import app
from app.models.user import TipoUsuario, User
from app.routers.auth import get_auth_registration_service


def _payload(**overrides):
    data = {
        "email": "novo@email.com",
        "password": "Senha@123",
        "tipo_usuario": "empreendedor",
        "nome": "Novo Usuario",
        "cpf": "12345678901",
    }
    data.update(overrides)
    return data


class SuccessfulAuthService:
    def register(self, payload, db):
        return User(
            id_usuario=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            auth_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            email=payload.email,
            tipo_usuario=payload.tipo_usuario,
            nome=payload.nome,
            cpf=payload.cpf,
        )


def test_given_valid_payload_when_register_then_returns_201_without_sensitive_data(client):
    app.dependency_overrides[get_auth_registration_service] = lambda: SuccessfulAuthService()

    response = client.post("/auth/register", json=_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["auth_user_id"] == "00000000-0000-0000-0000-000000000002"
    assert data["email"] == "novo@email.com"
    assert data["tipo_usuario"] == TipoUsuario.EMPREENDEDOR
    assert data["nome"] == "Novo Usuario"
    assert "password" not in data


def test_given_existing_email_when_register_then_returns_400(client):
    class DuplicateEmailService:
        def register(self, payload, db):
            raise AuthEmailAlreadyExistsError(payload.email)

    app.dependency_overrides[get_auth_registration_service] = lambda: DuplicateEmailService()

    response = client.post("/auth/register", json=_payload())

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()
    assert "uso" in response.json()["detail"].lower()


def test_given_local_persistence_failure_when_register_then_returns_500(client):
    class FailingPersistenceService:
        def register(self, payload, db):
            raise UserRegistrationPersistenceError()

    app.dependency_overrides[get_auth_registration_service] = lambda: FailingPersistenceService()

    response = client.post("/auth/register", json=_payload())

    assert response.status_code == 500
    assert response.json()["detail"] == "Falha no cadastro do usuario."


def test_given_weak_password_when_register_then_returns_422(client):
    response = client.post("/auth/register", json=_payload(password="fraca123"))

    assert response.status_code == 422


def test_given_invalid_email_when_register_then_returns_422(client):
    response = client.post("/auth/register", json=_payload(email="email-invalido"))

    assert response.status_code == 422
