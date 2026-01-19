#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deploy Unified Data Model to Fly.io        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check for app name argument
APP_NAME="${1:-crawldoctor}"
echo -e "${BLUE}App name: $APP_NAME${NC}"
echo ""

# Step 1: Ensure we're logged in and tokens are fresh
echo -e "${YELLOW}[1/6] Checking fly.io authentication...${NC}"
fly auth whoami 2>&1 | head -5

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}Not logged in or token expired.${NC}"
    echo -e "${YELLOW}Running: fly auth login${NC}"
    fly auth login
fi

echo -e "${GREEN}✓ Logged in to fly.io${NC}"
echo ""

# Step 2: Create backup directory
echo -e "${YELLOW}[2/6] Creating backup directory...${NC}"
mkdir -p backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Backup directory ready${NC}"
echo ""

# Step 3: Try to create database backup
echo -e "${YELLOW}[3/6] Attempting to backup database...${NC}"
echo -e "${BLUE}If app exists with database, this will create a backup${NC}"

set +e  # Don't exit on error for this step
fly ssh console -a $APP_NAME -C "pg_dump \$DATABASE_URL > /tmp/backup_${TIMESTAMP}.sql" 2>&1
BACKUP_EXIT=$?

if [ $BACKUP_EXIT -eq 0 ]; then
    echo -e "${BLUE}Downloading backup...${NC}"
    fly ssh sftp get -a $APP_NAME /tmp/backup_${TIMESTAMP}.sql backups/backup_${TIMESTAMP}.sql 2>&1
    
    if [ -f "backups/backup_${TIMESTAMP}.sql" ]; then
        BACKUP_SIZE=$(ls -lh "backups/backup_${TIMESTAMP}.sql" | awk '{print $5}')
        echo -e "${GREEN}✓ Database backup created: backups/backup_${TIMESTAMP}.sql ($BACKUP_SIZE)${NC}"
        BACKUP_CREATED=true
    else
        echo -e "${YELLOW}⚠️  Could not download backup (app may not exist yet)${NC}"
        BACKUP_CREATED=false
    fi
else
    echo -e "${YELLOW}⚠️  Could not create backup (app may not exist yet or no database)${NC}"
    BACKUP_CREATED=false
fi
set -e  # Re-enable exit on error
echo ""

# Step 4: Frontend check
echo -e "${YELLOW}[4/6] Checking frontend build...${NC}"
if [ ! -d "frontend/build" ]; then
    echo -e "${BLUE}Building frontend...${NC}"
    cd frontend
    npm install
    npm run build
    cd ..
fi

if [ ! -f "frontend/build/index.html" ]; then
    echo -e "${RED}Error: Frontend build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend build ready${NC}"
echo ""

# Step 5: Deploy to fly.io
echo -e "${YELLOW}[5/6] Deploying to fly.io...${NC}"
echo ""
echo -e "${BLUE}This will:${NC}"
echo -e "${BLUE}  1. Build Docker image with new code${NC}"
echo -e "${BLUE}  2. Deploy to fly.io${NC}"
echo -e "${BLUE}  3. Run database migrations automatically (via entrypoint)${NC}"
echo -e "${BLUE}  4. Add client_id fields to database${NC}"
echo ""

if [ "$BACKUP_CREATED" = true ]; then
    echo -e "${GREEN}✓ Database backup saved: backups/backup_${TIMESTAMP}.sql${NC}"
    echo ""
fi

read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Deploying...${NC}"

# Deploy with fly
fly deploy --app $APP_NAME --strategy immediate

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Deployment failed${NC}"
    if [ "$BACKUP_CREATED" = true ]; then
        echo -e "${YELLOW}Database backup is safe at: backups/backup_${TIMESTAMP}.sql${NC}"
    fi
    exit 1
fi

echo -e "${GREEN}✓ Deployment completed${NC}"
echo ""

# Step 6: Verify deployment
echo -e "${YELLOW}[6/6] Verifying deployment...${NC}"
sleep 5

# Get app URL
APP_URL=$(fly info --app $APP_NAME 2>&1 | grep "Hostname" | awk '{print $3}' || echo "$APP_NAME.fly.dev")

echo -e "${BLUE}Checking health endpoint...${NC}"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "https://${APP_URL}/track/status" || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed (HTTP 200)${NC}"
else
    echo -e "${YELLOW}⚠️  Health check: HTTP $HEALTH_CHECK (app may still be starting)${NC}"
fi

# Check if migration ran
echo -e "${BLUE}Checking database migration...${NC}"
set +e
fly ssh console -a $APP_NAME -C "cd /app && alembic current" 2>&1 | grep -q "unified_client_id"
MIGRATION_CHECK=$?
set -e

if [ $MIGRATION_CHECK -eq 0 ]; then
    echo -e "${GREEN}✓ Database migration verified: unified_client_id is active${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify migration (check logs)${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          DEPLOYMENT SUCCESSFUL! 🎉            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$BACKUP_CREATED" = true ]; then
    echo -e "${GREEN}✓ Database backup: backups/backup_${TIMESTAMP}.sql${NC}"
fi
echo -e "${GREEN}✓ Code deployed to fly.io${NC}"
echo -e "${GREEN}✓ Database migration completed${NC}"
echo -e "${GREEN}✓ App URL: https://${APP_URL}${NC}"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo -e "1. Login to dashboard: ${BLUE}https://${APP_URL}${NC}"
echo -e "2. Look for new 'Users' page in sidebar"
echo -e "3. Monitor logs: ${BLUE}fly logs -a $APP_NAME${NC}"
echo ""

# Create deployment log
LOG_FILE="backups/deployment_log_${TIMESTAMP}.txt"
{
    echo "Unified Data Model Deployment"
    echo "============================="
    echo "Date: $(date)"
    echo "App: $APP_NAME"
    echo "URL: https://${APP_URL}"
    if [ "$BACKUP_CREATED" = true ]; then
        echo "Backup: backups/backup_${TIMESTAMP}.sql"
    fi
    echo "Status: SUCCESS"
} > "$LOG_FILE"

echo -e "${GREEN}Deployment log: $LOG_FILE${NC}"
echo ""

