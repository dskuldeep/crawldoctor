"""add_event_attribution_fields

Revision ID: 9f3c0f9a2b1e
Revises: 349ee6677812
Create Date: 2026-01-19 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f3c0f9a2b1e'
down_revision = '349ee6677812'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check and add columns only if they don't exist (idempotent)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('visit_events')]
    
    if 'page_domain' not in columns:
        op.add_column('visit_events', sa.Column('page_domain', sa.String(length=200), nullable=True))
    if 'referrer_domain' not in columns:
        op.add_column('visit_events', sa.Column('referrer_domain', sa.String(length=200), nullable=True))
    if 'tracking_id' not in columns:
        op.add_column('visit_events', sa.Column('tracking_id', sa.String(length=100), nullable=True))
    if 'source' not in columns:
        op.add_column('visit_events', sa.Column('source', sa.String(length=100), nullable=True))
    if 'medium' not in columns:
        op.add_column('visit_events', sa.Column('medium', sa.String(length=100), nullable=True))
    if 'campaign' not in columns:
        op.add_column('visit_events', sa.Column('campaign', sa.String(length=100), nullable=True))

    # Create indexes concurrently to avoid blocking large tables.
    # Must run outside a transaction.
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_page_domain ON visit_events (page_domain)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_referrer_domain ON visit_events (referrer_domain)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_tracking_id ON visit_events (tracking_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_source ON visit_events (source)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_medium ON visit_events (medium)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_visit_events_campaign ON visit_events (campaign)")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_campaign")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_medium")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_source")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_tracking_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_referrer_domain")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_visit_events_page_domain")

    op.drop_column('visit_events', 'campaign')
    op.drop_column('visit_events', 'medium')
    op.drop_column('visit_events', 'source')
    op.drop_column('visit_events', 'tracking_id')
    op.drop_column('visit_events', 'referrer_domain')
    op.drop_column('visit_events', 'page_domain')
