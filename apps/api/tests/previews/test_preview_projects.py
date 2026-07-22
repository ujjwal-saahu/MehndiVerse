"""Hand/foot design preview projects — see docs/hand-foot-preview.md."""

import io
import json

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.messaging import Conversation, Message
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_design,
    make_preview_project,
    make_subscription,
    make_subscription_plan,
    make_user,
)


def _png_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(80, 20, 140)).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes_with_exif() -> bytes:
    image = Image.new("RGB", (48, 48), color=(200, 150, 20))
    exif = Image.Exif()
    exif[0x9003] = "2024:01:01 12:00:00"  # DateTimeOriginal
    exif[0x010F] = "PhoneCameraMaker"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def _mock_upload(storage_mock, *, side_effect=None) -> None:
    if side_effect is not None:
        storage_mock.post(url__regex=r"/object/preview-projects/.*").mock(side_effect=side_effect)
    else:
        storage_mock.post(url__regex=r"/object/preview-projects/.*").mock(
            return_value=httpx.Response(200, json={"Key": "preview-projects/mock"})
        )
    storage_mock.post(url__regex=r"/object/sign/preview-projects/.*").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/preview-projects/mock?token=abc"}
        )
    )


def _mock_sign(storage_mock) -> None:
    storage_mock.post(url__regex=r"/object/sign/preview-projects/.*").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/preview-projects/mock?token=abc"}
        )
    )


def _mock_delete(storage_mock) -> httpx.Response:
    return storage_mock.delete(url__regex=r"/object/preview-projects/.*").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )


def test_create_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/previews", files={"file": ("hand.png", _png_bytes(), "image/png")}
    )
    assert response.status_code == 401


def test_create_rejects_an_unsupported_file_type(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/previews",
        files={"file": ("hand.txt", b"not an image", "text/plain")},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_create_succeeds_with_a_photo_and_a_design(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_upload(storage_mock)
    customer = make_user(db_session, role="customer")
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/previews",
        files={"file": ("hand.png", _png_bytes(), "image/png")},
        data={
            "design_id": str(design.id),
            "overlay_transform": json.dumps(
                {"x": 0.4, "y": 0.6, "scale": 1.2, "rotation_degrees": 15, "opacity": 0.9}
            ),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["design"]["id"] == str(design.id)
    assert body["overlay_transform"]["scale"] == 1.2
    assert body["source_image_url"]
    assert body["result_image_url"] is None
    assert body["source_width"] == 64
    assert body["source_height"] == 64


def test_create_rejects_a_premium_design_without_entitlement(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/previews",
        files={"file": ("hand.png", _png_bytes(), "image/png")},
        data={"design_id": str(design.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_create_allows_a_premium_design_for_an_entitled_customer(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_upload(storage_mock)
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"premium_design_access": True}
    )
    make_subscription(db_session, user=customer, plan=plan, status="active")
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/previews",
        files={"file": ("hand.png", _png_bytes(), "image/png")},
        data={"design_id": str(design.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 201


def test_exif_metadata_is_stripped_before_upload(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    captured: dict[str, bytes] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json={"Key": "preview-projects/mock"})

    _mock_upload(storage_mock, side_effect=_capture)

    source = _jpeg_bytes_with_exif()
    assert Image.open(io.BytesIO(source)).getexif()  # sanity: source really has EXIF

    response = client.post(
        "/api/v1/previews",
        files={"file": ("hand.jpg", source, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    uploaded_image = Image.open(io.BytesIO(captured["body"]))
    assert not uploaded_image.getexif()


def test_update_transform_without_a_new_photo(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_sign(storage_mock)
    user = make_user(db_session)
    preview = make_preview_project(db_session, user=user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        f"/api/v1/previews/{preview.id}",
        data={
            "overlay_transform": json.dumps(
                {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation_degrees": 0, "opacity": 1.0}
            )
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["overlay_transform"]["scale"] == 1.0


def test_only_the_owner_can_update(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    preview = make_preview_project(db_session, user=owner)
    db_session.commit()
    token = sign_token(other.id, email=other.email)

    response = client.patch(
        f"/api/v1/previews/{preview.id}",
        data={"overlay_transform": json.dumps({})},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_export_stores_the_composited_image(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_upload(storage_mock)
    user = make_user(db_session)
    preview = make_preview_project(db_session, user=user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        f"/api/v1/previews/{preview.id}/export",
        files={"file": ("export.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["result_image_url"]

    db_session.refresh(preview)
    assert preview.result_storage_path is not None


def test_share_returns_a_signed_url_with_a_ttl(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_sign(storage_mock)
    user = make_user(db_session)
    preview = make_preview_project(db_session, user=user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get(f"/api/v1/previews/{preview.id}/share", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["url"]
    assert body["expires_in_seconds"] == 3600


def test_send_to_artist_requires_being_the_booking_customer(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="customer")
    other_customer = make_user(db_session, role="customer")
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(db_session, customer=other_customer, artist_profile=artist_profile)
    preview = make_preview_project(db_session, user=owner)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/previews/{preview.id}/send-to-artist",
        json={"booking_id": str(booking.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_send_to_artist_creates_a_message_and_grants_the_artist_access(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_sign(storage_mock)
    customer = make_user(db_session, role="customer")
    artist_user = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=artist_user)
    booking = make_booking(db_session, customer=customer, artist_profile=artist_profile)
    preview = make_preview_project(db_session, user=customer)
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/previews/{preview.id}/send-to-artist",
        json={"booking_id": str(booking.id)},
        headers=auth_headers(customer_token),
    )
    assert response.status_code == 200
    assert response.json()["shared_with_booking_id"] == str(booking.id)

    conversation = db_session.execute(
        select(Conversation).where(Conversation.booking_id == booking.id)
    ).scalar_one()
    messages = (
        db_session.execute(select(Message).where(Message.conversation_id == conversation.id))
        .scalars()
        .all()
    )
    assert len(messages) == 1

    artist_token = sign_token(artist_user.id, email=artist_user.email)
    view_response = client.get(f"/api/v1/previews/{preview.id}", headers=auth_headers(artist_token))
    assert view_response.status_code == 200


def test_a_stranger_cannot_view_a_preview(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    preview = make_preview_project(db_session, user=owner)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/previews/{preview.id}", headers=auth_headers(token))
    assert response.status_code == 403


def test_list_mine_only_shows_the_callers_own_previews(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    _mock_sign(storage_mock)
    owner = make_user(db_session)
    other = make_user(db_session)
    make_preview_project(db_session, user=owner)
    make_preview_project(db_session, user=other)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get("/api/v1/previews/mine", headers=auth_headers(token))
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_delete_soft_deletes_and_cleans_up_storage(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    delete_route = _mock_delete(storage_mock)
    user = make_user(db_session)
    preview = make_preview_project(db_session, user=user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.delete(f"/api/v1/previews/{preview.id}", headers=auth_headers(token))
    assert response.status_code == 204
    assert delete_route.call_count == 1

    db_session.refresh(preview)
    assert preview.deleted_at is not None

    get_response = client.get(f"/api/v1/previews/{preview.id}", headers=auth_headers(token))
    assert get_response.status_code == 404
