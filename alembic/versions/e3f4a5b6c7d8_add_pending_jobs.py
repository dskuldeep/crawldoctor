"""add pending_jobs table for durable job queue

Revision ID: e3f4a5b6c7d8
Revises: add_ip_enrichment
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'e3f4a5b6c7d8'
down_revision = 'add_ip_enrichment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pending_jobs',
        sa.Column('job_name', sa.String(100), nullable=False),
        sa.Column('dedup_key', sa.String(255), nullable=False),
        sa.Column('payload', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('job_name', 'dedup_key'),
    )


def downgrade() -> None:
    op.drop_table('pending_jobs')
