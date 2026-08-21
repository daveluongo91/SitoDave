"""001 initial and evolution schema

Revision ID: 001_initial_and_evolution
Revises: 
Create Date: 2026-08-21 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_and_evolution"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabella contacts
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("first_name", sa.String(128), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(128), nullable=False, server_default=""),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("country", sa.String(64), nullable=True, server_default="IT"),
        sa.Column("language", sa.String(16), nullable=False, server_default="it"),
        sa.Column("first_source", sa.String(64), nullable=True),
        sa.Column("last_source", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new_lead"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("owner", sa.String(64), nullable=True, server_default="Davide Luongo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("last_contact_at", sa.String(32), nullable=True),
        sa.Column("next_followup_at", sa.String(32), nullable=True),
        sa.Column("customer_since", sa.String(32), nullable=True),
        sa.Column("total_spent_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_blacklisted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("blacklist_reason", sa.Text(), nullable=True),
        sa.Column("blacklisted_at", sa.String(32), nullable=True),
        sa.Column("privacy_consent", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("privacy_consent_at", sa.String(32), nullable=True),
        sa.Column("marketing_email_consent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("marketing_email_consent_at", sa.String(32), nullable=True),
        sa.Column("marketing_phone_consent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("marketing_phone_consent_at", sa.String(32), nullable=True),
        sa.Column("consent_version", sa.String(32), nullable=False, server_default="1.0"),
        sa.Column("consent_source", sa.String(128), nullable=True),
        sa.Column("consent_revoked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("consent_revoked_at", sa.String(32), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.String(32), nullable=True),
    )
    op.create_index("ix_contacts_email", "contacts", ["email"])
    op.create_index("ix_contacts_phone", "contacts", ["phone"])
    op.create_index("ix_contacts_status", "contacts", ["status"])
    op.create_index("ix_contacts_is_blacklisted", "contacts", ["is_blacklisted"])

    # 2. Tabella contact_interactions
    op.create_table(
        "contact_interactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="internal_note"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("workshop_or_trip_key", sa.String(64), nullable=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_contact_interactions_contact_id", "contact_interactions", ["contact_id"])
    op.create_index("ix_contact_interactions_type", "contact_interactions", ["type"])

    # 3. Tabella tags e contact_tags
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("color", sa.String(32), nullable=False, server_default="#38bdf8"),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_tags_name", "tags", ["name"])

    op.create_table(
        "contact_tags",
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # 4. Tabella background_jobs
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("started_at", sa.String(32), nullable=True),
        sa.Column("completed_at", sa.String(32), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_background_jobs_type", "background_jobs", ["type"])
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])

    # 5. Batch alter su workshops per aggiungere campi esperienza/viaggi
    with op.batch_alter_table("workshops") as batch_op:
        batch_op.add_column(sa.Column("experience_type", sa.String(32), nullable=False, server_default="workshop"))
        batch_op.add_column(sa.Column("template_version", sa.String(32), nullable=False, server_default="workshop-v1"))
        batch_op.add_column(sa.Column("country", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("destination", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("arrival_airport", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("currency", sa.String(16), nullable=False, server_default="EUR"))
        batch_op.add_column(sa.Column("flights_included", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("baggage_info", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("documents_required", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("passport_or_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("visa_required", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("insurance_info", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("min_participants", sa.Integer(), nullable=True, server_default="4"))
        batch_op.add_column(sa.Column("technical_operator", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("sales_liability", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("accommodation_type", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("room_type", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("single_supplement_cents", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("meals_included", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("transfers_info", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("weather_conditions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("physical_level", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("day_by_day_itinerary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("legal_notes", sa.Text(), nullable=True))

    # 6. Batch alter su bookings per collegare contact_id
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id"), nullable=True))

    # 7. Batch alter su users per OTP e codici recupero
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("otp_hash", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("otp_expires_at", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("otp_failed_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("otp_cooldown_until", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("otp_challenge_token", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("recovery_codes_hash", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_password_change_at", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_password_change_at")
        batch_op.drop_column("recovery_codes_hash")
        batch_op.drop_column("otp_challenge_token")
        batch_op.drop_column("otp_cooldown_until")
        batch_op.drop_column("otp_failed_attempts")
        batch_op.drop_column("otp_expires_at")
        batch_op.drop_column("otp_hash")

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_column("contact_id")

    with op.batch_alter_table("workshops") as batch_op:
        batch_op.drop_column("legal_notes")
        batch_op.drop_column("day_by_day_itinerary")
        batch_op.drop_column("physical_level")
        batch_op.drop_column("weather_conditions")
        batch_op.drop_column("transfers_info")
        batch_op.drop_column("meals_included")
        batch_op.drop_column("single_supplement_cents")
        batch_op.drop_column("room_type")
        batch_op.drop_column("accommodation_type")
        batch_op.drop_column("sales_liability")
        batch_op.drop_column("technical_operator")
        batch_op.drop_column("min_participants")
        batch_op.drop_column("insurance_info")
        batch_op.drop_column("visa_required")
        batch_op.drop_column("passport_or_id")
        batch_op.drop_column("documents_required")
        batch_op.drop_column("baggage_info")
        batch_op.drop_column("flights_included")
        batch_op.drop_column("currency")
        batch_op.drop_column("arrival_airport")
        batch_op.drop_column("destination")
        batch_op.drop_column("country")
        batch_op.drop_column("template_version")
        batch_op.drop_column("experience_type")

    op.drop_table("background_jobs")
    op.drop_table("contact_tags")
    op.drop_table("tags")
    op.drop_table("contact_interactions")
    op.drop_table("contacts")