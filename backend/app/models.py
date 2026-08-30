from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.enums import (
    EventDevice,
    EventSeverity,
    JobItemStatus,
    JobMode,
    JobStatus,
    JobStep,
    RoutineType,
)


def enum_column(enum_class: type, name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=False,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    grid_position: Mapped[str | None] = mapped_column(String(20))
    robot_x: Mapped[float | None] = mapped_column(Float)
    robot_y: Mapped[float | None] = mapped_column(Float)
    robot_z: Mapped[float | None] = mapped_column(Float)
    robot_yaw: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    home_items: Mapped[list[Item]] = relationship(
        back_populates="home_location",
        foreign_keys="Item.home_location_id",
        passive_deletes=True,
    )
    routine_items: Mapped[list[RoutineItem]] = relationship(
        back_populates="target_location",
        foreign_keys="RoutineItem.target_location_id",
        passive_deletes=True,
    )
    source_job_items: Mapped[list[JobItem]] = relationship(
        back_populates="source_location",
        foreign_keys="JobItem.source_location_id",
        passive_deletes=True,
    )
    target_job_items: Mapped[list[JobItem]] = relationship(
        back_populates="target_location",
        foreign_keys="JobItem.target_location_id",
        passive_deletes=True,
    )


class Item(TimestampMixin, Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("length(trim(tag_id)) > 0", name="tag_id_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tag_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    home_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    home_location: Mapped[Location | None] = relationship(
        back_populates="home_items", foreign_keys=[home_location_id]
    )
    routine_items: Mapped[list[RoutineItem]] = relationship(
        back_populates="item", passive_deletes=True
    )
    job_items: Mapped[list[JobItem]] = relationship(
        back_populates="item", passive_deletes=True
    )


class Routine(TimestampMixin, Base):
    __tablename__ = "routines"
    __table_args__ = (
        CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint(
            "routine_type IN ('OUTING_PREP', 'RETURN_HOME')",
            name="routine_type_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    routine_type: Mapped[RoutineType] = mapped_column(
        enum_column(RoutineType, "routine_type"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    routine_items: Mapped[list[RoutineItem]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RoutineItem.sequence",
    )
    jobs: Mapped[list[Job]] = relationship(
        back_populates="routine", passive_deletes=True
    )


class RoutineItem(TimestampMixin, Base):
    __tablename__ = "routine_items"
    __table_args__ = (
        UniqueConstraint("routine_id", "item_id", name="uq_routine_items_routine_item"),
        UniqueConstraint(
            "routine_id", "sequence", name="uq_routine_items_routine_sequence"
        ),
        CheckConstraint("sequence > 0", name="sequence_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    routine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    routine: Mapped[Routine] = relationship(back_populates="routine_items")
    item: Mapped[Item] = relationship(back_populates="routine_items")
    target_location: Mapped[Location] = relationship(
        back_populates="routine_items", foreign_keys=[target_location_id]
    )


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        CheckConstraint("mode IN ('SIMULATION', 'REAL')", name="mode_allowed"),
        CheckConstraint(
            "status IN ('WAITING', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "current_step IN ('IDLE', 'PLAN', 'DETECT', 'PICK', 'MOVE', "
            "'PLACE', 'VERIFY', 'RECOVER', 'COMPLETE', 'ERROR')",
            name="current_step_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    routine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("routines.id", ondelete="SET NULL"), index=True
    )
    routine_code_snapshot: Mapped[str | None] = mapped_column(String(50))
    routine_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    mode: Mapped[JobMode] = mapped_column(
        enum_column(JobMode, "job_mode"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus, "job_status"),
        default=JobStatus.WAITING,
        server_default=JobStatus.WAITING.value,
        nullable=False,
        index=True,
    )
    current_step: Mapped[JobStep] = mapped_column(
        enum_column(JobStep, "job_step"),
        default=JobStep.IDLE,
        server_default=JobStep.IDLE.value,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)

    routine: Mapped[Routine | None] = relationship(back_populates="jobs")
    job_items: Mapped[list[JobItem]] = relationship(
        back_populates="job", passive_deletes=True, order_by="JobItem.sequence"
    )
    events: Mapped[list[JobEvent]] = relationship(
        back_populates="job", passive_deletes=True, order_by="JobEvent.created_at"
    )


class JobItem(TimestampMixin, Base):
    __tablename__ = "job_items"
    __table_args__ = (
        UniqueConstraint("job_id", "sequence", name="uq_job_items_job_sequence"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        CheckConstraint(
            "status IN ('WAITING', 'RUNNING', 'SUCCESS', 'FAILED', 'SKIPPED')",
            name="status_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True
    )
    target_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_id_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    source_location_code_snapshot: Mapped[str | None] = mapped_column(String(50))
    source_location_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    target_location_code_snapshot: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    target_location_name_snapshot: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    status: Mapped[JobItemStatus] = mapped_column(
        enum_column(JobItemStatus, "job_item_status"),
        default=JobItemStatus.WAITING,
        server_default=JobItemStatus.WAITING.value,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[Job] = relationship(back_populates="job_items")
    item: Mapped[Item | None] = relationship(back_populates="job_items")
    source_location: Mapped[Location | None] = relationship(
        back_populates="source_job_items", foreign_keys=[source_location_id]
    )
    target_location: Mapped[Location | None] = relationship(
        back_populates="target_job_items", foreign_keys=[target_location_id]
    )
    events: Mapped[list[JobEvent]] = relationship(
        back_populates="job_item",
        passive_deletes=True,
        order_by="JobEvent.created_at",
    )


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (
        CheckConstraint(
            "job_item_id IS NULL OR job_id IS NOT NULL",
            name="job_required_for_job_item",
        ),
        CheckConstraint(
            "step IS NULL OR step IN ('IDLE', 'PLAN', 'DETECT', 'PICK', 'MOVE', "
            "'PLACE', 'VERIFY', 'RECOVER', 'COMPLETE', 'ERROR')",
            name="step_allowed",
        ),
        CheckConstraint(
            "device IN ('SYSTEM', 'VISION', 'ARM', 'ESP32', 'RAZBOT')",
            name="device_allowed",
        ),
        CheckConstraint(
            "severity IN ('INFO', 'SUCCESS', 'WARNING', 'ERROR')",
            name="severity_allowed",
        ),
        Index("ix_job_events_job_created", "job_id", "created_at"),
        Index("ix_job_events_job_item_created", "job_item_id", "created_at"),
        Index("ix_job_events_event_type", "event_type"),
        Index("ix_job_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT")
    )
    job_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_items.id", ondelete="RESTRICT")
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    step: Mapped[JobStep | None] = mapped_column(enum_column(JobStep, "job_event_step"))
    device: Mapped[EventDevice] = mapped_column(
        enum_column(EventDevice, "event_device"), nullable=False
    )
    severity: Mapped[EventSeverity] = mapped_column(
        enum_column(EventSeverity, "event_severity"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[Job | None] = relationship(back_populates="events")
    job_item: Mapped[JobItem | None] = relationship(back_populates="events")
