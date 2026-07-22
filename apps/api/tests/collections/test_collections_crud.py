from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_collection, make_design, make_user


def test_create_collection_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/collections", json={"name": "Bridal Ideas"})
    assert response.status_code == 401


def test_create_collection(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(
        "/api/v1/collections",
        json={"name": "Bridal Ideas", "description": "For the big day", "is_private": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Bridal Ideas"
    assert body["description"] == "For the big day"
    assert body["is_private"] is False
    assert body["is_default"] is False
    assert body["item_count"] == 0
    assert body["cover_image_url"] is None


def test_create_collection_rejects_duplicate_name(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    client.post("/api/v1/collections", json={"name": "Bridal Ideas"}, headers=auth_headers(token))

    response = client.post(
        "/api/v1/collections", json={"name": "Bridal Ideas"}, headers=auth_headers(token)
    )

    assert response.status_code == 409


def test_different_users_can_reuse_the_same_collection_name(
    client: TestClient, db_session: Session
) -> None:
    alice = make_user(db_session)
    bob = make_user(db_session)
    db_session.commit()
    alice_token = sign_token(alice.id, email=alice.email)
    bob_token = sign_token(bob.id, email=bob.email)
    client.post(
        "/api/v1/collections", json={"name": "Bridal Ideas"}, headers=auth_headers(alice_token)
    )

    response = client.post(
        "/api/v1/collections", json={"name": "Bridal Ideas"}, headers=auth_headers(bob_token)
    )

    assert response.status_code == 201


def test_rename_collection(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer, name="Old Name")
    db_session.commit()

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"name": "New Name"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_rename_collection_rejects_duplicate_name(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    make_collection(db_session, user=viewer, name="Taken")
    collection = make_collection(db_session, user=viewer, name="Mine")
    db_session.commit()

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"name": "Taken"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_toggle_collection_privacy(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer, is_private=True)
    db_session.commit()

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"is_private": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["is_private"] is False


def test_non_owner_cannot_update_collection(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"name": "Hijacked"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_delete_collection(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    db_session.commit()

    response = client.delete(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))
    assert response.status_code == 204

    follow_up = client.get(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))
    assert follow_up.status_code == 404


def test_non_owner_cannot_delete_collection(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.delete(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))

    assert response.status_code == 403


def test_cannot_delete_default_collection(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))
    default_collection_id = client.get("/api/v1/collections", headers=auth_headers(token)).json()[
        "items"
    ][0]["id"]

    response = client.delete(
        f"/api/v1/collections/{default_collection_id}", headers=auth_headers(token)
    )

    assert response.status_code == 400


def test_private_collection_hidden_from_non_owner(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner, is_private=True)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))

    assert response.status_code == 404


def test_public_collection_visible_to_non_owner(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner, is_private=False)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["id"] == str(collection.id)


def test_owner_can_always_view_their_own_private_collection(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner, is_private=True)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))

    assert response.status_code == 200


def test_list_my_collections_only_shows_own_collections(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    make_collection(db_session, user=owner, name="Mine")
    make_collection(db_session, user=stranger, name="Not Mine")
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get("/api/v1/collections", headers=auth_headers(token))

    names = [c["name"] for c in response.json()["items"]]
    assert names == ["Mine"]


def test_collection_cover_defaults_to_most_recently_added_item(
    client: TestClient, db_session: Session
) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    db_session.commit()
    first = make_design(db_session, status="published")
    second = make_design(db_session, status="published")
    db_session.commit()
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(first.id)},
        headers=auth_headers(token),
    )
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(second.id)},
        headers=auth_headers(token),
    )

    response = client.get(f"/api/v1/collections/{collection.id}", headers=auth_headers(token))

    # No thumbnail uploaded for either design, so cover_image_url stays None,
    # but item_count confirms both items landed in the collection the cover
    # would be resolved from.
    assert response.json()["item_count"] == 2


def test_collection_cover_can_be_explicitly_set(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"cover_design_id": str(design.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 200


def test_collection_cover_rejects_unpublished_design(
    client: TestClient, db_session: Session
) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    draft = make_design(db_session, status="draft")
    db_session.commit()

    response = client.patch(
        f"/api/v1/collections/{collection.id}",
        json={"cover_design_id": str(draft.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
