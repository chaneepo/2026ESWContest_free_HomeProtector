import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.enums import (
    EventDevice,
    EventSeverity,
    JobItemStatus,
    JobMode,
    JobStatus,
    JobStep,
    RoutineType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NamedModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("이름은 비어 있을 수 없습니다.")
        return value


class LocationCreate(NamedModel):
    code: str = Field(min_length=1, max_length=50)
    grid_position: str | None = Field(default=None, max_length=20)
    robot_x: float | None = None
    robot_y: float | None = None
    robot_z: float | None = None
    robot_yaw: float | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("위치 코드는 비어 있을 수 없습니다.")
        return value


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    grid_position: str | None = Field(default=None, max_length=20)
    robot_x: float | None = None
    robot_y: float | None = None
    robot_z: float | None = None
    robot_yaw: float | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("이름은 비어 있을 수 없습니다.")
        return value


class LocationRead(LocationCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ItemCreate(NamedModel):
    tag_id: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=100)
    home_location_id: uuid.UUID | None = None
    is_active: bool = True

    @field_validator("tag_id")
    @classmethod
    def normalize_tag_id(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("태그 ID는 비어 있을 수 없습니다.")
        return value

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("분류는 비어 있을 수 없습니다.")
        return value


class ItemUpdate(BaseModel):
    tag_id: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    home_location_id: uuid.UUID | None = None
    is_active: bool | None = None

    @field_validator("tag_id", "name", "category")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("문자열 값은 비어 있을 수 없습니다.")
        return value


class ItemRead(ItemCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RoutineCreate(NamedModel):
    code: str = Field(min_length=1, max_length=50)
    routine_type: RoutineType
    description: str | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("루틴 코드는 비어 있을 수 없습니다.")
        return value


class RoutineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("이름은 비어 있을 수 없습니다.")
        return value


class RoutineRead(RoutineCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RoutineItemCreate(BaseModel):
    routine_id: uuid.UUID
    item_id: uuid.UUID
    target_location_id: uuid.UUID
    sequence: int = Field(gt=0)
    is_required: bool = True


class RoutineItemRead(RoutineItemCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class JobCreate(BaseModel):
    routine_id: uuid.UUID
    mode: JobMode = JobMode.SIMULATION


class JobItemRead(ORMModel):
    id: uuid.UUID
    job_id: uuid.UUID
    item_id: uuid.UUID | None
    sequence: int
    source_location_id: uuid.UUID | None
    target_location_id: uuid.UUID | None
    item_name_snapshot: str
    tag_id_snapshot: str
    source_location_code_snapshot: str | None
    source_location_name_snapshot: str | None
    target_location_code_snapshot: str
    target_location_name_snapshot: str
    status: JobItemStatus
    retry_count: int = Field(ge=0)
    failure_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobRead(ORMModel):
    id: uuid.UUID
    routine_id: uuid.UUID | None
    routine_code_snapshot: str | None
    routine_name_snapshot: str | None
    mode: JobMode
    status: JobStatus
    current_step: JobStep
    started_at: datetime | None
    completed_at: datetime | None
    retry_count: int = Field(ge=0)
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    job_items: list[JobItemRead] = Field(default_factory=list)


class JobEventCreate(BaseModel):
    job_id: uuid.UUID | None = None
    job_item_id: uuid.UUID | None = None
    event_type: str = Field(min_length=1, max_length=100)
    step: JobStep | None = None
    device: EventDevice
    severity: EventSeverity
    message: str = Field(min_length=1)
    metadata_json: dict[str, Any] | None = None

    @field_validator("event_type", "message")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("이벤트 값은 비어 있을 수 없습니다.")
        return value


class JobEventRead(JobEventCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime


class HealthRead(BaseModel):
    status: str
    database: str
