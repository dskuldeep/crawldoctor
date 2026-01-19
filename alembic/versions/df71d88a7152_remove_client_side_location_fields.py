"""remove_client_side_location_fields

Revision ID: df71d88a7152
Revises: 216d819051f9
Create Date: 2025-11-22 20:35:56.662791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df71d88a7152'
down_revision = '216d819051f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove client_side_location_city and client_side_location_country from all tables
    op.drop_column('visit_sessions', 'client_side_location_city')
    op.drop_column('visit_sessions', 'client_side_location_country')
    
    op.drop_column('visits', 'client_side_location_city')
    op.drop_column('visits', 'client_side_location_country')
    
    op.drop_column('visit_events', 'client_side_location_city')
    op.drop_column('visit_events', 'client_side_location_country')


def downgrade() -> None:
    # Re-add the columns if we need to rollback
    op.add_column('visit_sessions', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visit_sessions', sa.Column('client_side_location_country', sa.String(2), nullable=True))
    
    op.add_column('visits', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visits', sa.Column('client_side_location_country', sa.String(2), nullable=True))
    
    op.add_column('visit_events', sa.Column('client_side_location_city', sa.String(100), nullable=True))
    op.add_column('visit_events', sa.Column('client_side_location_country', sa.String(2), nullable=True))
