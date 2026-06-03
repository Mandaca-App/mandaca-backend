from decimal import Decimal
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import (
    InvalidImageTypeError,
    MenuContentUnreadableError,
    MenuExtractionError,
)
from app.models.menu import CategoriaCardapio
from app.schemas.menus import MenuItemExtracted

_SYSTEM_PROMPT = (
    "Você é um extrator de dados especializado em cardápios brasileiros. "
    "Dado o texto de um cardápio, extraia todos os pratos e bebidas identificáveis. "
    "Para cada item retorne: descricao (nome do prato, máx 255 chars), "
    "historia (história,origem do prato ou detalhes de composição,vazio se ausente,máx 500 chars),"
    "preco (número decimal em reais, 0.0 se ausente), "
    "categoria (uma de: entrada, prato_principal, sobremesa, bebida, lanche). "
    "Se o texto não for um cardápio ou nenhum prato puder ser identificado, "
    "retorne itens como lista vazia."
)

_CATEGORIA_MAP: dict[str, CategoriaCardapio] = {
    "entrada": CategoriaCardapio.ENTRADA,
    "prato_principal": CategoriaCardapio.PRATO_PRINCIPAL,
    "sobremesa": CategoriaCardapio.SOBREMESA,
    "bebida": CategoriaCardapio.BEBIDA,
    "lanche": CategoriaCardapio.LANCHE,
}


class _ItemExtraido(BaseModel):
    descricao: str = Field(..., max_length=255)
    historia: str = Field(default="", max_length=500)
    preco: float = Field(default=0.0)
    categoria: Literal["entrada", "prato_principal", "sobremesa", "bebida", "lanche"] = Field(
        default="prato_principal"
    )


class _ResultadoExtracao(BaseModel):
    itens: list[_ItemExtraido]


class MenuExtractionService:
    @staticmethod
    def _get_gemini_client() -> genai.Client:
        return genai.Client(api_key=settings.gemini_api_key)

    def extract(self, texto: str) -> list[MenuItemExtracted]:
        client = self._get_gemini_client()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=texto,
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": _ResultadoExtracao.model_json_schema(),
                    "temperature": 0,
                },
            )

            resultado = _ResultadoExtracao.model_validate_json(response.text)

        except Exception as exc:
            raise MenuExtractionError() from exc

        if not resultado.itens:
            raise MenuContentUnreadableError()

        return [
            MenuItemExtracted(
                descricao=item.descricao or None,
                historia=item.historia,
                preco=Decimal(str(item.preco)),
                categoria=_CATEGORIA_MAP[item.categoria],
            )
            for item in resultado.itens
        ]

    def _transcribe_image(self, image_bytes: bytes, content_type: str) -> str:
        """Usa Gemini Vision para converter a imagem do cardápio em texto."""
        client = self._get_gemini_client()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                    # Você pode passar a string de texto diretamente na lista
                    "Transcreva todo o texto visível nesta imagem de cardápio, "
                    "incluindo nomes dos pratos, descrições, preços e categorias. "
                    "Mantenha a estrutura e formatação original.",
                ],
            )
            return response.text or ""
        except Exception as exc:
            raise MenuExtractionError("Falha ao transcrever a imagem do cardápio.") from exc

    def scan_from_image(self, image_bytes: bytes, content_type: str) -> list[MenuItemExtracted]:
        """Transcreve a imagem via Gemini Vision e extrai os itens do cardápio."""
        if not content_type or not content_type.startswith("image/"):
            raise InvalidImageTypeError()

        texto = self._transcribe_image(image_bytes, content_type)
        return self.extract(texto)
