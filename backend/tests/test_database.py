import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.enums import EventDevice, EventSeverity, JobMode, JobStep
from backend.app.models import Item, Job, JobEvent, Routine, RoutineItem
from backend.app.schemas import (
    JobCreate,
    JobEventCreate,
    LocationCreate,
    RoutineItemCreate,
)
from backend.app.seed import seed_development_data
from backend.app.services import (
    DomainValidationError,
    create_job_event,
    create_job_from_routine,
    get_job_events,
)

CORE_TABLES = {
    "locations",
    "items",
    "routines",
    "routine_items",
    "jobs",
    "job_items",
    "job_events",
}


def create_seeded_job(session: Session, routine_code: str = "OUTING_PREP") -> Job:
    seed_development_data(session)
    routine = session.scalar(select(Routine).where(Routine.code == routine_code))
    assert routine is not None
    job = create_job_from_routine(
        session, JobCreate(routine_id=routine.id, mode=JobMode.SIMULATION)
    )
    session.commit()
    return job


def test_migration_creates_exact_core_tables(test_engine) -> None:
    table_names = set(inspect(test_engine).get_table_names())
    assert CORE_TABLES.issubset(table_names)
    assert "alembic_version" in table_names


def test_seed_is_idempotent(db_session: Session) -> None:
    first = seed_development_data(db_session)
    second = seed_development_data(db_session)

    assert first.locations_created == 5
    assert first.items_created == 5
    assert first.routines_created == 2
    assert first.routine_items_created == 8
    assert second.locations_created == 0
    assert second.items_created == 0
    assert second.routines_created == 0
    assert second.routine_items_created == 0


def test_duplicate_tag_id_is_rejected(db_session: Session) -> None:
    seed_development_data(db_session)
    db_session.add(Item(tag_id="TAG-001", name="중복 약통", category="의약품"))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_foreign_key_is_rejected(db_session: Session) -> None:
    db_session.add(
        Item(
            tag_id="TAG-999",
            name="잘못된 물품",
            category="테스트",
            home_location_id=uuid.uuid4(),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_routine_relationships_and_processing_order(db_session: Session) -> None:
    seed_development_data(db_session)
    routine = db_session.scalar(select(Routine).where(Routine.code == "OUTING_PREP"))

    assert routine is not None
    assert [entry.sequence for entry in routine.routine_items] == [1, 2, 3]
    assert [entry.item.tag_id for entry in routine.routine_items] == [
        "TAG-001",
        "TAG-003",
        "TAG-004",
    ]
    assert {entry.target_location.code for entry in routine.routine_items} == {"BAG"}


def test_job_copies_snapshots_and_relationships(db_session: Session) -> None:
    job = create_seeded_job(db_session)
    first_item = job.job_items[0]
    original_item_name = first_item.item_name_snapshot
    original_routine_name = job.routine_name_snapshot

    assert len(job.job_items) == 3
    assert job.events[0].event_type == "PLAN_CREATED"
    assert first_item.target_location_code_snapshot == "BAG"

    assert job.routine is not None
    assert first_item.item is not None
    job.routine.name = "변경된 루틴 이름"
    first_item.item.name = "변경된 물품 이름"
    db_session.commit()

    assert job.routine_name_snapshot == original_routine_name
    assert first_item.item_name_snapshot == original_item_name


def test_events_are_returned_in_chronological_order(db_session: Session) -> None:
    job = create_seeded_job(db_session)
    base_time = datetime.now(UTC)
    db_session.add_all(
        [
            JobEvent(
                job_id=job.id,
                event_type="VERIFY_SUCCESS",
                step=JobStep.VERIFY,
                device=EventDevice.ESP32,
                severity=EventSeverity.SUCCESS,
                message="검증 성공",
                created_at=base_time + timedelta(seconds=2),
            ),
            JobEvent(
                job_id=job.id,
                event_type="PICK_SUCCESS",
                step=JobStep.PICK,
                device=EventDevice.ARM,
                severity=EventSeverity.SUCCESS,
                message="파지 성공",
                created_at=base_time + timedelta(seconds=1),
            ),
        ]
    )
    db_session.commit()

    event_types = [event.event_type for event in get_job_events(db_session, job.id)]
    assert event_types[-2:] == ["PICK_SUCCESS", "VERIFY_SUCCESS"]


def test_negative_retry_count_is_rejected(db_session: Session) -> None:
    job = Job(mode=JobMode.SIMULATION, retry_count=-1)
    db_session.add(job)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_execution_history_survives_master_item_deletion(db_session: Session) -> None:
    job = create_seeded_job(db_session)
    historical_item = job.job_items[0]
    item = historical_item.item
    assert item is not None
    snapshot = historical_item.item_name_snapshot

    links = list(
        db_session.scalars(select(RoutineItem).where(RoutineItem.item_id == item.id))
    )
    for link in links:
        db_session.delete(link)
    db_session.commit()

    db_session.delete(item)
    db_session.commit()
    db_session.refresh(historical_item)

    assert historical_item.item_id is None
    assert historical_item.item_name_snapshot == snapshot
    assert db_session.get(Job, job.id) is not None


def test_job_with_history_cannot_be_deleted_accidentally(db_session: Session) -> None:
    job = create_seeded_job(db_session)
    db_session.delete(job)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_mismatched_job_item(db_session: Session) -> None:
    first_job = create_seeded_job(db_session)
    routine = db_session.scalar(select(Routine).where(Routine.code == "OUTING_PREP"))
    assert routine is not None
    second_job = create_job_from_routine(
        db_session, JobCreate(routine_id=routine.id, mode=JobMode.SIMULATION)
    )
    db_session.commit()

    request = JobEventCreate(
        job_id=second_job.id,
        job_item_id=first_job.job_items[0].id,
        event_type="PICK_STARTED",
        step=JobStep.PICK,
        device=EventDevice.ARM,
        severity=EventSeverity.INFO,
        message="파지 시작",
    )
    with pytest.raises(DomainValidationError):
        create_job_event(db_session, request)


def test_pydantic_rejects_empty_names_and_invalid_sequences() -> None:
    with pytest.raises(ValidationError):
        LocationCreate(code="EMPTY", name="   ")

    with pytest.raises(ValidationError):
        RoutineItemCreate(
            routine_id=uuid.uuid4(),
            item_id=uuid.uuid4(),
            target_location_id=uuid.uuid4(),
            sequence=0,
        )

    with pytest.raises(ValidationError):
        JobCreate(routine_id=uuid.uuid4(), mode="INVALID")  # type: ignore[arg-type]
