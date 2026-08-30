import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.enums import EventDevice, EventSeverity, JobStatus, JobStep
from backend.app.models import Job, JobEvent, JobItem, Routine
from backend.app.schemas import JobCreate, JobEventCreate


class DomainValidationError(ValueError):
    pass


class ResourceNotFoundError(LookupError):
    pass


def create_job_from_routine(session: Session, request: JobCreate) -> Job:
    routine = session.get(Routine, request.routine_id)
    if routine is None:
        raise ResourceNotFoundError("루틴을 찾을 수 없습니다.")
    if not routine.is_active:
        raise DomainValidationError("비활성화된 루틴으로 작업을 만들 수 없습니다.")
    if not routine.routine_items:
        raise DomainValidationError("루틴에 등록된 물품이 없습니다.")

    job = Job(
        routine_id=routine.id,
        routine_code_snapshot=routine.code,
        routine_name_snapshot=routine.name,
        mode=request.mode,
        status=JobStatus.WAITING,
        current_step=JobStep.IDLE,
    )
    session.add(job)
    session.flush()

    for configured_item in routine.routine_items:
        item = configured_item.item
        target = configured_item.target_location
        source = item.home_location

        if not item.is_active:
            raise DomainValidationError(
                f"비활성화된 물품이 루틴에 포함되어 있습니다: {item.tag_id}"
            )
        if not target.is_active:
            raise DomainValidationError(
                f"비활성화된 목적지가 루틴에 포함되어 있습니다: {target.code}"
            )

        session.add(
            JobItem(
                job_id=job.id,
                item_id=item.id,
                sequence=configured_item.sequence,
                source_location_id=source.id if source else None,
                target_location_id=target.id,
                item_name_snapshot=item.name,
                tag_id_snapshot=item.tag_id,
                source_location_code_snapshot=source.code if source else None,
                source_location_name_snapshot=source.name if source else None,
                target_location_code_snapshot=target.code,
                target_location_name_snapshot=target.name,
            )
        )

    session.add(
        JobEvent(
            job_id=job.id,
            event_type="PLAN_CREATED",
            step=JobStep.PLAN,
            device=EventDevice.SYSTEM,
            severity=EventSeverity.INFO,
            message="루틴을 기반으로 작업 계획을 생성했습니다.",
            metadata_json={
                "routine_code": routine.code,
                "item_count": len(routine.routine_items),
                "mode": request.mode.value,
            },
        )
    )
    session.flush()
    session.refresh(job)
    return job


def create_job_event(session: Session, request: JobEventCreate) -> JobEvent:
    job = session.get(Job, request.job_id) if request.job_id else None
    if request.job_id and job is None:
        raise ResourceNotFoundError("작업을 찾을 수 없습니다.")

    job_item = (
        session.get(JobItem, request.job_item_id) if request.job_item_id else None
    )
    if request.job_item_id and job_item is None:
        raise ResourceNotFoundError("작업 물품을 찾을 수 없습니다.")
    if job_item and request.job_id != job_item.job_id:
        raise DomainValidationError("작업과 작업 물품의 조합이 일치하지 않습니다.")

    event = JobEvent(**request.model_dump())
    session.add(event)
    session.flush()
    session.refresh(event)
    return event


def get_job_events(session: Session, job_id: uuid.UUID) -> list[JobEvent]:
    return list(
        session.scalars(
            select(JobEvent)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at, JobEvent.id)
        )
    )
