"""Add role-based access control

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type first
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'USER')")

    # Add role and is_active columns to user table
    op.add_column(
        "user",
        sa.Column(
            "role",
            postgresql.ENUM("ADMIN", "USER", name="userrole"),
            nullable=True,
            default="USER",
        ),
    )
    op.add_column(
        "user", sa.Column("is_active", sa.Boolean(), nullable=True, default=True)
    )

    # Add is_global column to processing_rule table
    op.add_column(
        "processing_rule",
        sa.Column("is_global", sa.Boolean(), nullable=True, default=True),
    )

    # Update existing data
    op.execute("UPDATE \"user\" SET role = 'USER', is_active = true WHERE role IS NULL")
    op.execute("UPDATE processing_rule SET is_global = true WHERE is_global IS NULL")

    # Make columns not nullable after setting defaults
    op.alter_column("user", "role", nullable=False)
    op.alter_column("user", "is_active", nullable=False)
    op.alter_column("processing_rule", "is_global", nullable=False)


def downgrade():
    # Remove columns
    op.drop_column("processing_rule", "is_global")
    op.drop_column("user", "is_active")
    op.drop_column("user", "role")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS userrole")
