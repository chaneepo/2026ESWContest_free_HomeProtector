"""Create the seven CARE-PACK core tables.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_type(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=False,
    )


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("grid_position", sa.String(length=20), nullable=True),
        sa.Column("robot_x", sa.Float(), nullable=True),
        sa.Column("robot_y", sa.Float(), nullable=True),
        sa.Column("robot_z", sa.Float(), nullable=True),
        sa.Column("robot_yaw", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
        sa.UniqueConstraint("code", name="uq_locations_code"),
        sa.UniqueConstraint("name", name="uq_locations_name"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("home_location_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length(trim(tag_id)) > 0", name="tag_id_not_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.ForeignKeyConstraint(
            ["home_location_id"],
            ["locations.id"],
            name="fk_items_home_location_id_locations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_items"),
        sa.UniqueConstraint("tag_id", name="uq_items_tag_id"),
    )

    op.create_table(
        "routines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "routine_type",
            enum_type("routine_type", ("OUTING_PREP", "RETURN_HOME")),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.CheckConstraint(
            "routine_type IN ('OUTING_PREP', 'RETURN_HOME')",
            name="routine_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_routines"),
        sa.UniqueConstraint("code", name="uq_routines_code"),
    )

    op.create_table(
        "routine_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("routine_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("target_location_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default="true", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("sequence > 0", name="sequence_positive"),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_routine_items_item_id_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["routine_id"],
            ["routines.id"],
            name="fk_routine_items_routine_id_routines",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_location_id"],
            ["locations.id"],
            name="fk_routine_items_target_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_routine_items"),
        sa.UniqueConstraint(
            "routine_id", "item_id", name="uq_routine_items_routine_item"
        ),
        sa.UniqueConstraint(
            "routine_id", "sequence", name="uq_routine_items_routine_sequence"
        ),
    )
    op.create_index("ix_routine_items_item_id", "routine_items", ["item_id"])
    op.create_index("ix_routine_items_routine_id", "routine_items", ["routine_id"])
    op.create_index(
        "ix_routine_items_target_location_id",
        "routine_items",
        ["target_location_id"],
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("routine_id", sa.Uuid(), nullable=True),
        sa.Column("routine_code_snapshot", sa.String(length=50), nullable=True),
        sa.Column("routine_name_snapshot", sa.String(length=100), nullable=True),
        sa.Column(
            "mode",
            enum_type("job_mode", ("SIMULATION", "REAL")),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum_type(
                "job_status", ("WAITING", "RUNNING", "SUCCESS", "FAILED", "STOPPED")
            ),
            server_default="WAITING",
            nullable=False,
        ),
        sa.Column(
            "current_step",
            enum_type(
                "job_step",
                (
                    "IDLE",
                    "PLAN",
                    "DETECT",
                    "PICK",
                    "MOVE",
                    "PLACE",
                    "VERIFY",
                    "RECOVER",
                    "COMPLETE",
                    "ERROR",
                ),
            ),
            server_default="IDLE",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        sa.CheckConstraint("mode IN ('SIMULATION', 'REAL')", name="mode_allowed"),
        sa.CheckConstraint(
            "status IN ('WAITING', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "current_step IN ('IDLE', 'PLAN', 'DETECT', 'PICK', 'MOVE', "
            "'PLACE', 'VERIFY', 'RECOVER', 'COMPLETE', 'ERROR')",
            name="current_step_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["routine_id"],
            ["routines.id"],
            name="fk_jobs_routine_id_routines",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
    )
    op.create_index("ix_jobs_routine_id", "jobs", ["routine_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "job_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("source_location_id", sa.Uuid(), nullable=True),
        sa.Column("target_location_id", sa.Uuid(), nullable=True),
        sa.Column("item_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("tag_id_snapshot", sa.String(length=50), nullable=False),
        sa.Column("source_location_code_snapshot", sa.String(length=50), nullable=True),
        sa.Column(
            "source_location_name_snapshot", sa.String(length=100), nullable=True
        ),
        sa.Column(
            "target_location_code_snapshot", sa.String(length=50), nullable=False
        ),
        sa.Column(
            "target_location_name_snapshot", sa.String(length=100), nullable=False
        ),
        sa.Column(
            "status",
            enum_type(
                "job_item_status",
                ("WAITING", "RUNNING", "SUCCESS", "FAILED", "SKIPPED"),
            ),
            server_default="WAITING",
            nullable=False,
        ),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("sequence > 0", name="sequence_positive"),
        sa.CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        sa.CheckConstraint(
            "status IN ('WAITING', 'RUNNING', 'SUCCESS', 'FAILED', 'SKIPPED')",
            name="status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_job_items_item_id_items",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_items_job_id_jobs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["locations.id"],
            name="fk_job_items_source_location_id_locations",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_location_id"],
            ["locations.id"],
            name="fk_job_items_target_location_id_locations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_items"),
        sa.UniqueConstraint("job_id", "sequence", name="uq_job_items_job_sequence"),
    )
    op.create_index("ix_job_items_item_id", "job_items", ["item_id"])
    op.create_index("ix_job_items_job_id", "job_items", ["job_id"])
    op.create_index(
        "ix_job_items_source_location_id", "job_items", ["source_location_id"]
    )
    op.create_index("ix_job_items_status", "job_items", ["status"])
    op.create_index(
        "ix_job_items_target_location_id", "job_items", ["target_location_id"]
    )

    op.create_table(
        "job_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("job_item_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "step",
            enum_type(
                "job_event_step",
                (
                    "IDLE",
                    "PLAN",
                    "DETECT",
                    "PICK",
                    "MOVE",
                    "PLACE",
                    "VERIFY",
                    "RECOVER",
                    "COMPLETE",
                    "ERROR",
                ),
            ),
            nullable=True,
        ),
        sa.Column(
            "device",
            enum_type("event_device", ("SYSTEM", "VISION", "ARM", "ESP32", "RAZBOT")),
            nullable=False,
        ),
        sa.Column(
            "severity",
            enum_type("event_severity", ("INFO", "SUCCESS", "WARNING", "ERROR")),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "job_item_id IS NULL OR job_id IS NOT NULL",
            name="job_required_for_job_item",
        ),
        sa.CheckConstraint(
            "step IS NULL OR step IN ('IDLE', 'PLAN', 'DETECT', 'PICK', 'MOVE', "
            "'PLACE', 'VERIFY', 'RECOVER', 'COMPLETE', 'ERROR')",
            name="step_allowed",
        ),
        sa.CheckConstraint(
            "device IN ('SYSTEM', 'VISION', 'ARM', 'ESP32', 'RAZBOT')",
            name="device_allowed",
        ),
        sa.CheckConstraint(
            "severity IN ('INFO', 'SUCCESS', 'WARNING', 'ERROR')",
            name="severity_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_events_job_id_jobs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_item_id"],
            ["job_items.id"],
            name="fk_job_events_job_item_id_job_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_events"),
    )
    op.create_index("ix_job_events_created_at", "job_events", ["created_at"])
    op.create_index("ix_job_events_event_type", "job_events", ["event_type"])
    op.create_index("ix_job_events_job_created", "job_events", ["job_id", "created_at"])
    op.create_index(
        "ix_job_events_job_item_created",
        "job_events",
        ["job_item_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("job_events")
    op.drop_table("job_items")
    op.drop_table("jobs")
    op.drop_table("routine_items")
    op.drop_table("routines")
    op.drop_table("items")
    op.drop_table("locations")
