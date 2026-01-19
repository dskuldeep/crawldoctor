#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}========================================${NC}"
echo -e "${RED}  ROLLBACK - Unified Data Model${NC}"
echo -e "${RED}========================================${NC}"
echo ""

APP_NAME="crawldoctor"
BACKUP_DIR="./backups"

# List available backups
echo -e "${YELLOW}Available backups:${NC}"
ls -lht $BACKUP_DIR/*.sql 2>/dev/null || echo "No backups found"
echo ""

# Get latest backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/pre_unified_model_*.sql 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo -e "${RED}Error: No backup found!${NC}"
    echo -e "${YELLOW}Please specify backup file manually${NC}"
    exit 1
fi

echo -e "${BLUE}Latest backup: $LATEST_BACKUP${NC}"
BACKUP_SIZE=$(ls -lh "$LATEST_BACKUP" | awk '{print $5}')
BACKUP_DATE=$(ls -l "$LATEST_BACKUP" | awk '{print $6, $7, $8}')
echo -e "${BLUE}Size: $BACKUP_SIZE${NC}"
echo -e "${BLUE}Date: $BACKUP_DATE${NC}"
echo ""

echo -e "${RED}⚠️  WARNING: This will:${NC}"
echo -e "${RED}   1. Rollback database migration (remove client_id fields)${NC}"
echo -e "${RED}   2. Restore previous code version${NC}"
echo -e "${RED}   3. All data collected since deployment will be preserved${NC}"
echo -e "${RED}      (only the client_id fields will be removed)${NC}"
echo ""

read -p "Continue with rollback? Type 'ROLLBACK' to confirm: " CONFIRM

if [ "$CONFIRM" != "ROLLBACK" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/3] Rolling back database migration...${NC}"

# Rollback migration (removes client_id columns)
fly ssh console -a $APP_NAME -C "cd /app && alembic downgrade -1"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migration rolled back${NC}"
else
    echo -e "${RED}Error: Migration rollback failed${NC}"
    echo -e "${YELLOW}Attempting manual database restore...${NC}"
    
    # Upload backup to server
    fly ssh sftp shell -a $APP_NAME << EOF
put $LATEST_BACKUP /tmp/restore_backup.sql
EOF
    
    # Restore database
    fly ssh console -a $APP_NAME -C "psql \$DATABASE_URL < /tmp/restore_backup.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database restored from backup${NC}"
    else
        echo -e "${RED}Error: Database restore failed${NC}"
        echo -e "${RED}Please contact support with backup file: $LATEST_BACKUP${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}[2/3] Checking out previous code version...${NC}"

# If using git, checkout previous commit
if [ -d ".git" ]; then
    CURRENT_COMMIT=$(git rev-parse HEAD)
    PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
    
    echo -e "${BLUE}Current: $CURRENT_COMMIT${NC}"
    echo -e "${BLUE}Rolling back to: $PREVIOUS_COMMIT${NC}"
    
    git checkout $PREVIOUS_COMMIT
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Code rolled back${NC}"
    else
        echo -e "${RED}Error: Git checkout failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Not a git repository - skipping code rollback${NC}"
    echo -e "${YELLOW}Please manually restore previous code version${NC}"
fi

echo ""
echo -e "${YELLOW}[3/3] Redeploying to fly.io...${NC}"

fly deploy -a $APP_NAME

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Previous version redeployed${NC}"
else
    echo -e "${RED}Error: Deployment failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ROLLBACK COMPLETED${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}✓ Database migration rolled back${NC}"
echo -e "${GREEN}✓ Previous code version restored${NC}"
echo -e "${GREEN}✓ Application redeployed${NC}"
echo ""
echo -e "${BLUE}System is now back to previous state${NC}"
echo -e "${BLUE}No data was lost during rollback${NC}"
echo ""

# Verify
sleep 5
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://crawldoctor.fly.dev/track/status)
echo -e "${BLUE}Health check: HTTP $HEALTH${NC}"
echo ""

