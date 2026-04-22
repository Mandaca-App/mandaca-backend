from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.business_contexts import (
    BusinessContextResponse,
    BusinessContextUpdate,
)
from app.services.business_context_service import BusinessContextService

router = APIRouter(prefix="/business-contexts", tags=["business-contexts"])
business_context_service = BusinessContextService()


@router.get("/by-enterprise/{enterprise_id}", response_model=list[BusinessContextResponse])
async def list_contexts_by_enterprise(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> list[BusinessContextResponse]:
    return business_context_service.list_by_enterprise(enterprise_id, db)


@router.get("/{context_id}", response_model=BusinessContextResponse)
async def get_context(
    context_id: UUID,
    db: Session = Depends(get_db),
) -> BusinessContextResponse:
    return business_context_service.get_by_id(context_id, db)


@router.post(
    "/{enterprise_id}",
    response_model=BusinessContextResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_context_from_enterprise(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
) -> BusinessContextResponse:
    """Monta automaticamente o snapshot do negócio (empresa + avaliações + cardápio)
    e persiste como novo contexto. Nenhum payload é necessário."""
    return business_context_service.create_from_enterprise(enterprise_id, db)


@router.put("/{context_id}", response_model=BusinessContextResponse)
async def update_context(
    context_id: UUID,
    payload: BusinessContextUpdate,
    db: Session = Depends(get_db),
) -> BusinessContextResponse:
    return business_context_service.update(context_id, payload, db)


@router.delete("/{context_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_context(
    context_id: UUID,
    db: Session = Depends(get_db),
):
    business_context_service.delete(context_id, db)
    return None
