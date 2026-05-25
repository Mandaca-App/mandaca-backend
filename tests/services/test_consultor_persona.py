import pytest
from pydantic import ValidationError

from app.schemas.chat import EnterpriseContext
from app.services.prompts.consultor_persona import build_system_prompt


def test_given_no_context_when_build_system_prompt_then_returns_generic_valid_prompt():
    # WHEN
    prompt = build_system_prompt(None)

    # THEN
    assert "Consultor Mandaca" in prompt
    assert "nenhum contexto estruturado" in prompt
    assert "turismo e gastronomia" in prompt
    assert "Recusa para fora de escopo" in prompt
    assert "{" not in prompt
    assert "}" not in prompt


def test_given_enterprise_context_when_build_system_prompt_then_personalizes_context():
    # GIVEN
    context = EnterpriseContext(
        enterprise_name="Pousada Raiz",
        category="hospedagem",
        city="Triunfo",
        state="PE",
    )

    # WHEN
    prompt = build_system_prompt(context)

    # THEN
    assert "Pousada Raiz" in prompt
    assert "hospedagem" in prompt
    assert "Triunfo" in prompt
    assert "PE" in prompt


def test_given_empty_enterprise_context_when_build_system_prompt_then_uses_fallback():
    # WHEN
    prompt = build_system_prompt(EnterpriseContext())

    # THEN
    assert "contexto estruturado vazio" in prompt
    assert "Consultor Mandaca" in prompt


def test_given_extra_field_when_enterprise_context_created_then_rejects_it():
    # WHEN / THEN
    with pytest.raises(ValidationError):
        EnterpriseContext(enterprise_name="X", segmento="fora da whitelist")


def test_given_prompt_when_built_then_contains_required_sections():
    # GIVEN
    context = EnterpriseContext(
        enterprise_name="Bistro Sertao",
        category="restaurante",
        city="Caruaru",
        state="PE",
    )

    # WHEN
    prompt = build_system_prompt(context)

    # THEN
    assert "Consultor Mandaca" in prompt
    assert "Tom de voz:" in prompt
    assert "Dominio permitido:" in prompt
    assert "Recusa para fora de escopo:" in prompt
    assert "Formato de resposta:" in prompt
    assert "Bistro Sertao" in prompt
