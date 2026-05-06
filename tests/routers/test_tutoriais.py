from app.models.tutorial import CategoriaTutorial, Tutorial

ADMIN_HEADERS = {"X-User-Type": "admin"}


def _payload(**overrides):
    data = {
        "categoria": "geral",
        "titulo": "Como usar a Central de Ajuda",
        "descricao": "Tutorial introdutorio",
        "url": "https://notion.so/tutorial",
        "ordem": 0,
        "ativo": True,
    }
    data.update(overrides)
    return data


def _create_tutorial(db, **overrides):
    tutorial = Tutorial(
        categoria=overrides.get("categoria", CategoriaTutorial.GERAL),
        titulo=overrides.get("titulo", "Tutorial"),
        descricao=overrides.get("descricao"),
        url=overrides.get("url", "https://youtube.com/watch?v=abc123"),
        ordem=overrides.get("ordem", 0),
        ativo=overrides.get("ativo", True),
    )
    db.add(tutorial)
    db.commit()
    db.refresh(tutorial)
    return tutorial


def test_given_active_tutorials_when_list_then_returns_ordered_and_ignores_inactive(client, db):
    _create_tutorial(db, categoria=CategoriaTutorial.RESERVA, titulo="Reserva 2", ordem=2)
    _create_tutorial(db, categoria=CategoriaTutorial.CARDAPIO, titulo="Cardapio 2", ordem=2)
    _create_tutorial(db, categoria=CategoriaTutorial.GERAL, titulo="Geral 1", ordem=1)
    _create_tutorial(db, categoria=CategoriaTutorial.CARDAPIO, titulo="Cardapio 1", ordem=1)
    _create_tutorial(db, categoria=CategoriaTutorial.RELATORIOS, titulo="Relatorios 1", ordem=1)
    _create_tutorial(
        db,
        categoria=CategoriaTutorial.CARDAPIO,
        titulo="Inativo",
        ordem=0,
        ativo=False,
    )

    response = client.get("/api/tutoriais")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert [item["titulo"] for item in data] == [
        "Cardapio 1",
        "Cardapio 2",
        "Geral 1",
        "Relatorios 1",
        "Reserva 2",
    ]


def test_given_category_filter_when_list_then_returns_only_category(client, db):
    for index in range(3):
        _create_tutorial(
            db,
            categoria=CategoriaTutorial.CARDAPIO,
            titulo=f"Cardapio {index}",
            ordem=index,
        )
    for index in range(2):
        _create_tutorial(
            db,
            categoria=CategoriaTutorial.RESERVA,
            titulo=f"Reserva {index}",
            ordem=index,
        )

    response = client.get("/api/tutoriais?categoria=cardapio")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert {item["categoria"] for item in data} == {"cardapio"}


def test_given_invalid_category_filter_when_list_then_returns_422(client):
    response = client.get("/api/tutoriais?categoria=inexistente")

    assert response.status_code == 422
    detail = str(response.json()["detail"])
    assert "cardapio" in detail
    assert "reserva" in detail
    assert "relatorios" in detail
    assert "geral" in detail


def test_given_valid_payload_when_admin_creates_then_returns_201(client, db):
    response = client.post(
        "/api/tutoriais",
        headers=ADMIN_HEADERS,
        json=_payload(categoria="cardapio", titulo="Cadastrar item", ordem=3),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["categoria"] == "cardapio"
    assert data["titulo"] == "Cadastrar item"
    assert data["ordem"] == 3
    assert db.query(Tutorial).count() == 1


def test_given_invalid_url_when_admin_creates_then_returns_422_and_does_not_persist(client, db):
    response = client.post(
        "/api/tutoriais",
        headers=ADMIN_HEADERS,
        json=_payload(url="not-a-url"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "URL inválida"
    assert db.query(Tutorial).count() == 0


def test_given_non_admin_when_create_then_returns_403(client, db):
    response = client.post(
        "/api/tutoriais",
        headers={"X-User-Type": "empreendedor"},
        json=_payload(),
    )

    assert response.status_code == 403
    assert db.query(Tutorial).count() == 0


def test_given_existing_tutorial_when_admin_updates_order_then_list_reflects_new_order(client, db):
    first = _create_tutorial(db, categoria=CategoriaTutorial.CARDAPIO, titulo="Primeiro", ordem=0)
    _create_tutorial(db, categoria=CategoriaTutorial.CARDAPIO, titulo="Segundo", ordem=1)

    update_response = client.put(
        f"/api/tutoriais/{first.id}",
        headers=ADMIN_HEADERS,
        json={"ordem": 5},
    )

    assert update_response.status_code == 200
    assert update_response.json()["ordem"] == 5

    list_response = client.get("/api/tutoriais?categoria=cardapio")

    assert list_response.status_code == 200
    assert [item["titulo"] for item in list_response.json()] == ["Segundo", "Primeiro"]


def test_given_existing_tutorial_when_admin_deletes_then_hard_deletes(client, db):
    tutorial = _create_tutorial(db, categoria=CategoriaTutorial.GERAL, titulo="Remover")

    response = client.delete(f"/api/tutoriais/{tutorial.id}", headers=ADMIN_HEADERS)

    assert response.status_code == 204
    assert db.get(Tutorial, tutorial.id) is None
