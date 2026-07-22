from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.design import DesignCategory
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_design, make_user


def _search(client: TestClient, token: str, **params: object) -> dict:
    response = client.get("/api/v1/designs/search", params=params, headers=auth_headers(token))
    return response


def test_search_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/search")
    assert response.status_code == 401


def test_keyword_search_matches_title(client: TestClient, db_session: Session) -> None:
    matching = make_design(db_session, status="published")
    matching.title = "Bridal Peacock Mehndi"
    non_matching = make_design(db_session, status="published")
    non_matching.title = "Simple Floral Pattern"
    db_session.add_all([matching, non_matching])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="peacock")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(matching.id)]


def test_keyword_search_matches_description(client: TestClient, db_session: Session) -> None:
    matching = make_design(db_session, status="published")
    matching.title = "Untitled"
    matching.description = "Perfect for a bridal ceremony with intricate detailing"
    non_matching = make_design(db_session, status="published")
    non_matching.title = "Untitled"
    non_matching.description = "A casual everyday look"
    db_session.add_all([matching, non_matching])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="ceremony")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(matching.id)]


def test_no_keyword_returns_all_published_designs(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    make_design(db_session, status="published")
    draft = make_design(db_session, status="draft")
    viewer = make_user(db_session)
    db_session.add(draft)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert str(draft.id) not in ids
    assert len(ids) == 2


def test_empty_search_results(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="nonexistentkeywordxyz")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["page_info"]["has_more"] is False
    assert body["page_info"]["next_cursor"] is None


def test_category_filter_axes_are_and_within_axis_or(
    client: TestClient, db_session: Session
) -> None:
    style_a = make_category(db_session, category_type="style")
    style_b = make_category(db_session, category_type="style")
    occasion = make_category(db_session, category_type="occasion")

    both_axes = make_design(db_session, status="published")
    db_session.add(DesignCategory(design_id=both_axes.id, category_id=style_a.id))
    db_session.add(DesignCategory(design_id=both_axes.id, category_id=occasion.id))

    only_style = make_design(db_session, status="published")
    db_session.add(DesignCategory(design_id=only_style.id, category_id=style_b.id))

    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(
        client,
        token,
        category_id=[str(style_a.id), str(style_b.id), str(occasion.id)],
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(both_axes.id)]


def test_artist_filter(client: TestClient, db_session: Session) -> None:
    artist = make_artist_profile(db_session)
    matching = make_design(db_session, artist_profile=artist, status="published")
    non_matching = make_design(db_session, status="published")
    db_session.add_all([matching, non_matching])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, artist_id=str(artist.id))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(matching.id)]


def test_premium_filter(client: TestClient, db_session: Session) -> None:
    free = make_design(db_session, status="published")
    free.is_premium = False
    premium = make_design(db_session, status="published")
    premium.is_premium = True
    db_session.add_all([free, premium])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, is_premium=True)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(premium.id)]


def test_difficulty_filter(client: TestClient, db_session: Session) -> None:
    beginner = make_design(db_session, status="published")
    beginner.difficulty_level = "beginner"
    advanced = make_design(db_session, status="published")
    advanced.difficulty_level = "advanced"
    db_session.add_all([beginner, advanced])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, difficulty_level="advanced")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(advanced.id)]


def test_body_placement_filter(client: TestClient, db_session: Session) -> None:
    hand = make_design(db_session, status="published")
    hand.body_placement = "hand"
    foot = make_design(db_session, status="published")
    foot.body_placement = "foot"
    db_session.add_all([hand, foot])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, body_placement="foot")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(foot.id)]


def test_clear_filters_returns_full_unfiltered_result(
    client: TestClient, db_session: Session
) -> None:
    premium = make_design(db_session, status="published")
    premium.is_premium = True
    free = make_design(db_session, status="published")
    free.is_premium = False
    db_session.add_all([premium, free])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    filtered = _search(client, token, is_premium=True)
    assert len(filtered.json()["items"]) == 1

    cleared = _search(client, token)
    assert cleared.status_code == 200
    assert len(cleared.json()["items"]) == 2


def test_sort_newest_orders_by_created_at_descending(
    client: TestClient, db_session: Session
) -> None:
    # `now()` is frozen for the duration of a Postgres transaction, so two
    # designs created back-to-back in the same test transaction would
    # otherwise get an identical `created_at` — set them explicitly apart.
    older = make_design(db_session, status="published")
    older.created_at = datetime.now(UTC) - timedelta(hours=1)
    newer = make_design(db_session, status="published")
    db_session.add_all([older, newer])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, sort="newest")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(newer.id), str(older.id)]


def test_sort_popular_orders_by_view_count_descending(
    client: TestClient, db_session: Session
) -> None:
    low = make_design(db_session, status="published")
    low.view_count = 1
    high = make_design(db_session, status="published")
    high.view_count = 50
    db_session.add_all([low, high])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, sort="popular")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(high.id), str(low.id)]


def test_sort_most_saved_orders_by_save_count_descending(
    client: TestClient, db_session: Session
) -> None:
    low = make_design(db_session, status="published")
    low.save_count = 0
    high = make_design(db_session, status="published")
    high.save_count = 7
    db_session.add_all([low, high])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, sort="most_saved")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(high.id), str(low.id)]


def test_relevance_sort_ranks_stronger_matches_first(
    client: TestClient, db_session: Session
) -> None:
    weak = make_design(db_session, status="published")
    weak.title = "Floral pattern"
    weak.description = "mentions henna once"
    strong = make_design(db_session, status="published")
    strong.title = "Henna henna henna design"
    strong.description = "all about henna henna"
    db_session.add_all([weak, strong])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="henna", sort="relevance")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(strong.id), str(weak.id)]


def test_search_result_pagination_walks_full_list_without_duplicates(
    client: TestClient, db_session: Session
) -> None:
    designs = [make_design(db_session, status="published") for _ in range(5)]
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    seen_ids: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params: dict[str, object] = {"sort": "newest", "limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = _search(client, token, **params)
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


def test_invalid_sort_value_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, sort="popularity")

    assert response.status_code == 422


def test_invalid_difficulty_level_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, difficulty_level="expert")

    assert response.status_code == 422


def test_invalid_body_placement_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, body_placement="shoulder")

    assert response.status_code == 422


def test_too_many_category_filters_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    category_ids = [str(make_category(db_session).id) for _ in range(21)]
    db_session.commit()

    response = _search(client, token, category_id=category_ids)

    assert response.status_code == 422


def test_malformed_cursor_is_rejected(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, cursor="not-a-valid-cursor!!")

    assert response.status_code == 422


def test_cursor_from_a_different_sort_is_rejected(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    make_design(db_session, status="published")
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    newest_page = _search(client, token, sort="newest", limit=1).json()
    cursor = newest_page["page_info"]["next_cursor"]
    assert cursor is not None

    response = _search(client, token, sort="popular", cursor=cursor)

    assert response.status_code == 422


def test_query_is_truncated_and_control_characters_stripped(
    client: TestClient, db_session: Session
) -> None:
    matching = make_design(db_session, status="published")
    matching.title = "Mandala Design"
    db_session.add(matching)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="mandala\x00\x01  ")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(matching.id)]


def test_search_records_a_search_event(client: TestClient, db_session: Session) -> None:
    from app.db.models.search import SearchEvent

    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = _search(client, token, q="anything", sort="newest")
    assert response.status_code == 200

    events = db_session.query(SearchEvent).filter(SearchEvent.user_id == viewer.id).all()
    assert len(events) == 1
    assert events[0].query == "anything"
    assert events[0].filters["sort"] == "newest"
