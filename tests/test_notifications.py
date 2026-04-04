import uuid

from app.models.notification import Notification


def test_listar_notificacoes_usuario(client, db):
    user_id = uuid.uuid4()
    db.add(Notification(usuario_id=user_id, titulo="Nota 1", mensagem="Corpo 1"))
    db.commit()

    response = client.get(f"/notifications/?usuario_id={user_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Nota 1"


def test_listar_notificacoes_usuario_sem_notificacoes(client, db):
    user_id = uuid.uuid4()

    response = client.get(f"/notifications/?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json() == []


def test_contar_notificacoes_nao_lidas(client, db):
    user_id = uuid.uuid4()
    db.add(Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False))
    db.add(Notification(usuario_id=user_id, titulo="N2", mensagem="C2", lida=True))
    db.commit()

    response = client.get(f"/notifications/count?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json()["unread_count"] == 1


def test_contar_notificacoes_nao_lidas_zerado(client, db):
    user_id = uuid.uuid4()

    response = client.get(f"/notifications/count?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json()["unread_count"] == 0


def test_marcar_como_lida(client, db):
    user_id = uuid.uuid4()
    notif = Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False)
    db.add(notif)
    db.commit()
    db.refresh(notif)

    response = client.patch(f"/notifications/{notif.id}/read?usuario_id={user_id}")

    assert response.status_code == 200
    db.refresh(notif)
    assert notif.lida is True


def test_marcar_como_lida_notificacao_inexistente(client, db):
    user_id = uuid.uuid4()
    fake_id = uuid.uuid4()

    response = client.patch(f"/notifications/{fake_id}/read?usuario_id={user_id}")

    assert response.status_code == 404


def test_marcar_como_lida_notificacao_de_outro_usuario(client, db):
    user_id = uuid.uuid4()
    outro_user_id = uuid.uuid4()
    notif = Notification(usuario_id=outro_user_id, titulo="N1", mensagem="C1", lida=False)
    db.add(notif)
    db.commit()
    db.refresh(notif)

    response = client.patch(f"/notifications/{notif.id}/read?usuario_id={user_id}")

    assert response.status_code == 404


def test_marcar_todas_como_lidas(client, db):
    user_id = uuid.uuid4()
    db.add(Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False))
    db.add(Notification(usuario_id=user_id, titulo="N2", mensagem="C2", lida=False))
    db.commit()

    response = client.patch(f"/notifications/read-all?usuario_id={user_id}")

    assert response.status_code == 200
    assert "2 notificacoes marcadas como lidas" in response.json()["message"]


def test_marcar_todas_como_lidas_sem_notificacoes(client, db):
    user_id = uuid.uuid4()

    response = client.patch(f"/notifications/read-all?usuario_id={user_id}")

    assert response.status_code == 200
    assert "0 notificacoes marcadas como lidas" in response.json()["message"]
