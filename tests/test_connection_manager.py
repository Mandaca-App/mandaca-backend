"""Testes BDD para ConnectionManager.

Broadcast por sala de reserva, tolerante a clientes desconectados.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.connection_manager import ConnectionManager

RESERVA_ID = uuid.uuid4()


def _ws() -> AsyncMock:
    ws = AsyncMock()
    return ws


@pytest.mark.anyio
async def test_given_two_clients_when_broadcast_then_both_receive():
    # GIVEN
    manager = ConnectionManager()
    first, second = _ws(), _ws()
    await manager.connect(RESERVA_ID, first)
    await manager.connect(RESERVA_ID, second)

    # WHEN
    await manager.broadcast(RESERVA_ID, {"conteudo": "oi"})

    # THEN
    first.send_json.assert_awaited_once_with({"conteudo": "oi"})
    second.send_json.assert_awaited_once_with({"conteudo": "oi"})


@pytest.mark.anyio
async def test_given_dead_client_when_broadcast_then_others_still_receive():
    # GIVEN
    manager = ConnectionManager()
    dead, alive = _ws(), _ws()
    dead.send_json.side_effect = RuntimeError("connection closed")
    await manager.connect(RESERVA_ID, dead)
    await manager.connect(RESERVA_ID, alive)

    # WHEN
    await manager.broadcast(RESERVA_ID, {"conteudo": "oi"})

    # THEN
    alive.send_json.assert_awaited_once()


@pytest.mark.anyio
async def test_given_connected_client_when_disconnect_then_room_cleared():
    # GIVEN
    manager = ConnectionManager()
    ws = _ws()
    await manager.connect(RESERVA_ID, ws)

    # WHEN
    manager.disconnect(RESERVA_ID, ws)
    await manager.broadcast(RESERVA_ID, {"conteudo": "oi"})

    # THEN
    ws.send_json.assert_not_awaited()
