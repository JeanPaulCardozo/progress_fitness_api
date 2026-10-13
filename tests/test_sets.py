from datetime import date, timedelta

import pytest

from progress_fitness_api.models.sets import Set


def a_set(**changes):
    return {
        "date": date.today().isoformat(),
        "day": 1,
        "exercise": "Sentadilla",
        "reps": 8,
        "weight": 60,
        "feel": "Moderado",
        **changes,
    }


def test_sets_require_login(client):
    assert client.get("/sets/").status_code == 401
    assert client.post("/sets/", json=a_set()).status_code == 401


def test_create_and_list_sets(client, db, auth):
    res = client.post("/sets/", json=a_set(notes="buena técnica"), headers=auth)
    assert res.status_code == 201
    body = res.json()
    assert body["date"] == date.today().isoformat()
    assert body["exercise"] == "Sentadilla"
    assert body["weight"] == 60
    assert body["notes"] == "buena técnica"
    assert (
        db.get(Set, body["id"]).volume == 480
    )  # 60 kg × 8 reps, lo calcula el servidor

    listed = client.get("/sets/", headers=auth).json()
    assert [s["id"] for s in listed] == [body["id"]]


@pytest.mark.parametrize("feel", ["Fácil", "Moderado", "Difícil", "Al Fallo"])
def test_all_feel_values_are_accepted(client, auth, feel):
    assert client.post("/sets/", json=a_set(feel=feel), headers=auth).status_code == 201


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"day": 0}, "day"),
        ({"day": 8}, "day"),
        ({"feel": "Al fallo"}, "feel"),
        ({"date": (date.today() + timedelta(days=3)).isoformat()}, "date"),
        ({"date": "09/10/2026"}, "date"),
    ],
)
def test_invalid_sets_are_rejected(client, auth, changes, field):
    res = client.post("/sets/", json=a_set(**changes), headers=auth)
    assert res.status_code == 422
    assert res.json()["message"].startswith(f"{field}:")


def test_users_only_see_their_own_sets(client, auth, other_auth):
    client.post("/sets/", json=a_set(), headers=auth)
    assert client.get("/sets/", headers=other_auth).json() == []


def test_delete_own_set(client, auth):
    set_id = client.post("/sets/", json=a_set(), headers=auth).json()["id"]
    assert client.delete(f"/sets/{set_id}", headers=auth).status_code == 204
    assert client.get("/sets/", headers=auth).json() == []


def test_cannot_delete_another_users_set(client, auth, other_auth):
    set_id = client.post("/sets/", json=a_set(), headers=auth).json()["id"]
    res = client.delete(f"/sets/{set_id}", headers=other_auth)
    assert res.status_code == 403
    assert len(client.get("/sets/", headers=auth).json()) == 1


def test_delete_missing_set(client, auth):
    res = client.delete("/sets/999", headers=auth)
    assert res.status_code == 404
    assert res.json() == {"message": "Set Not Found"}
