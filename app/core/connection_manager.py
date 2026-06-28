"""Gerencia conexões WebSocket ativas agrupadas por sala (reserva).

Mantém o estado das conexões em memória e faz broadcast para todos os
clientes de uma reserva. Instanciado como singleton no router.
"""

from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[UUID, list[WebSocket]] = {}

    async def connect(self, reserva_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms.setdefault(reserva_id, []).append(websocket)

    def disconnect(self, reserva_id: UUID, websocket: WebSocket) -> None:
        room = self._rooms.get(reserva_id)
        if room is None:
            return
        if websocket in room:
            room.remove(websocket)
        if not room:
            del self._rooms[reserva_id]

    async def broadcast(self, reserva_id: UUID, payload: dict) -> None:
        """Envia o payload a todos os clientes da sala, ignorando os que falharem."""
        for websocket in list(self._rooms.get(reserva_id, [])):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(reserva_id, websocket)
