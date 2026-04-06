from datetime import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.models.enterprise import Enterprise
from app.models.user import User

router = APIRouter(prefix="/enterprises", tags=["enterprises"])


class EnterpriseCreate(BaseModel):
    nome: str
    especialidade: Optional[str] = None
    endereco: Optional[str] = None
    historia: Optional[str] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Optional[str] = None
    usuario_id: UUID


class EnterpriseUpdate(BaseModel):
    nome: Optional[str] = None
    especialidade: Optional[str] = None
    endereco: Optional[str] = None
    historia: Optional[str] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Optional[str] = None
    usuario_id: Optional[UUID] = None


class EnterpriseResponse(BaseModel):
    id_empresa: UUID
    nome: str
    especialidade: Optional[str] = None
    endereco: Optional[str] = None
    historia: Optional[str] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Optional[str] = None
    usuario_id: UUID

    model_config = {"from_attributes": True}


class EnterprisePercentageResponse(BaseModel):
    id_empresa: UUID
    nome: str
    porcentagem: float
    campos_preenchidos: list[str]
    campos_faltando: list[str]


class PhotoOverviewResponse(BaseModel):
    url_foto_empresa: Optional[str] = None

    model_config = {"from_attributes": True}


class EnterpriseOverviewResponse(BaseModel):
    id_empresa: UUID
    endereco: Optional[str] = None
    historia: Optional[str] = None
    fotos: list[PhotoOverviewResponse]


@router.get("/overview", response_model=EnterpriseOverviewResponse)
def get_enterprise_overview(
    enterprise_id: UUID,
    db: Session = Depends(get_db),
):
    """Retorna endereco, historia e todas as fotos de uma empresa."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )

    return EnterpriseOverviewResponse(
        id_empresa=enterprise.id_empresa,
        endereco=enterprise.endereco,
        historia=enterprise.historia,
        fotos=[
            PhotoOverviewResponse(
                url_foto_empresa=photo.url_foto_empresa,
            )
            for photo in enterprise.fotos
        ],
    )


@router.get("/", response_model=list[EnterpriseResponse])
def list_enterprises(db: Session = Depends(get_db)):
    """Retorna uma lista de todas as empresas no formato EnterpriseResponse."""
    return db.query(Enterprise).all()


@router.get("/{enterprise_id}", response_model=EnterpriseResponse)
def get_enterprise(enterprise_id: UUID, db: Session = Depends(get_db)):
    """Retorna uma empresa específica pelo ID no formato EnterpriseResponse."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )
    return enterprise


@router.post("/", response_model=EnterpriseResponse, status_code=status.HTTP_201_CREATED)
def create_enterprise(payload: EnterpriseCreate, db: Session = Depends(get_db)):
    """Endpoint que cria uma nova empresa a partir dos dados enviados no corpo da requisição."""
    existing_name = db.query(Enterprise).filter(Enterprise.nome == payload.nome).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma empresa com esse nome",
        )

    user = db.get(User, payload.usuario_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário vinculado não encontrado",
        )

    if user.empresa is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já possui uma empresa vinculada",
        )

    enterprise = Enterprise(
        nome=payload.nome,
        especialidade=payload.especialidade,
        endereco=payload.endereco,
        historia=payload.historia,
        hora_abrir=payload.hora_abrir,
        hora_fechar=payload.hora_fechar,
        telefone=payload.telefone,
        usuario_id=payload.usuario_id,
    )

    db.add(enterprise)
    db.commit()
    db.refresh(enterprise)

    return enterprise


@router.get("/percentage/{enterprise_id}", response_model=EnterprisePercentageResponse)
def enterprise_percentage(enterprise_id: UUID, db: Session = Depends(get_db)):
    """Retorna a porcentagem de preenchimento do perfil da empresa pelo ID."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )

    # campos opcionais que contribuem para o perfil completo
    campos = {
        "especialidade": enterprise.especialidade,
        "endereco": enterprise.endereco,
        "historia": enterprise.historia,
        "hora_abrir": enterprise.hora_abrir,
        "hora_fechar": enterprise.hora_fechar,
        "telefone": enterprise.telefone,
        "fotos": enterprise.fotos or None,  # lista vazia = não preenchido
        "cardapios": enterprise.cardapios or None,  # lista vazia = não preenchido
    }

    preenchidos = [campo for campo, valor in campos.items() if valor is not None]
    faltando = [campo for campo, valor in campos.items() if valor is None]

    porcentagem = round(20 + len(preenchidos) / len(campos) * 80, 1)

    return EnterprisePercentageResponse(
        id_empresa=enterprise.id_empresa,
        nome=enterprise.nome,
        porcentagem=porcentagem,
        campos_preenchidos=preenchidos,
        campos_faltando=faltando,
    )


@router.put("/{enterprise_id}", response_model=EnterpriseResponse)
def update_enterprise(
    enterprise_id: UUID,
    payload: EnterpriseUpdate,
    db: Session = Depends(get_db),
):
    """Endpoint que atualiza os dados de uma empresa específica informada pelo ID."""
    enterprise = db.get(Enterprise, enterprise_id)
    if not enterprise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )

    if payload.nome is not None and payload.nome != enterprise.nome:
        existing_name = (
            db.query(Enterprise)
            .filter(
                Enterprise.nome == payload.nome,
                Enterprise.id_empresa != enterprise_id,
            )
            .first()
        )
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma empresa com esse nome",
            )
        enterprise.nome = payload.nome

    if payload.usuario_id is not None and payload.usuario_id != enterprise.usuario_id:
        user = db.get(User, payload.usuario_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário vinculado não encontrado",
            )

        if user.empresa is not None and user.empresa.id_empresa != enterprise.id_empresa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este usuário já está vinculado a outra empresa",
            )

        enterprise.usuario_id = payload.usuario_id

    if payload.especialidade is not None:
        enterprise.especialidade = payload.especialidade
    if payload.endereco is not None:
        enterprise.endereco = payload.endereco
    if payload.historia is not None:
        enterprise.historia = payload.historia
    if payload.hora_abrir is not None:
        enterprise.hora_abrir = payload.hora_abrir
    if payload.hora_fechar is not None:
        enterprise.hora_fechar = payload.hora_fechar
    if payload.telefone is not None:
        enterprise.telefone = payload.telefone

    db.commit()
    db.refresh(enterprise)

    return enterprise
