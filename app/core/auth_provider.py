from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.core.exceptions import AuthEmailAlreadyExistsError
from app.core.supabase_client import supabase


@dataclass(frozen=True)
class AuthProviderUser:
    id: UUID
    email: str


class AuthProvider(Protocol):
    def create_user(self, email: str, password: str) -> AuthProviderUser:
        pass

    def delete_user(self, auth_user_id: UUID) -> None:
        pass


class SupabaseAuthProvider:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client or supabase

    def create_user(self, email: str, password: str) -> AuthProviderUser:
        try:
            response = self._client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                }
            )
        except Exception as exc:
            if _looks_like_duplicate_email(exc):
                raise AuthEmailAlreadyExistsError(email) from exc
            raise

        user = _extract_response_user(response)
        auth_user_id = _extract_attr(user, "id")
        user_email = _extract_attr(user, "email") or email
        if auth_user_id is None:
            raise ValueError("Supabase Auth nao retornou id do usuario.")

        return AuthProviderUser(id=UUID(str(auth_user_id)), email=str(user_email))

    def delete_user(self, auth_user_id: UUID) -> None:
        self._client.auth.admin.delete_user(str(auth_user_id))


def _extract_response_user(response: Any) -> Any:
    if isinstance(response, dict):
        return response.get("user")
    return getattr(response, "user", response)


def _extract_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _looks_like_duplicate_email(exc: Exception) -> bool:
    message = str(exc).lower()
    duplicate_markers = (
        "already registered",
        "already exists",
        "already been registered",
        "email_exists",
        "email already",
        "user already",
    )
    return any(marker in message for marker in duplicate_markers)
