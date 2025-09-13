#!/bin/bash
# Daily OHLCV Sync Cron Job Setup
#
# This script sets up a cron job to run the daily OHLCV syncer at 5 PM every day.
# It also creates necessary directories and sets up logging.
#
# Usage:
#     chmod +x scripts/setup_daily_sync_cron.sh
#     ./scripts/setup_daily_sync_cron.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up Daily OHLCV Sync Cron Job${NC}"

# Get the current directory (project root)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo -e "${YELLOW}📁 Project directory: $PROJECT_DIR${NC}"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"
echo -e "${GREEN}✅ Created logs directory${NC}"

# Make the daily syncer executable
chmod +x "$PROJECT_DIR/scripts/daily_ohlcv_syncer.py"
echo -e "${GREEN}✅ Made daily_ohlcv_syncer.py executable${NC}"

# Create a wrapper script for cron execution
WRAPPER_SCRIPT="$PROJECT_DIR/scripts/run_daily_sync.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Daily OHLCV Sync Wrapper Script
# This script is called by cron and sets up the proper environment

# Set environment variables
export PYTHONPATH="$PROJECT_DIR"
export ACTIVE_DATABASE=prod

# Change to project directory
cd "$PROJECT_DIR"

# Run the daily syncer
python3 scripts/daily_ohlcv_syncer.py

# Log completion
echo "\$(date): Daily OHLCV sync completed" >> "$PROJECT_DIR/logs/cron_sync.log"
EOF

chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✅ Created wrapper script: $WRAPPER_SCRIPT${NC}"

# Create the cron job entry
CRON_ENTRY="0 17 * * * $WRAPPER_SCRIPT >> $PROJECT_DIR/logs/cron_sync.log 2>&1"

echo -e "${YELLOW}📅 Cron job entry:${NC}"
echo -e "${BLUE}$CRON_ENTRY${NC}"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Cron job added successfully!${NC}"
    echo -e "${YELLOW}📋 Current crontab:${NC}"
    crontab -l
else
    echo -e "${RED}❌ Failed to add cron job${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Daily OHLCV sync setup completed!${NC}"
echo -e "${YELLOW}📝 The sync will run every day at 5:00 PM${NC}"
echo -e "${YELLOW}📊 Logs will be saved to: $PROJECT_DIR/logs/${NC}"
echo -e "${YELLOW}🔍 To view logs: tail -f $PROJECT_DIR/logs/daily_ohlcv_sync.log${NC}"
echo -e "${YELLOW}🔍 To view cron logs: tail -f $PROJECT_DIR/logs/cron_sync.log${NC}"

echo -e "${BLUE}📋 Manual testing commands:${NC}"
echo -e "${YELLOW}  # Test sync for all stocks:${NC}"
echo -e "${BLUE}  python3 scripts/daily_ohlcv_syncer.py${NC}"
echo -e "${YELLOW}  # Test sync for specific stock:${NC}"
echo -e "${BLUE}  python3 scripts/daily_ohlcv_syncer.py --symbol RELIANCE${NC}"
echo -e "${YELLOW}  # Validate existing data only:${NC}"
echo -e "${BLUE}  python3 scripts/daily_ohlcv_syncer.py --validate-only${NC}"
