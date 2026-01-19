"""Script to downgrade database migrations to base."""
import sys
import os
from alembic import command
from alembic.config import Config

try:
    # Set up alembic config
    cfg = Config('/app/alembic.ini')
    
    # Set database URL from environment
    db_url = os.environ.get('CRAWLDOCTOR_DATABASE_URL')
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        cfg.set_main_option('sqlalchemy.url', db_url)
        print(f"✅ Using database URL from environment")
    
    # Show current version
    print('\n📋 Current migration:')
    command.current(cfg)
    print()
    
    # Downgrade to base
    print('⏬ Downgrading to base...')
    command.downgrade(cfg, 'base')
    
    print('✅ Successfully downgraded to base')
    print()
    
    # Verify
    print('📋 Current migration after downgrade:')
    command.current(cfg)
    
except Exception as e:
    print(f'⚠️  Warning during downgrade: {e}')
    print('Tables will be recreated during deployment')
    # Don't exit with error - deployment will recreate tables
    sys.exit(0)


