"""
Testes unitários para MenuExtractionService.

Foco: lógica de extração e mapeamento, isolada da IA.
Estratégia: cliente Gemini completamente mockado.
Não há chamadas de rede nestes testes.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    InvalidImageTypeError,
    MenuContentUnreadableError,
    MenuExtractionError,
)
from app.models.menu import CategoriaCardapio
from app.services.menu_extraction_service import MenuExtractionService

FAKE_MENU_TEXT = "Baião de dois R$18,00 | Carne de sol R$25,00 | Suco de umbu R$8,00"
FAKE_UNREADABLE_TEXT = "asdkjh aslkdjh lkajsd lkajsdlkj"
FAKE_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_gemini_response(json_text: str) -> MagicMock:
    response = MagicMock()
    response.text = json_text
    return response


def _mock_gemini_client(json_text: str) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = _mock_gemini_response(json_text)
    return client


# ---------------------------------------------------------------------------
# extract — cenário 1: extração bem-sucedida
# ---------------------------------------------------------------------------


def test_given_valid_menu_text_when_extracted_then_returns_items():
    # GIVEN
    service = MenuExtractionService()
    payload = (
        '{"itens": ['
        '{"descricao": "Baião de dois", "historia": "", "preco": 18.0, '
        '"categoria": "prato_principal"},'
        '{"descricao": "Suco de umbu", "historia": "", "preco": 8.0, '
        '"categoria": "bebida"}'
        "]}"
    )
    client = _mock_gemini_client(payload)

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN
        result = service.extract(FAKE_MENU_TEXT)

    # THEN
    assert len(result) == 2
    assert result[0].descricao == "Baião de dois"
    assert result[0].categoria == CategoriaCardapio.PRATO_PRINCIPAL
    assert result[0].preco == Decimal("18.0")
    assert result[1].categoria == CategoriaCardapio.BEBIDA


# ---------------------------------------------------------------------------
# extract — cenário 2: campos ausentes recebem defaults neutros
# ---------------------------------------------------------------------------


def test_given_menu_without_price_when_extracted_then_preco_is_zero():
    # GIVEN
    service = MenuExtractionService()
    payload = (
        '{"itens": ['
        '{"descricao": "Prato sem preço", "historia": "", "preco": 0.0, '
        '"categoria": "prato_principal"}'
        "]}"
    )
    client = _mock_gemini_client(payload)

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN
        result = service.extract(FAKE_MENU_TEXT)

    # THEN
    assert len(result) == 1
    assert result[0].preco == Decimal("0.0")
    assert result[0].historia == ""


def test_given_menu_without_historia_when_extracted_then_historia_is_empty():
    # GIVEN
    service = MenuExtractionService()
    payload = (
        '{"itens": ['
        '{"descricao": "Tapioca", "historia": "", "preco": 12.0, "categoria": "lanche"}'
        "]}"
    )
    client = _mock_gemini_client(payload)

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN
        result = service.extract(FAKE_MENU_TEXT)

    # THEN
    assert result[0].historia == ""


# ---------------------------------------------------------------------------
# extract — cenário 3: falha na IA → MenuExtractionError
# ---------------------------------------------------------------------------


def test_given_ai_failure_when_extracted_then_raises_extraction_error():
    # GIVEN
    service = MenuExtractionService()
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("timeout")

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN / THEN
        with pytest.raises(MenuExtractionError):
            service.extract(FAKE_MENU_TEXT)


def test_given_invalid_json_response_when_extracted_then_raises_extraction_error():
    # GIVEN
    service = MenuExtractionService()
    client = _mock_gemini_client("isso nao e json valido")

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN / THEN
        with pytest.raises(MenuExtractionError):
            service.extract(FAKE_MENU_TEXT)


# ---------------------------------------------------------------------------
# extract — cenário 4: texto não é cardápio → MenuContentUnreadableError
# ---------------------------------------------------------------------------


def test_given_unreadable_content_when_extracted_then_raises_unreadable_error():
    # GIVEN
    service = MenuExtractionService()
    client = _mock_gemini_client('{"itens": []}')

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN / THEN
        with pytest.raises(MenuContentUnreadableError):
            service.extract(FAKE_UNREADABLE_TEXT)


# ---------------------------------------------------------------------------
# extract — mapeamento de todas as categorias
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("categoria_str", "categoria_enum"),
    [
        ("entrada", CategoriaCardapio.ENTRADA),
        ("prato_principal", CategoriaCardapio.PRATO_PRINCIPAL),
        ("sobremesa", CategoriaCardapio.SOBREMESA),
        ("bebida", CategoriaCardapio.BEBIDA),
        ("lanche", CategoriaCardapio.LANCHE),
    ],
)
def test_given_each_categoria_when_extracted_then_maps_correctly(categoria_str, categoria_enum):
    # GIVEN
    service = MenuExtractionService()
    payload = (
        f'{{"itens": [{{"descricao": "Item", "historia": "", "preco": 10.0, '
        f'"categoria": "{categoria_str}"}}]}}'
    )
    client = _mock_gemini_client(payload)

    with patch(
        "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
        return_value=client,
    ):
        # WHEN
        result = service.extract("qualquer texto")

    # THEN
    assert result[0].categoria == categoria_enum


# ---------------------------------------------------------------------------
# scan_from_image — validação de tipo e pipeline imagem→texto→itens
# ---------------------------------------------------------------------------


def test_given_valid_image_when_scan_then_returns_extracted_items():
    # GIVEN
    service = MenuExtractionService()

    payload = (
        '{"itens": ['
        '{"descricao": "Baião de dois", "historia": "", "preco": 18.0, '
        '"categoria": "prato_principal"}'
        "]}"
    )
    gemini_client = _mock_gemini_client(payload)

    with patch.object(service, "_transcribe_image", return_value=FAKE_MENU_TEXT):
        with patch(
            "app.services.menu_extraction_service.MenuExtractionService._get_gemini_client",
            return_value=gemini_client,
        ):
            # WHEN
            result = service.scan_from_image(FAKE_IMAGE_BYTES, "image/png")

    # THEN
    assert len(result) == 1
    assert result[0].descricao == "Baião de dois"
    assert result[0].categoria == CategoriaCardapio.PRATO_PRINCIPAL


@pytest.mark.parametrize("content_type", [None, "", "application/pdf", "text/plain"])
def test_given_invalid_content_type_when_scan_then_raises_invalid_image_error(content_type):
    # GIVEN
    service = MenuExtractionService()

    # WHEN / THEN
    with pytest.raises(InvalidImageTypeError):
        service.scan_from_image(FAKE_IMAGE_BYTES, content_type)


def test_given_transcription_failure_when_scan_then_raises_extraction_error():
    # GIVEN
    service = MenuExtractionService()

    with patch.object(service, "_transcribe_image", side_effect=MenuExtractionError()):
        # WHEN / THEN
        with pytest.raises(MenuExtractionError):
            service.scan_from_image(FAKE_IMAGE_BYTES, "image/jpeg")
