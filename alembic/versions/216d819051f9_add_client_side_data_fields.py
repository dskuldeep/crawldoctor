"""add_client_side_data_fields

Revision ID: 216d819051f9
Revises: unified_client_id
Create Date: 2025-11-22 19:58:32.645915

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '216d819051f9'
down_revision = 'unified_client_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add client-side data fields to visit_sessions table
    op.add_column('visit_sessions', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_location_country', sa.String(100), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_timezone', sa.String(50), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_language', sa.String(50), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_screen_resolution', sa.String(50), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_viewport_size', sa.String(50), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_device_memory', sa.String(20), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_connection_type', sa.String(50), nullable=True))
    
    # Add client-side data fields to visits table
    op.add_column('visits', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visits', sa.Column('client_side_location_country', sa.String(100), nullable=True))
    op.add_column('visits', sa.Column('client_side_timezone', sa.String(50), nullable=True))
    op.add_column('visits', sa.Column('client_side_language', sa.String(50), nullable=True))
    op.add_column('visits', sa.Column('client_side_screen_resolution', sa.String(50), nullable=True))
    op.add_column('visits', sa.Column('client_side_viewport_size', sa.String(50), nullable=True))
    op.add_column('visits', sa.Column('client_side_device_memory', sa.String(20), nullable=True))
    op.add_column('visits', sa.Column('client_side_connection_type', sa.String(50), nullable=True))
    
    # Add client-side data fields to visit_events table
    op.add_column('visit_events', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_location_country', sa.String(100), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_timezone', sa.String(50), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_language', sa.String(50), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_screen_resolution', sa.String(50), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_viewport_size', sa.String(50), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_device_memory', sa.String(20), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_connection_type', sa.String(50), nullable=True))


def downgrade() -> None:
    # Remove client-side data fields from visit_events table
    op.drop_column('visit_events', 'client_side_connection_type')
    op.drop_column('visit_events', 'client_side_device_memory')
    op.drop_column('visit_events', 'client_side_viewport_size')
    op.drop_column('visit_events', 'client_side_screen_resolution')
    op.drop_column('visit_events', 'client_side_language')
    op.drop_column('visit_events', 'client_side_timezone')
    op.drop_column('visit_events', 'client_side_location_country')
    op.drop_column('visit_events', 'client_side_location_city')
    
    # Remove client-side data fields from visits table
    op.drop_column('visits', 'client_side_connection_type')
    op.drop_column('visits', 'client_side_device_memory')
    op.drop_column('visits', 'client_side_viewport_size')
    op.drop_column('visits', 'client_side_screen_resolution')
    op.drop_column('visits', 'client_side_language')
    op.drop_column('visits', 'client_side_timezone')
    op.drop_column('visits', 'client_side_location_country')
    op.drop_column('visits', 'client_side_location_city')
    
    # Remove client-side data fields from visit_sessions table
    op.drop_column('visit_sessions', 'client_side_connection_type')
    op.drop_column('visit_sessions', 'client_side_device_memory')
    op.drop_column('visit_sessions', 'client_side_viewport_size')
    op.drop_column('visit_sessions', 'client_side_screen_resolution')
    op.drop_column('visit_sessions', 'client_side_language')
    op.drop_column('visit_sessions', 'client_side_timezone')
    op.drop_column('visit_sessions', 'client_side_location_country')
    op.drop_column('visit_sessions', 'client_side_location_city')
