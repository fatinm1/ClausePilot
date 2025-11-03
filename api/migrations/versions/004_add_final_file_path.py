"""add final_file_path to document

Revision ID: 004_add_final_file_path
Revises: 003_add_rbac
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_final_file_path'
down_revision = '003_add_rbac'
branch_labels = None
depends_on = None


def upgrade():
    # Add final_file_path column to document table
    op.add_column('document', sa.Column('final_file_path', sa.String(length=500), nullable=True))


def downgrade():
    # Remove final_file_path column from document table
    op.drop_column('document', 'final_file_path')

