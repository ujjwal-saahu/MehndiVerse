"""Genuine cross-connection concurrency tests for the "prevent duplicate
likes"/"prevent duplicate collection items" requirements.

Every other test in tests/engagement and tests/collections uses the
per-test `db_session` fixture, which is a single connection/transaction —
sequential calls within it still exercise the same unique-constraint-conflict
code path a real race would hit (Postgres enforces uniqueness against a
transaction's own uncommitted rows too), but it can't demonstrate that two
*independent* connections racing against already-committed rows behave
correctly. These tests open their own connections/sessions (bypassing the
rollback-based test isolation, with explicit setup/teardown via committed
ORM inserts) and run the service functions from separate threads so the
race is real, not simulated.
"""

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.design import Design
from app.db.models.engagement import Collection
from app.db.models.user import User
from app.services.engagement import (
    add_item_to_collection,
    get_or_create_default_collection,
    like_design,
)


def _run_concurrently[T](engine: Engine, fns: list[Callable[[Session], T]]) -> list[T]:
    def worker(fn: Callable[[Session], T]) -> T:
        connection = engine.connect()
        session = sessionmaker(bind=connection)()
        try:
            result = fn(session)
            session.commit()
            return result
        finally:
            session.close()
            connection.close()

    with ThreadPoolExecutor(max_workers=len(fns)) as executor:
        futures = [executor.submit(worker, fn) for fn in fns]
        return [future.result() for future in futures]


def _committed_user_and_design(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    connection = engine.connect()
    session = sessionmaker(bind=connection)()
    try:
        user = User(email=f"{uuid.uuid4()}@example.com", role="customer")
        design = Design(title="Concurrency Test", status="published")
        session.add_all([user, design])
        session.commit()
        return user.id, design.id
    finally:
        session.close()
        connection.close()


def test_concurrent_likes_only_count_once(db_engine: Engine) -> None:
    user_id, design_id = _committed_user_and_design(db_engine)
    try:
        _run_concurrently(
            db_engine,
            [
                lambda session: like_design(session, user_id=user_id, design_id=design_id)
                for _ in range(5)
            ],
        )

        with db_engine.connect() as conn:
            like_rows = conn.execute(
                text("SELECT count(*) FROM likes WHERE user_id = :u AND design_id = :d"),
                {"u": user_id, "d": design_id},
            ).scalar_one()
            like_count = conn.execute(
                text("SELECT like_count FROM designs WHERE id = :d"), {"d": design_id}
            ).scalar_one()

        assert like_rows == 1
        assert like_count == 1
    finally:
        with db_engine.begin() as conn:
            conn.execute(text("DELETE FROM likes WHERE design_id = :d"), {"d": design_id})
            conn.execute(text("DELETE FROM designs WHERE id = :d"), {"d": design_id})
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})


def test_concurrent_saves_create_exactly_one_default_collection(db_engine: Engine) -> None:
    user_id, design_id = _committed_user_and_design(db_engine)

    def save(session: Session) -> None:
        collection = get_or_create_default_collection(session, user_id=user_id)
        add_item_to_collection(session, collection=collection, design_id=design_id)

    try:
        _run_concurrently(db_engine, [save for _ in range(5)])

        with db_engine.connect() as conn:
            default_collections = conn.execute(
                text("SELECT count(*) FROM collections WHERE user_id = :u AND is_default = true"),
                {"u": user_id},
            ).scalar_one()
            item_rows = conn.execute(
                text(
                    "SELECT count(*) FROM collection_items ci "
                    "JOIN collections c ON c.id = ci.collection_id "
                    "WHERE c.user_id = :u AND ci.design_id = :d"
                ),
                {"u": user_id, "d": design_id},
            ).scalar_one()
            save_count = conn.execute(
                text("SELECT save_count FROM designs WHERE id = :d"), {"d": design_id}
            ).scalar_one()

        assert default_collections == 1
        assert item_rows == 1
        assert save_count == 1
    finally:
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM collection_items WHERE collection_id IN "
                    "(SELECT id FROM collections WHERE user_id = :u)"
                ),
                {"u": user_id},
            )
            conn.execute(text("DELETE FROM collections WHERE user_id = :u"), {"u": user_id})
            conn.execute(text("DELETE FROM designs WHERE id = :d"), {"d": design_id})
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})


def test_concurrent_add_item_to_named_collection_only_adds_once(db_engine: Engine) -> None:
    user_id, design_id = _committed_user_and_design(db_engine)

    connection = db_engine.connect()
    session = sessionmaker(bind=connection)()
    try:
        collection = Collection(user_id=user_id, name="Concurrency Collection", is_private=True)
        session.add(collection)
        session.commit()
        collection_id = collection.id
    finally:
        session.close()
        connection.close()

    def add(session: Session) -> None:
        collection = session.get(Collection, collection_id)
        assert collection is not None
        add_item_to_collection(session, collection=collection, design_id=design_id)

    try:
        _run_concurrently(db_engine, [add for _ in range(5)])

        with db_engine.connect() as conn:
            item_rows = conn.execute(
                text(
                    "SELECT count(*) FROM collection_items "
                    "WHERE collection_id = :c AND design_id = :d"
                ),
                {"c": collection_id, "d": design_id},
            ).scalar_one()

        assert item_rows == 1
    finally:
        with db_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM collection_items WHERE collection_id = :c"),
                {"c": collection_id},
            )
            conn.execute(text("DELETE FROM collections WHERE id = :c"), {"c": collection_id})
            conn.execute(text("DELETE FROM designs WHERE id = :d"), {"d": design_id})
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
