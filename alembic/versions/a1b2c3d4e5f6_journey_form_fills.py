"""journey_form_fills and form_fill_count

Revision ID: a1b2c3d4e5f6
Revises: 7e0ce48e2311
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = 'a1b2c3d4e5f6'
down_revision = '7e0ce48e2311'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('journey_summaries', sa.Column('form_fill_count', sa.Integer(), nullable=True, server_default='0'))
    op.create_table(
        'journey_form_fills',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False, index=True),
        sa.Column('visit_event_id', sa.BigInteger(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('page_url', sa.String(length=2000), nullable=True),
        sa.Column('path', sa.String(length=1000), nullable=True),
        sa.Column('form_values', JSONB, nullable=True),
        sa.Column('filled_fields', sa.Integer(), nullable=True),
        sa.Column('form_id', sa.String(length=255), nullable=True),
        sa.Column('form_action', sa.String(length=2000), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_journey_form_fills_client_timestamp', 'journey_form_fills', ['client_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_journey_form_fills_client_timestamp', table_name='journey_form_fills')
    op.drop_table('journey_form_fills')
    op.drop_column('journey_summaries', 'form_fill_count')
