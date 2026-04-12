import logging

import groq as groq_sdk
from groq import AsyncGroq

from app.core.config import settings
from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)

logger = logging.getLogger(__name__)

_CHAT_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 1024
_TEMPERATURE = 0.7

_SYSTEM_PROMPT = """
Você é Mandaca, uma consultora de negócios especializada em apoiar
microempreendedores do interior de Pernambuco. Conhece profundamente a
cultura, os desafios e oportunidades do sertão e agreste nordestino.
Responda de forma clara, acolhedora e prática, usando linguagem acessível.
Foque em orientações sobre gestão, vendas, finanças pessoais e formalização
de pequenos negócios.
"""


class ChatService:
    async def send_message(self, message: str) -> str:
        client = AsyncGroq(api_key=settings.groq_api_key)
        try:
            response = await client.chat.completions.create(
                model=_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
            )
            content = response.choices[0].message.content
            return content or ""
        except groq_sdk.RateLimitError:
            raise ChatRateLimitError()
        except groq_sdk.APITimeoutError:
            raise ChatServiceTimeoutError()
        except groq_sdk.APIConnectionError:
            raise ChatServiceConnectionError()
        except groq_sdk.APIStatusError:
            raise ChatServiceError()
