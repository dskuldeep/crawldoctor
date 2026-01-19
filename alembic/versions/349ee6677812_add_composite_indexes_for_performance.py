"""add_composite_indexes_for_performance

Revision ID: 349ee6677812
Revises: fix_asn_type
Create Date: 2026-01-19 20:26:34.415033

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '349ee6677812'
down_revision = 'fix_asn_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create composite indexes for high-performance user journey queries
    # These indexes prevent full table scans and memory sorting when fetching user history
    op.create_index(
        'idx_visits_client_timestamp', 'visits', ['client_id', 'timestamp'], 
        postgresql_ops={'timestamp': 'DESC'}
    )
    op.create_index(
        'idx_events_client_timestamp', 'visit_events', ['client_id', 'timestamp'], 
        postgresql_ops={'timestamp': 'DESC'}
    )
    op.create_index(
        'idx_sessions_client_last_visit', 'visit_sessions', ['client_id', 'last_visit'], 
        postgresql_ops={'last_visit': 'DESC'}
    )


def downgrade() -> None:
    op.drop_index('idx_sessions_client_last_visit', table_name='visit_sessions')
    op.drop_index('idx_events_client_timestamp', table_name='visit_events')
    op.drop_index('idx_visits_client_timestamp', table_name='visits')
