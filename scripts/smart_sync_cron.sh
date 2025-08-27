#!/bin/bash
# Smart Yahoo Finance Data Sync Cron Script
# This script can be added to crontab for automatic daily syncing

# Set environment variables
export PYTHONPATH="/Users/gurudayal/Desktop/ai:$PYTHONPATH"

# Navigate to project directory
cd "$(dirname "$0")/.."

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file for this run
LOG_FILE="logs/smart_sync_$(date +%Y%m%d_%H%M%S).log"

echo "$(date): 🚀 Starting Smart Yahoo Finance Data Sync..." | tee -a "$LOG_FILE"

# Run the smart syncer using Anaconda Python
/opt/anaconda3/bin/python scripts/smart_yahoo_syncer.py 2>&1 | tee -a "$LOG_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): ✅ Smart sync completed successfully" | tee -a "$LOG_FILE"
else
    echo "$(date): ❌ Smart sync failed with exit code $?" | tee -a "$LOG_FILE"
fi

# Clean up old log files (keep last 30 days)
find logs -name "smart_sync_*.log" -mtime +30 -delete

# Also clean up old sync logs
find logs -name "smart_sync.log" -mtime +30 -delete

echo "$(date): 🧹 Cleanup completed" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"
