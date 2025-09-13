#!/bin/bash
# Daily OHLCV Sync Wrapper Script
# This script is called by cron and sets up the proper environment

# Set environment variables
export PYTHONPATH="/Users/gurudayal/Desktop/ai"
export ACTIVE_DATABASE=prod

# Change to project directory
cd "/Users/gurudayal/Desktop/ai"

# Run the daily syncer
python3 scripts/daily_ohlcv_syncer.py

# Log completion
echo "$(date): Daily OHLCV sync completed" >> "/Users/gurudayal/Desktop/ai/logs/cron_sync.log"
