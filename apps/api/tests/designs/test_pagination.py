from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.design import Design, DesignCategory, DesignImage
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_design, make_user


def _make_published(db_session: Session, count: int) -> list[Design]:
    return [make_design(db_session, status="published") for _ in range(count)]


def test_list_published_designs_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/published")
    assert response.status_code == 401


def test_default_page_has_no_more_when_under_the_limit(
    client: TestClient, db_session: Session
) -> None:
    _make_published(db_session, 3)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert body["page_info"]["has_more"] is False
    assert body["page_info"]["next_cursor"] is None


def test_cursor_pagination_walks_the_full_list_without_duplicates(
    client: TestClient, db_session: Session
) -> None:
    designs = _make_published(db_session, 5)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    seen_ids: list[str] = []
    cursor: str | None = None
    for _ in range(10):  # safety cap against an infinite loop bug
        params = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get(
            "/api/v1/designs/published", params=params, headers=auth_headers(token)
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


def test_trending_sort_orders_by_view_count_descending(
    client: TestClient, db_session: Session
) -> None:
    low = make_design(db_session, status="published")
    high = make_design(db_session, status="published")
    low.view_count = 1
    high.view_count = 99
    db_session.add_all([low, high])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/published", params={"sort": "trending"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [str(high.id), str(low.id)]


def test_invalid_sort_value_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/published", params={"sort": "popular"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_malformed_cursor_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/published",
        params={"cursor": "not-a-valid-cursor!!"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_cursor_from_a_different_sort_mode_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    _make_published(db_session, 3)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    latest_page = client.get(
        "/api/v1/designs/published",
        params={"sort": "latest", "limit": 1},
        headers=auth_headers(token),
    ).json()
    cursor = latest_page["page_info"]["next_cursor"]
    assert cursor is not None

    response = client.get(
        "/api/v1/designs/published",
        params={"sort": "trending", "cursor": cursor},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_list_published_designs_sets_a_safe_public_cache_header(
    client: TestClient, db_session: Session
) -> None:
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("public")


def test_thumbnail_url_prefers_medium_thumbnail_over_full_image(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    db_session.add(
        DesignImage(
            design_id=design.id,
            status="ready",
            image_url="https://example.test/original.jpg",
            thumbnail_medium_url="https://example.test/thumb-medium.jpg",
            is_primary=True,
        )
    )
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["thumbnail_url"] == "https://example.test/thumb-medium.jpg"


def test_pending_and_failed_images_are_never_used_as_thumbnails(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    db_session.add(DesignImage(design_id=design.id, status="pending", sort_order=0))
    db_session.add(
        DesignImage(design_id=design.id, status="failed", sort_order=1, processing_error="boom")
    )
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["thumbnail_url"] is None


def test_list_published_designs_includes_artist_display_name(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    artist_profile.business_name = "Henna by Asha"
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    db_session.add_all([artist_profile, design])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["items"][0]["artist_display_name"] == "Henna by Asha"


def test_category_filter_uses_category_id(client: TestClient, db_session: Session) -> None:
    matching = make_design(db_session, status="published")
    non_matching = make_design(db_session, status="published")
    category = make_category(db_session, category_type="style")
    db_session.add(DesignCategory(design_id=matching.id, category_id=category.id))
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/published",
        params={"category_id": str(category.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(matching.id)]
    assert str(non_matching.id) not in ids
