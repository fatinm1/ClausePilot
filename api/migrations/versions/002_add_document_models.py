"""Add document processing models

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # Create documents table (SQLAlchemy will handle enum creation)
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "uploaded", "processing", "completed", "error", name="documentstatus"
            ),
            nullable=True,
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("output_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create processing_rules table
    op.create_table(
        "processing_rule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create processing_jobs table
    op.create_table(
        "processing_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_log", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["document.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for better performance
    op.create_index(op.f("ix_document_user_id"), "document", ["user_id"], unique=False)
    op.create_index(op.f("ix_document_status"), "document", ["status"], unique=False)
    op.create_index(
        op.f("ix_processing_rule_user_id"), "processing_rule", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_processing_job_document_id"),
        "processing_job",
        ["document_id"],
        unique=False,
    )


def downgrade():
    # Drop indexes
    op.drop_index(op.f("ix_processing_job_document_id"), table_name="processing_job")
    op.drop_index(op.f("ix_processing_rule_user_id"), table_name="processing_rule")
    op.drop_index(op.f("ix_document_status"), table_name="document")
    op.drop_index(op.f("ix_document_user_id"), table_name="document")

    # Drop tables
    op.drop_table("processing_job")
    op.drop_table("processing_rule")
    op.drop_table("document")

    # Drop enum (only if it exists)
    op.execute("DROP TYPE IF EXISTS documentstatus")
