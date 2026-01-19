"""fix_asn_type

Revision ID: fix_asn_type
Revises: df71d88a7152
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_asn_type'
down_revision = 'df71d88a7152'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change asn column from Integer to String(50) in visit_sessions
    # Using 'USING cast(asn as varchar)' for Postgres compatibility
    op.execute('ALTER TABLE visit_sessions ALTER COLUMN asn TYPE VARCHAR(50) USING cast(asn as varchar)')


def downgrade() -> None:
    # Change back to Integer (might fail if data contains non-numeric strings)
    op.execute('ALTER TABLE visit_sessions ALTER COLUMN asn TYPE INTEGER USING cast(asn as integer)')
