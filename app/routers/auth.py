from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserRegisterResponse
from app.services.auth_registration_service import AuthRegistrationService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_registration_service() -> AuthRegistrationService:
    return AuthRegistrationService()


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
    service: AuthRegistrationService = Depends(get_auth_registration_service),
) -> User:
    return service.register(payload, db)
