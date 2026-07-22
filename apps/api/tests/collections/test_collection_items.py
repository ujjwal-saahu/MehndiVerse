from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_collection, make_design, make_user


def test_add_item_to_collection(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(design.id)]


def test_add_item_prevents_duplicates(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    db_session.commit()
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    response = client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(design.id)]


def test_add_item_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner)
    design = make_design(db_session, status="published")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_add_unpublished_design_returns_404(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    draft = make_design(db_session, status="draft")
    db_session.commit()

    response = client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(draft.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_remove_item_from_collection(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    db_session.commit()
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    response = client.delete(
        f"/api/v1/collections/{collection.id}/items/{design.id}", headers=auth_headers(token)
    )
    assert response.status_code == 204

    follow_up = client.get(
        f"/api/v1/collections/{collection.id}/items", headers=auth_headers(token)
    )
    assert follow_up.json()["items"] == []


def test_remove_item_is_idempotent(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.delete(
        f"/api/v1/collections/{collection.id}/items/{design.id}", headers=auth_headers(token)
    )

    assert response.status_code == 204


def test_remove_item_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner)
    design = make_design(db_session, status="published")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.delete(
        f"/api/v1/collections/{collection.id}/items/{design.id}", headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_non_owner_cannot_list_items_of_private_collection(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner, is_private=True)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/collections/{collection.id}/items", headers=auth_headers(token))

    assert response.status_code == 404


def test_non_owner_can_list_items_of_public_collection(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner, is_private=False)
    design = make_design(db_session, status="published")
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    stranger_token = sign_token(stranger.id, email=stranger.email)
    response = client.get(
        f"/api/v1/collections/{collection.id}/items", headers=auth_headers(stranger_token)
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(design.id)]


def test_items_pagination_walks_full_list_without_duplicates(
    client: TestClient, db_session: Session
) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    designs = [make_design(db_session, status="published") for _ in range(5)]
    db_session.commit()
    for design in designs:
        client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={"design_id": str(design.id)},
            headers=auth_headers(token),
        )

    seen_ids: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params: dict[str, object] = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get(
            f"/api/v1/collections/{collection.id}/items",
            params=params,
            headers=auth_headers(token),
        )
        assert response.status_code == 200
        body = response.json()
        seen_ids.extend(item["id"] for item in body["items"])
        if not body["page_info"]["has_more"]:
            assert body["page_info"]["next_cursor"] is None
            break
        cursor = body["page_info"]["next_cursor"]
        assert cursor is not None
    else:
        raise AssertionError("Pagination did not terminate within the safety cap.")

    assert sorted(seen_ids) == sorted(str(d.id) for d in designs)
    assert len(seen_ids) == len(set(seen_ids))


def test_reorder_items(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
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

    response = client.put(
        f"/api/v1/collections/{collection.id}/items/reorder",
        json={"design_ids": [str(second.id), str(first.id)]},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(second.id), str(first.id)]


def test_reorder_rejects_partial_list(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
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

    response = client.put(
        f"/api/v1/collections/{collection.id}/items/reorder",
        json={"design_ids": [str(first.id)]},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_reorder_rejects_unknown_design_id(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    collection = make_collection(db_session, user=viewer)
    design = make_design(db_session, status="published")
    other = make_design(db_session, status="published")
    db_session.commit()
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(token),
    )

    response = client.put(
        f"/api/v1/collections/{collection.id}/items/reorder",
        json={"design_ids": [str(other.id)]},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_reorder_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    collection = make_collection(db_session, user=owner)
    design = make_design(db_session, status="published")
    db_session.commit()
    owner_token = sign_token(owner.id, email=owner.email)
    client.post(
        f"/api/v1/collections/{collection.id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(owner_token),
    )

    stranger_token = sign_token(stranger.id, email=stranger.email)
    response = client.put(
        f"/api/v1/collections/{collection.id}/items/reorder",
        json={"design_ids": [str(design.id)]},
        headers=auth_headers(stranger_token),
    )

    assert response.status_code == 403


def test_adding_to_default_collection_increments_save_count(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))
    default_collection_id = client.get("/api/v1/collections", headers=auth_headers(token)).json()[
        "items"
    ][0]["id"]

    other_design = make_design(db_session, status="published")
    db_session.commit()
    client.post(
        f"/api/v1/collections/{default_collection_id}/items",
        json={"design_id": str(other_design.id)},
        headers=auth_headers(token),
    )

    detail = client.get(f"/api/v1/designs/{other_design.id}", headers=auth_headers(token))
    assert detail.json()["save_count"] == 1
