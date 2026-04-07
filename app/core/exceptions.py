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
