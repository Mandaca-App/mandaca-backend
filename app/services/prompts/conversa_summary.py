from app.models.chat_message import ChatMessage


def build_summary_prompt(notas_atuais: str | None, mensagens: list[ChatMessage]) -> str:
    historico_anterior = _build_previous_summary(notas_atuais)
    conversa = _build_conversation_block(mensagens)

    return f"""
Voce e um assistente que resume conversas entre um microempreendedor de turismo
e gastronomia do interior de Pernambuco e o Consultor Mandaca.

Sua tarefa e produzir um resumo unico e consolidado da conversa, em portugues
brasileiro, que sirva de memoria de longo prazo para as proximas conversas.

Diretrizes:
- Preserve fatos concretos sobre o negocio (nome, cardapio, horarios, metas).
- Preserve preferencias, duvidas recorrentes e decisoes ja tomadas pelo empreendedor.
- Seja objetivo: use frases curtas e topicos quando ajudar.
- Nao invente informacoes que nao apareceram na conversa.
- Retorne apenas o texto do resumo, sem preambulo nem comentarios.
{historico_anterior}
Mensagens recentes a incorporar no resumo:
{conversa}
""".strip()


def _build_previous_summary(notas_atuais: str | None) -> str:
    if not notas_atuais:
        return ""
    return (
        "\nResumo anterior da conversa (atualize-o de forma incremental, "
        f"sem perder o que ja foi registrado):\n{notas_atuais}\n"
    )


def _build_conversation_block(mensagens: list[ChatMessage]) -> str:
    linhas: list[str] = []
    for mensagem in mensagens:
        linhas.append(f"Empreendedor: {mensagem.conteudo_usuario}")
        linhas.append(f"Consultor: {mensagem.conteudo_assistente}")
    return "\n".join(linhas)
