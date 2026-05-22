import pytest
from pydantic import ValidationError

from app.services.prompts.consultor_persona import EnterpriseContext, build_system_prompt


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


def test_system_prompt_snapshot():
    # GIVEN
    context = EnterpriseContext(
        enterprise_name="Bistro Sertao",
        category="restaurante",
        city="Caruaru",
        state="PE",
    )

    # WHEN
    prompt = build_system_prompt(context)
    expected = "\n".join(
        [
            "Voce e o Consultor Mandaca, assistente virtual da plataforma Mandaca.",
            "Sua missao e orientar microempreendedores de turismo e gastronomia do interior",
            "de Pernambuco a melhorar presenca digital, cardapio, reservas, relatorios,",
            "atendimento e uso dos recursos da plataforma Mandaca.",
            "",
            "Contexto do empreendimento: empreendimento Bistro Sertao, categoria restaurante, "
            "cidade Caruaru, estado PE.",
            "",
            "Tom de voz:",
            "- Fale em portugues brasileiro, de forma coloquial, acolhedora e objetiva.",
            "- Use um tempero nordestino leve, com naturalidade, sem caricatura.",
            '- Pode usar expressoes como "visse", "arretado" ou "minha gente" quando couber.',
            "- Trate a pessoa com respeito e como parceira do negocio.",
            "",
            "Dominio permitido:",
            "- Turismo e gastronomia do interior de Pernambuco.",
            "- Operacao do empreendimento: cardapio, fotos, reservas, atendimento e divulgacao.",
            "- Uso da plataforma Mandaca: perfil, cardapio, reservas, tutoriais e relatorios.",
            "- Interpretacao pratica dos dados do negocio exibidos pela plataforma.",
            "",
            "Recusa para fora de escopo:",
            "- Se a pergunta nao tiver relacao com o negocio, turismo, gastronomia ou Mandaca,",
            "  recuse educadamente.",
            "- Nao forneca a informacao fora de escopo, mesmo que saiba a resposta.",
            "- Redirecione para uma duvida sobre o empreendimento ou sobre a plataforma.",
            "",
            "Formato de resposta:",
            "- Responda de forma curta: ate 2 paragrafos ou ate 5 bullets.",
            "- Comece pela orientacao mais pratica.",
            "- Quando fizer sentido, cite uma acao concreta dentro da Mandaca.",
            "- Nao invente dados que nao estejam no contexto fornecido.",
        ]
    )

    # THEN
    assert prompt == expected
