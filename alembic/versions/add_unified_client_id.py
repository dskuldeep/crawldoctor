"""Add unified client_id for user tracking across sessions

Revision ID: unified_client_id
Revises: 73f8498762a0
Create Date: 2025-11-22

This migration adds a persistent client_id field to unify user tracking
across multiple sessions, domains, and time periods.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'unified_client_id'
down_revision = '73f8498762a0'
branch_labels = None
depends_on = None


def upgrade():
    """Add client_id to all tracking tables for unified user identity."""
    
    # Add client_id to visit_sessions table
    op.add_column('visit_sessions', sa.Column('client_id', sa.String(64), nullable=True))
    op.create_index('ix_visit_sessions_client_id', 'visit_sessions', ['client_id'])
    
    # Add client_id to visits table
    op.add_column('visits', sa.Column('client_id', sa.String(64), nullable=True))
    op.create_index('ix_visits_client_id', 'visits', ['client_id'])
    
    # Add client_id to visit_events table
    op.add_column('visit_events', sa.Column('client_id', sa.String(64), nullable=True))
    op.create_index('ix_visit_events_client_id', 'visit_events', ['client_id'])
    
    # Create composite indexes for common queries
    op.create_index(
        'ix_visit_sessions_client_id_last_visit',
        'visit_sessions',
        ['client_id', 'last_visit']
    )
    op.create_index(
        'ix_visits_client_id_timestamp',
        'visits',
        ['client_id', 'timestamp']
    )
    op.create_index(
        'ix_visit_events_client_id_timestamp',
        'visit_events',
        ['client_id', 'timestamp']
    )


def downgrade():
    """Remove client_id fields and indexes."""
    
    # Drop composite indexes
    op.drop_index('ix_visit_events_client_id_timestamp', 'visit_events')
    op.drop_index('ix_visits_client_id_timestamp', 'visits')
    op.drop_index('ix_visit_sessions_client_id_last_visit', 'visit_sessions')
    
    # Drop client_id indexes
    op.drop_index('ix_visit_events_client_id', 'visit_events')
    op.drop_index('ix_visits_client_id', 'visits')
    op.drop_index('ix_visit_sessions_client_id', 'visit_sessions')
    
    # Drop client_id columns
    op.drop_column('visit_events', 'client_id')
    op.drop_column('visits', 'client_id')
    op.drop_column('visit_sessions', 'client_id')

