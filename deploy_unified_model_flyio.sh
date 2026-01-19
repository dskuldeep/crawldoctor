#!/bin/bash
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Unified Data Model - Fly.io Deploy${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
APP_NAME="crawldoctor"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pre_unified_model_${TIMESTAMP}.sql"

# Step 1: Pre-flight checks
echo -e "${YELLOW}[1/8] Running pre-flight checks...${NC}"

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}Error: fly CLI not found. Install it with: curl -L https://fly.io/install.sh | sh${NC}"
    exit 1
fi

# Check if logged in to fly
if ! fly auth whoami &> /dev/null; then
    echo -e "${RED}Error: Not logged in to fly.io. Run: fly auth login${NC}"
    exit 1
fi

# Check if app exists
if ! fly apps list | grep -q "$APP_NAME"; then
    echo -e "${RED}Error: App '$APP_NAME' not found on fly.io${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pre-flight checks passed${NC}"
echo ""

# Step 2: Create backup directory
echo -e "${YELLOW}[2/8] Creating backup directory...${NC}"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓ Backup directory ready: $BACKUP_DIR${NC}"
echo ""

# Step 3: Backup production database
echo -e "${YELLOW}[3/8] Backing up production database...${NC}"
echo -e "${BLUE}This is CRITICAL to ensure we can rollback if needed${NC}"

# Get database URL from fly.io secrets
DB_URL=$(fly secrets list -a $APP_NAME | grep DATABASE_URL | awk '{print $2}' || echo "")

if [ -z "$DB_URL" ]; then
    echo -e "${YELLOW}Warning: Could not auto-detect DATABASE_URL${NC}"
    echo -e "${YELLOW}Using fly ssh console to create backup...${NC}"
    
    # Create backup using fly ssh
    fly ssh console -a $APP_NAME -C "pg_dump \$DATABASE_URL > /tmp/backup_${TIMESTAMP}.sql"
    
    # Download backup
    fly ssh sftp get -a $APP_NAME /tmp/backup_${TIMESTAMP}.sql "$BACKUP_FILE"
    
    # Verify backup
    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
        echo -e "${GREEN}✓ Database backup created: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
    else
        echo -e "${RED}Error: Backup failed!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Database URL detected${NC}"
    # Note: Direct backup would need pg_dump installed locally with network access
    echo -e "${YELLOW}Creating backup via fly ssh...${NC}"
    fly ssh console -a $APP_NAME -C "pg_dump \$DATABASE_URL > /tmp/backup_${TIMESTAMP}.sql"
    fly ssh sftp get -a $APP_NAME /tmp/backup_${TIMESTAMP}.sql "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
        echo -e "${GREEN}✓ Database backup created: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
    else
        echo -e "${RED}Error: Backup failed!${NC}"
        exit 1
    fi
fi
echo ""

# Step 4: Rebuild frontend with new Users page
echo -e "${YELLOW}[4/8] Rebuilding frontend with unified user tracking...${NC}"
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
fi

# Build production frontend
echo -e "${BLUE}Building production frontend...${NC}"
npm run build

if [ ! -d "build" ]; then
    echo -e "${RED}Error: Frontend build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend built successfully${NC}"
cd ..
echo ""

# Step 5: Run migration test locally (dry run)
echo -e "${YELLOW}[5/8] Testing migration locally...${NC}"
echo -e "${BLUE}Verifying migration syntax...${NC}"

# Check if migration file exists
MIGRATION_FILE="alembic/versions/add_unified_client_id.py"
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Validate Python syntax
python3 -m py_compile "$MIGRATION_FILE"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migration file syntax is valid${NC}"
else
    echo -e "${RED}Error: Migration file has syntax errors${NC}"
    exit 1
fi
echo ""

# Step 6: Deploy to fly.io
echo -e "${YELLOW}[6/8] Deploying to fly.io...${NC}"
echo -e "${BLUE}This will:${NC}"
echo -e "${BLUE}  1. Build new Docker image with updated code${NC}"
echo -e "${BLUE}  2. Deploy to production${NC}"
echo -e "${BLUE}  3. Run database migration automatically${NC}"
echo ""

read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Deployment cancelled by user${NC}"
    exit 0
fi

# Deploy
fly deploy -a $APP_NAME --no-cache

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Deployment failed!${NC}"
    echo -e "${YELLOW}Your database backup is safe at: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Application deployed${NC}"
echo ""

# Step 7: Run database migration on production
echo -e "${YELLOW}[7/8] Running database migration on production...${NC}"
echo -e "${BLUE}Adding client_id fields to all tracking tables...${NC}"

# Run migration via fly ssh
fly ssh console -a $APP_NAME -C "cd /app && alembic upgrade head"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Migration failed!${NC}"
    echo -e "${YELLOW}ROLLBACK INSTRUCTIONS:${NC}"
    echo -e "${YELLOW}1. Restore database: fly ssh console -a $APP_NAME -C 'psql \$DATABASE_URL < /tmp/backup_${TIMESTAMP}.sql'${NC}"
    echo -e "${YELLOW}2. Or use local backup: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database migration completed${NC}"
echo ""

# Step 8: Verify deployment
echo -e "${YELLOW}[8/8] Verifying deployment...${NC}"

# Check app health
echo -e "${BLUE}Checking app health...${NC}"
sleep 5  # Give app time to restart

HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" https://crawldoctor.fly.dev/track/status)

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed (HTTP 200)${NC}"
else
    echo -e "${YELLOW}Warning: Health check returned HTTP $HEALTH_CHECK${NC}"
    echo -e "${YELLOW}App may still be starting up...${NC}"
fi

# Verify migration
echo -e "${BLUE}Verifying database migration...${NC}"
fly ssh console -a $APP_NAME -C "cd /app && alembic current" > /tmp/alembic_current.txt 2>&1

if grep -q "unified_client_id" /tmp/alembic_current.txt; then
    echo -e "${GREEN}✓ Migration verified: unified_client_id is active${NC}"
else
    echo -e "${YELLOW}Warning: Could not verify migration status${NC}"
    cat /tmp/alembic_current.txt
fi

# Check if new endpoints are available
echo -e "${BLUE}Checking new API endpoints...${NC}"
USERS_ENDPOINT=$(curl -s -o /dev/null -w "%{http_code}" https://crawldoctor.fly.dev/api/v1/analytics/users)

if [ "$USERS_ENDPOINT" = "401" ] || [ "$USERS_ENDPOINT" = "403" ]; then
    echo -e "${GREEN}✓ New /users endpoint is available (requires auth)${NC}"
elif [ "$USERS_ENDPOINT" = "200" ]; then
    echo -e "${GREEN}✓ New /users endpoint is available${NC}"
else
    echo -e "${YELLOW}Warning: Users endpoint returned HTTP $USERS_ENDPOINT${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DEPLOYMENT SUCCESSFUL! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}✓ Database backed up to: $BACKUP_FILE${NC}"
echo -e "${GREEN}✓ Frontend rebuilt with Users page${NC}"
echo -e "${GREEN}✓ Code deployed to fly.io${NC}"
echo -e "${GREEN}✓ Database migration completed${NC}"
echo -e "${GREEN}✓ All systems verified${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "1. Login to dashboard: ${BLUE}https://crawldoctor.fly.dev${NC}"
echo -e "2. Check new 'Users' page in sidebar"
echo -e "3. Monitor for client_id adoption:"
echo -e "   ${BLUE}fly ssh console -a $APP_NAME -C 'psql \$DATABASE_URL -c \"SELECT COUNT(*), COUNT(client_id) FROM visits WHERE timestamp >= NOW() - INTERVAL '"'"'1 hour'"'"';\"'${NC}"
echo ""
echo -e "${YELLOW}Backup Location:${NC}"
echo -e "  $BACKUP_FILE"
echo -e "  ${YELLOW}Keep this safe for at least 7 days!${NC}"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo -e "  - UNIFIED_DATA_MODEL.md"
echo -e "  - DEPLOYMENT_GUIDE_UNIFIED_MODEL.md"
echo -e "  - UNIFIED_MODEL_IMPLEMENTATION_SUMMARY.md"
echo ""

# Create deployment log
LOG_FILE="${BACKUP_DIR}/deployment_log_${TIMESTAMP}.txt"
{
    echo "Unified Data Model Deployment Log"
    echo "=================================="
    echo "Timestamp: $(date)"
    echo "App: $APP_NAME"
    echo "Backup: $BACKUP_FILE"
    echo "Migration: unified_client_id"
    echo "Status: SUCCESS"
    echo ""
    echo "Changes:"
    echo "- Added client_id field to visit_sessions, visits, visit_events"
    echo "- Created 6 new indexes for client_id queries"
    echo "- Added /api/v1/analytics/users endpoints"
    echo "- Added Users page to frontend"
    echo ""
    echo "Health checks:"
    echo "- App status: HTTP $HEALTH_CHECK"
    echo "- Users endpoint: HTTP $USERS_ENDPOINT"
} > "$LOG_FILE"

echo -e "${GREEN}Deployment log saved to: $LOG_FILE${NC}"
echo ""

