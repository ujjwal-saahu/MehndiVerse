from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.engagement import Collection
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_design, make_user


def test_save_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/save")

    assert response.status_code == 401


def test_save_creates_default_collection_and_increments_save_count(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"saved": True, "save_count": 1}
    default_collection = (
        db_session.query(Collection)
        .filter(Collection.user_id == viewer.id, Collection.is_default.is_(True))
        .one()
    )
    assert default_collection.name == "Saved Designs"


def test_saving_twice_does_not_double_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))
    second = client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    assert second.json() == {"saved": True, "save_count": 1}


def test_unsave_decrements_save_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    response = client.delete(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"saved": False, "save_count": 0}


def test_unsaving_when_never_saved_is_a_no_op(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.delete(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"saved": False, "save_count": 0}


def test_save_unpublished_design_returns_404(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="draft")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    assert response.status_code == 404


def test_saved_designs_screen_lists_saved_designs(client: TestClient, db_session: Session) -> None:
    first = make_design(db_session, status="published")
    first.title = "First Saved"
    second = make_design(db_session, status="published")
    second.title = "Second Saved"
    not_saved = make_design(db_session, status="published")
    db_session.add_all([first, second, not_saved])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    client.post(f"/api/v1/designs/{first.id}/save", headers=auth_headers(token))
    client.post(f"/api/v1/designs/{second.id}/save", headers=auth_headers(token))

    response = client.get("/api/v1/designs/saved", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert ids == {str(first.id), str(second.id)}
    assert str(not_saved.id) not in ids


def test_saved_designs_screen_orders_most_recently_saved_first(
    client: TestClient, db_session: Session
) -> None:
    # `now()` is frozen for the duration of a Postgres transaction, so two
    # saves issued back-to-back in this test's transaction would otherwise
    # get an identical `added_at` — set them explicitly apart.
    from datetime import UTC, datetime, timedelta

    from app.db.models.engagement import CollectionItem

    older = make_design(db_session, status="published")
    newer = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    client.post(f"/api/v1/designs/{older.id}/save", headers=auth_headers(token))
    client.post(f"/api/v1/designs/{newer.id}/save", headers=auth_headers(token))

    older_item = db_session.query(CollectionItem).filter(CollectionItem.design_id == older.id).one()
    newer_item = db_session.query(CollectionItem).filter(CollectionItem.design_id == newer.id).one()
    base = datetime.now(UTC)
    older_item.added_at = base
    newer_item.added_at = base + timedelta(seconds=1)
    db_session.commit()

    response = client.get("/api/v1/designs/saved", headers=auth_headers(token))

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(newer.id), str(older.id)]


def test_saved_designs_screen_empty_state(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/saved", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"items": [], "page_info": {"next_cursor": None, "has_more": False}}


def test_saved_designs_pagination_walks_full_list_without_duplicates(
    client: TestClient, db_session: Session
) -> None:
    designs = [make_design(db_session, status="published") for _ in range(5)]
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    for design in designs:
        client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))

    seen_ids: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params: dict[str, object] = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/api/v1/designs/saved", params=params, headers=auth_headers(token))
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


def test_design_detail_reflects_save_state(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    before = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert before.json()["is_saved"] is False

    client.post(f"/api/v1/designs/{design.id}/save", headers=auth_headers(token))
    after = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert after.json()["is_saved"] is True
    assert after.json()["save_count"] == 1
