"""add_updated_at_to_processing_rule

Revision ID: a399165ddde8
Revises: de35d2855092
Create Date: 2025-08-27 17:26:13.998584

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a399165ddde8"
down_revision = "de35d2855092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add updated_at column to processing_rule table
    op.add_column(
        "processing_rule", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    # Set existing records to have updated_at = created_at
    op.execute(
        "UPDATE processing_rule SET updated_at = created_at WHERE updated_at IS NULL"
    )

    # Make the column not nullable after setting values
    op.alter_column("processing_rule", "updated_at", nullable=False)


def downgrade() -> None:
    # Remove updated_at column from processing_rule table
    op.drop_column("processing_rule", "updated_at")
