"""Normalize constraint names created by the initial development revision.

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260829_0002"
down_revision: str | None = "20260829_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RENAMES = (
    (
        "locations",
        "ck_locations_ck_locations_code_not_empty",
        "ck_locations_code_not_empty",
    ),
    (
        "locations",
        "ck_locations_ck_locations_name_not_empty",
        "ck_locations_name_not_empty",
    ),
    ("items", "ck_items_ck_items_tag_id_not_empty", "ck_items_tag_id_not_empty"),
    ("items", "ck_items_ck_items_name_not_empty", "ck_items_name_not_empty"),
    (
        "routines",
        "ck_routines_ck_routines_code_not_empty",
        "ck_routines_code_not_empty",
    ),
    (
        "routines",
        "ck_routines_ck_routines_name_not_empty",
        "ck_routines_name_not_empty",
    ),
    ("routines", "ck_routines_routine_type", "ck_routines_routine_type_allowed"),
    (
        "routine_items",
        "ck_routine_items_ck_routine_items_sequence_positive",
        "ck_routine_items_sequence_positive",
    ),
    (
        "jobs",
        "ck_jobs_ck_jobs_retry_count_non_negative",
        "ck_jobs_retry_count_non_negative",
    ),
    ("jobs", "ck_jobs_job_mode", "ck_jobs_mode_allowed"),
    ("jobs", "ck_jobs_job_status", "ck_jobs_status_allowed"),
    ("jobs", "ck_jobs_job_step", "ck_jobs_current_step_allowed"),
    (
        "job_items",
        "ck_job_items_ck_job_items_sequence_positive",
        "ck_job_items_sequence_positive",
    ),
    (
        "job_items",
        "ck_job_items_ck_job_items_retry_count_non_negative",
        "ck_job_items_retry_count_non_negative",
    ),
    (
        "job_items",
        "ck_job_items_job_item_status",
        "ck_job_items_status_allowed",
    ),
    (
        "job_events",
        "ck_job_events_ck_job_events_job_required_for_job_item",
        "ck_job_events_job_required_for_job_item",
    ),
    (
        "job_events",
        "ck_job_events_job_event_step",
        "ck_job_events_step_allowed",
    ),
    (
        "job_events",
        "ck_job_events_event_device",
        "ck_job_events_device_allowed",
    ),
    (
        "job_events",
        "ck_job_events_event_severity",
        "ck_job_events_severity_allowed",
    ),
)


def rename_if_present(table: str, old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old_name}' AND conrelid = '{table}'::regclass
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{new_name}' AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old_name} TO {new_name};
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    for table, old_name, new_name in RENAMES:
        rename_if_present(table, old_name, new_name)


def downgrade() -> None:
    # This compatibility revision changes names only. Keeping the normalized
    # names is safe when moving back to the foundational schema revision.
    pass
