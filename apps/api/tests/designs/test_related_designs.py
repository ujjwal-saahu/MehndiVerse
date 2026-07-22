from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.design import DesignCategory
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_design, make_user


def test_related_designs_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.get(f"/api/v1/designs/{design.id}/related")

    assert response.status_code == 401


def test_related_designs_share_a_category_and_exclude_self(
    client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session, category_type="style")
    anchor = make_design(db_session, status="published")
    related = make_design(db_session, status="published")
    unrelated = make_design(db_session, status="published")
    db_session.add_all(
        [
            DesignCategory(design_id=anchor.id, category_id=category.id),
            DesignCategory(design_id=related.id, category_id=category.id),
        ]
    )
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{anchor.id}/related", headers=auth_headers(token))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(related.id) in ids
    assert str(anchor.id) not in ids
    assert str(unrelated.id) not in ids


def test_related_designs_excludes_unpublished_matches(
    client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session, category_type="style")
    anchor = make_design(db_session, status="published")
    draft_match = make_design(db_session, status="draft")
    db_session.add_all(
        [
            DesignCategory(design_id=anchor.id, category_id=category.id),
            DesignCategory(design_id=draft_match.id, category_id=category.id),
        ]
    )
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{anchor.id}/related", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == []


def test_related_designs_is_empty_when_design_has_no_categories(
    client: TestClient, db_session: Session
) -> None:
    anchor = make_design(db_session, status="published")
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{anchor.id}/related", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == []


def test_related_designs_for_a_private_draft_is_hidden_from_strangers(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    draft = make_design(db_session, artist_profile=artist_profile)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/designs/{draft.id}/related", headers=auth_headers(token))

    assert response.status_code == 404


def test_related_designs_sets_a_safe_public_cache_header(
    client: TestClient, db_session: Session
) -> None:
    anchor = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{anchor.id}/related", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("public")
