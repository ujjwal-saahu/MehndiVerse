from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus
from app.db.models.artist import ArtistProfile, ArtistService
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user


def _approved(
    db_session: Session, *, city: str | None = None, country: str | None = None, rating: float = 0
) -> ArtistProfile:
    profile = make_artist_profile(db_session)
    profile.city = city
    profile.country = country
    profile.rating_average = rating
    profile.rating_count = 10 if rating else 0
    db_session.add(profile)
    return profile


def _submitted(db_session: Session) -> ArtistProfile:
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.SUBMITTED.value
    db_session.add(profile)
    return profile


def _draft(db_session: Session) -> ArtistProfile:
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.DRAFT.value
    db_session.add(profile)
    return profile


def _viewer_token(db_session: Session) -> str:
    viewer = make_user(db_session, role="customer")
    db_session.commit()
    return sign_token(viewer.id, email=viewer.email)


def test_directory_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artists")
    assert response.status_code == 401


def test_directory_only_shows_approved_by_default(client: TestClient, db_session: Session) -> None:
    approved = _approved(db_session, city="Jaipur", country="IN", rating=4.5)
    _submitted(db_session)
    _draft(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get("/api/v1/artists", headers=auth_headers(token))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(approved.id)]


def test_verified_only_false_also_includes_submitted_and_under_review(
    client: TestClient, db_session: Session
) -> None:
    approved = _approved(db_session, rating=4.0)
    submitted = _submitted(db_session)
    _draft(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        "/api/v1/artists", params={"verified_only": "false"}, headers=auth_headers(token)
    )

    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(approved.id), str(submitted.id)}


def test_city_filter(client: TestClient, db_session: Session) -> None:
    jaipur = _approved(db_session, city="Jaipur", rating=3)
    _approved(db_session, city="Mumbai", rating=3)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get("/api/v1/artists", params={"city": "jai"}, headers=auth_headers(token))

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(jaipur.id)]


def test_country_filter(client: TestClient, db_session: Session) -> None:
    india = _approved(db_session, country="IN", rating=3)
    _approved(db_session, country="US", rating=3)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get("/api/v1/artists", params={"country": "in"}, headers=auth_headers(token))

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(india.id)]


def test_min_rating_filter(client: TestClient, db_session: Session) -> None:
    good = _approved(db_session, rating=4.5)
    _approved(db_session, rating=2.0)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        "/api/v1/artists", params={"min_rating": 4.0}, headers=auth_headers(token)
    )

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(good.id)]


def test_service_filter_matches_active_service_name(
    client: TestClient, db_session: Session
) -> None:
    with_service = _approved(db_session, rating=3)
    without_service = _approved(db_session, rating=3)
    db_session.flush()
    db_session.add(
        ArtistService(
            artist_profile_id=with_service.id,
            name="Bridal Henna",
            pricing_type="fixed",
            price_amount=1000,
            currency="INR",
        )
    )
    db_session.add(
        ArtistService(
            artist_profile_id=without_service.id,
            name="Party Glitter Tattoo",
            pricing_type="fixed",
            price_amount=500,
            currency="INR",
        )
    )
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        "/api/v1/artists", params={"service": "henna"}, headers=auth_headers(token)
    )

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(with_service.id)]


def test_pagination(client: TestClient, db_session: Session) -> None:
    for rating in (5.0, 4.0, 3.0):
        _approved(db_session, rating=rating)
    db_session.commit()
    token = _viewer_token(db_session)

    first_page = client.get(
        "/api/v1/artists", params={"limit": 2}, headers=auth_headers(token)
    ).json()
    assert len(first_page["items"]) == 2
    assert first_page["page_info"]["has_more"] is True

    second_page = client.get(
        "/api/v1/artists",
        params={"limit": 2, "cursor": first_page["page_info"]["next_cursor"]},
        headers=auth_headers(token),
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["page_info"]["has_more"] is False
