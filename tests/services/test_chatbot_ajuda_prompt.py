from app.services.prompts.chatbot_ajuda_tutorial import (
    ChatbotAjudaPromptModule,
    build_chatbot_ajuda_system_prompt,
)


def test_system_prompt_contains_onboarding_scope_and_real_features():
    prompt = build_chatbot_ajuda_system_prompt()

    assert "Chatbot de Onboarding da Mandaca" in prompt
    assert "Cardapio e fotos dos pratos" in prompt
    assert "Reservas" in prompt
    assert "Relatorios de IA" in prompt
    assert "Fallback fora do escopo" in prompt
    assert "Nunca alucine fluxo de uso" in prompt


def test_system_prompt_accepts_dynamic_knowledge_modules():
    prompt = build_chatbot_ajuda_system_prompt(
        [
            ChatbotAjudaPromptModule(
                topic="pix",
                title="Pagamento via Pix",
                status="em_desenvolvimento",
                content="Pagamento via Pix ainda esta em teste interno.",
            )
        ]
    )

    assert "[em_desenvolvimento] Pagamento via Pix" in prompt
    assert "teste interno" in prompt
