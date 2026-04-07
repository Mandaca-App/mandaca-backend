"""Exceções de domínio da aplicação Mandacá.

Services levantam estas exceções. O FastAPI converte para HTTPException
via handlers registrados em app/main.py — nunca importe fastapi nos services.
"""


class MandacaError(Exception):
    """Classe base para todas as exceções de domínio."""


class EnterpriseNotFoundError(MandacaError):
    def __init__(self, enterprise_id: str) -> None:
        super().__init__(f"Empresa não encontrada: {enterprise_id}")
        self.enterprise_id = enterprise_id


class DuplicateEnterpriseNameError(MandacaError):
    def __init__(self, nome: str) -> None:
        super().__init__(f"Já existe uma empresa com esse nome: {nome}")
        self.nome = nome


class UserNotFoundError(MandacaError):
    def __init__(self, usuario_id: str) -> None:
        super().__init__(f"Usuário vinculado não encontrado: {usuario_id}")
        self.usuario_id = usuario_id


class UserAlreadyHasEnterpriseError(MandacaError):
    def __init__(self, usuario_id: str) -> None:
        super().__init__(f"Este usuário já possui uma empresa vinculada: {usuario_id}")
        self.usuario_id = usuario_id


class UserAlreadyLinkedError(MandacaError):
    def __init__(self, usuario_id: str) -> None:
        super().__init__(f"Este usuário já está vinculado a outra empresa: {usuario_id}")
        self.usuario_id = usuario_id


class AddressNotFoundError(MandacaError):
    def __init__(self, endereco: str) -> None:
        super().__init__(f"Endereço não encontrado ou não geocodificável: {endereco}")
        self.endereco = endereco


class GeocodingUnavailableError(MandacaError):
    def __init__(self) -> None:
        super().__init__("Serviço de geolocalização temporariamente indisponível.")
