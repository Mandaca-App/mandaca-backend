import uuid

from app.models.notification import Notification
from app.models.user import TipoUsuario, User


def _create_user(db, user_id: uuid.UUID) -> User:
    user = User(
        id_usuario=user_id,
        tipo_usuario=TipoUsuario.TURISTA,
        nome="Test User",
        cpf=str(user_id).replace("-", "")[:11],
    )
    db.add(user)
    db.commit()
    return user


def test_given_user_with_notifications_when_list_then_returns_all(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)
    db.add(Notification(usuario_id=user_id, titulo="Nota 1", mensagem="Corpo 1"))
    db.commit()

    response = client.get(f"/notifications/?usuario_id={user_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Nota 1"


def test_given_user_without_notifications_when_list_then_returns_empty(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)

    response = client.get(f"/notifications/?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json() == []


def test_given_user_with_mixed_read_status_when_count_unread_then_returns_correct(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)
    db.add(Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False))
    db.add(Notification(usuario_id=user_id, titulo="N2", mensagem="C2", lida=True))
    db.commit()

    response = client.get(f"/notifications/count?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json()["unread_count"] == 1


def test_given_user_without_notifications_when_count_unread_then_returns_zero(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)

    response = client.get(f"/notifications/count?usuario_id={user_id}")

    assert response.status_code == 200
    assert response.json()["unread_count"] == 0


def test_given_unread_notification_when_mark_read_then_status_changes(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)
    notif = Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False)
    db.add(notif)
    db.commit()
    db.refresh(notif)

    response = client.patch(f"/notifications/{notif.id}/read?usuario_id={user_id}")

    assert response.status_code == 200
    db.refresh(notif)
    assert notif.lida is True


def test_given_nonexistent_notification_when_mark_read_then_returns_404(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)
    fake_id = uuid.uuid4()

    response = client.patch(f"/notifications/{fake_id}/read?usuario_id={user_id}")

    assert response.status_code == 404


def test_given_other_user_notification_when_mark_read_then_returns_404(client, db):
    user_id = uuid.uuid4()
    outro_user_id = uuid.uuid4()
    _create_user(db, user_id)
    _create_user(db, outro_user_id)
    notif = Notification(usuario_id=outro_user_id, titulo="N1", mensagem="C1", lida=False)
    db.add(notif)
    db.commit()
    db.refresh(notif)

    response = client.patch(f"/notifications/{notif.id}/read?usuario_id={user_id}")

    assert response.status_code == 404


def test_given_multiple_unread_when_mark_all_read_then_all_updated(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)
    db.add(Notification(usuario_id=user_id, titulo="N1", mensagem="C1", lida=False))
    db.add(Notification(usuario_id=user_id, titulo="N2", mensagem="C2", lida=False))
    db.commit()

    response = client.patch(f"/notifications/read-all?usuario_id={user_id}")

    assert response.status_code == 200
    assert "2 notificações marcadas como lidas" in response.json()["message"]


def test_given_no_unread_when_mark_all_read_then_returns_zero(client, db):
    user_id = uuid.uuid4()
    _create_user(db, user_id)

    response = client.patch(f"/notifications/read-all?usuario_id={user_id}")

    assert response.status_code == 200
    assert "0 notificações marcadas como lidas" in response.json()["message"]


def test_given_health_endpoint_when_get_then_returns_ok(client, db):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_given_users_endpoint_when_list_then_returns_success(client, db):
    response = client.get("/users/")
    assert response.status_code == 200
