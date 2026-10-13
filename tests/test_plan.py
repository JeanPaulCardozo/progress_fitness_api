from progress_fitness_api.models.plan import Plan

PLAN = "# Día 1: Pierna\n- Sentadilla: 4 x 6–8, descanso 2 min"


def test_plan_requires_login(client):
    assert client.get("/plan/").status_code == 401


def test_new_user_has_no_plan(client, auth):
    res = client.get("/plan/", headers=auth)
    assert res.status_code == 404
    assert res.json() == {"message": "Plan Not Found"}


def test_put_creates_then_replaces_the_plan(client, db, auth):
    first = client.put("/plan/", json={"text": PLAN}, headers=auth)
    assert first.status_code == 200
    assert first.json()["text"] == PLAN

    second = client.put(
        "/plan/", json={"text": "# Día 1: Torso\n- Press: 3 x 8"}, headers=auth
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]  # upsert: misma fila
    assert db.query(Plan).count() == 1

    assert (
        client.get("/plan/", headers=auth).json()["text"]
        == "# Día 1: Torso\n- Press: 3 x 8"
    )


def test_plans_are_private(client, auth, other_auth):
    client.put("/plan/", json={"text": PLAN}, headers=auth)
    assert client.get("/plan/", headers=other_auth).status_code == 404


def test_plan_text_too_short(client, auth):
    assert client.put("/plan/", json={"text": "hi"}, headers=auth).status_code == 422
