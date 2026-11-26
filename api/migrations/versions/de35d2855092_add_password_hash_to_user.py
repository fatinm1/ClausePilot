"""add_password_hash_to_user

Revision ID: de35d2855092
Revises: 003
Create Date: 2025-08-27 14:03:07.392174

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "de35d2855092"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash column to user table
    op.add_column("user", sa.Column("password_hash", sa.String(255), nullable=True))

    # Set a default password hash for existing users (they'll need to reset passwords)
    op.execute(
        "UPDATE \"user\" SET password_hash = 'default_hash_needs_reset' WHERE password_hash IS NULL"
    )

    # Make the column not nullable
    op.alter_column("user", "password_hash", nullable=False)


def downgrade() -> None:
    # Remove password_hash column
    op.drop_column("user", "password_hash")
