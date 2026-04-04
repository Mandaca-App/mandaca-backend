from uuid import UUID

from pydantic import BaseModel

from app.models.audio_transcription import AudioTranscription


class ExtractedFieldsResponse(BaseModel):
    nome: str | None = None
    especialidade: str | None = None
    endereco: str | None = None
    historia: str | None = None
    telefone: str | None = None


class AudioTranscriptionResponse(BaseModel):
    id_transcricao: UUID
    usuario_id: UUID
    url_audio: str | None = None
    texto_bruto: str | None = None
    campos_extraidos: ExtractedFieldsResponse
    sucesso: bool

    @classmethod
    def from_record(cls, record: AudioTranscription) -> "AudioTranscriptionResponse":
        return cls(
            id_transcricao=record.id_transcricao,
            usuario_id=record.usuario_id,
            url_audio=record.url_audio,
            texto_bruto=record.texto_bruto,
            campos_extraidos=ExtractedFieldsResponse(
                nome=record.nome_extraido,
                especialidade=record.especialidade_extraida,
                endereco=record.endereco_extraido,
                historia=record.historia_extraida,
                telefone=record.telefone_extraido,
            ),
            sucesso=bool(
                record.nome_extraido or record.especialidade_extraida or record.endereco_extraido
            ),
        )
