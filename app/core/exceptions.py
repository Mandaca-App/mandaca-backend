"""Exceções de domínio da aplicação Mandacá.

Services levantam estas exceções. O FastAPI converte para HTTPException
via handlers registrados em app/main.py — nunca importe fastapi nos services.
"""

from uuid import UUID


class MandacaError(Exception):
    """Classe base para todas as exceções de domínio."""


class EnterpriseNotFoundError(MandacaError):
    def __init__(self, enterprise_id: UUID | str) -> None:
        super().__init__(f"Empresa não encontrada: {enterprise_id}")
        self.enterprise_id = enterprise_id


class DuplicateEnterpriseNameError(MandacaError):
    def __init__(self, nome: str) -> None:
        super().__init__(f"Já existe uma empresa com esse nome: {nome}")
        self.nome = nome


class UserNotFoundError(MandacaError):
    def __init__(self, usuario_id: UUID | str) -> None:
        super().__init__(f"Usuário vinculado não encontrado: {usuario_id}")
        self.usuario_id = usuario_id


class UserAlreadyHasEnterpriseError(MandacaError):
    def __init__(self, usuario_id: UUID | str) -> None:
        super().__init__(f"Este usuário já possui uma empresa vinculada: {usuario_id}")
        self.usuario_id = usuario_id


class UserAlreadyLinkedError(MandacaError):
    def __init__(self, usuario_id: UUID | str) -> None:
        super().__init__(f"Este usuário já está vinculado a outra empresa: {usuario_id}")
        self.usuario_id = usuario_id


class AddressNotFoundError(MandacaError):
    def __init__(self, endereco: str) -> None:
        super().__init__(f"Endereço não encontrado ou não geocodificável: {endereco}")
        self.endereco = endereco


class GeocodingUnavailableError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Serviço de geolocalização temporariamente indisponível.")


# ---------------------------------------------------------------------------
# Exceções de áudio / transcrição (transcription_service)
# ---------------------------------------------------------------------------


class UnsupportedAudioFormatError(MandacaError):
    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"Formato de áudio não suportado: {content_type}. Use mp3, wav, webm, ogg ou m4a."
        )
        self.content_type = content_type


class AudioTooLargeError(MandacaError):
    def __init__(self) -> None:
        super().__init__("O arquivo de áudio excede o limite de 25 MB.")


class AudioRateLimitError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Limite de requisições da API de transcrição atingido. Tente novamente.")


class AudioServiceConnectionError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Não foi possível conectar à API de transcrição. Tente novamente.")


class AudioServiceTimeoutError(MandacaError):
    def __init__(self) -> None:
        super().__init__("A API de transcrição demorou demais para responder. Tente novamente.")


class AudioTranscriptionError(MandacaError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Falha na transcrição do áudio: {detail}")


# ---------------------------------------------------------------------------
# Exceções de chat (chat_service)
# ---------------------------------------------------------------------------


class ChatRateLimitError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Limite de requisições da API de chat atingido. Tente novamente.")


class ChatServiceTimeoutError(MandacaError):
    def __init__(self) -> None:
        super().__init__("A API de chat demorou demais para responder. Tente novamente.")


class ChatServiceConnectionError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Não foi possível conectar à API de chat. Tente novamente.")


class ChatServiceError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Erro inesperado na API de chat. Tente novamente.")


class ChatbotNotFoundError(MandacaError):
    def __init__(self, chatbot_id: UUID | str) -> None:
        super().__init__(f"Chatbot nao encontrado: {chatbot_id}")
        self.chatbot_id = chatbot_id


class DuplicateChatbotTypeError(MandacaError):
    def __init__(self, tipo: str) -> None:
        super().__init__(f"Ja existe um chatbot cadastrado para o tipo: {tipo}")
        self.tipo = tipo


# ---------------------------------------------------------------------------
# Exceções de Menu (menu_service)
# ---------------------------------------------------------------------------


class MenuNotFoundError(MandacaError):
    def __init__(self, menu_id: UUID | str) -> None:
        super().__init__(f"Cardápio não encontrado: {menu_id}")
        self.menu_id = menu_id


class InvalidImageTypeError(MandacaError):
    def __init__(self) -> None:
        super().__init__("O arquivo enviado não é uma imagem válida.")


class MenuPageEmptyError(MandacaError):
    def __init__(self, page: int) -> None:
        super().__init__(f"Não há mais itens de cardápio na página {page}.")
        self.page = page


# ---------------------------------------------------------------------------
# Exceções de Avaliações (assessment_service)
# ---------------------------------------------------------------------------


class AssessmentNotFoundError(MandacaError):
    def __init__(self, assessment_id: UUID | str) -> None:
        super().__init__(f"Avaliação não encontrada: {assessment_id}")
        self.assessment_id = assessment_id


class AssessmentClassificationError(MandacaError):
    def __init__(
        self, detail: str = "Não foi possível classificar a avaliação no momento."
    ) -> None:
        super().__init__(detail)
        self.detail = detail


class AssessmentPageEmptyError(MandacaError):
    def __init__(self, page: int) -> None:
        super().__init__(f"Não há mais avaliações na página {page}.")
        self.page = page


# ---------------------------------------------------------------------------
# Exceções de Contexto de Negócio (business_context_service)
# ---------------------------------------------------------------------------


class BusinessContextNotFoundError(MandacaError):
    def __init__(self, context_id: UUID | str) -> None:
        super().__init__(f"Contexto de negócio não encontrado: {context_id}")
        self.context_id = context_id


class InvalidContextDataError(MandacaError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"dados_contexto inválido: {detail}")
        self.detail = detail


# ---------------------------------------------------------------------------
# Exceções de Relatório IA (report_service)
# ---------------------------------------------------------------------------


class AIReportNotFoundError(MandacaError):
    def __init__(self, report_id: UUID | str) -> None:
        super().__init__(f"Relatório IA não encontrado: {report_id}")
        self.report_id = report_id


class AIReportGenerationError(MandacaError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Falha ao gerar relatório IA: {detail}")
        self.detail = detail


# ---------------------------------------------------------------------------
# Exceções de Auto Apply (auto_apply_service)
# ---------------------------------------------------------------------------


class FieldNotAllowedError(MandacaError):
    def __init__(self, campo: str) -> None:
        super().__init__(f"Campo não permitido para alteração automática: {campo}")
        self.campo = campo


class InvalidFieldValueError(MandacaError):
    def __init__(self, campo: str, detail: str) -> None:
        super().__init__(f"Valor inválido para o campo {campo}: {detail}")
        self.campo = campo
        self.detail = detail


class AutoApplyPersistenceError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Falha ao aplicar alteração no banco de dados.")


# ---------------------------------------------------------------------------
# Exceções de Contato (contact_service)
# ---------------------------------------------------------------------------


class ContactNotFoundError(MandacaError):
    def __init__(self, contact_id: UUID | str) -> None:
        super().__init__(f"Contato não encontrado: {contact_id}")
        self.contact_id = contact_id


# ---------------------------------------------------------------------------
# Exceções de Extração de Cardápio via IA (menu_extraction_service)
# ---------------------------------------------------------------------------


class MenuExtractionError(MandacaError):
    def __init__(
        self, detail: str = "Falha ao processar o cardápio via IA. Tente novamente."
    ) -> None:
        super().__init__(detail)
        self.detail = detail


class MenuContentUnreadableError(MandacaError):
    def __init__(self) -> None:
        super().__init__("O conteúdo enviado não pôde ser interpretado como um cardápio.")
