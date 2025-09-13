#!/usr/bin/env python3
"""
Daily OHLCV Sync Status Checker

This script checks the status of the daily OHLCV sync:
1. Shows last sync times for all stocks
2. Identifies stocks that need syncing
3. Shows sync statistics and health

Usage:
    python scripts/check_daily_sync_status.py
"""

import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append('/Users/gurudayal/Desktop/ai')

from app.core.database import SessionLocal
from app.models.stock import Stock, DailyPrice, SyncTracker

def check_sync_status():
    """Check the status of daily OHLCV sync for all stocks."""
    
    db = SessionLocal()
    try:
        print("🔍 Daily OHLCV Sync Status Check")
        print("=" * 50)
        
        # Get all stocks
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        print(f"📊 Total Active Stocks: {len(stocks)}")
        
        # Get sync tracker data
        sync_trackers = db.query(SyncTracker).filter(
            SyncTracker.data_type == 'ohlcv'
        ).all()
        
        print(f"📈 OHLCV Sync Records: {len(sync_trackers)}")
        print()
        
        # Check recent syncs (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_syncs = [t for t in sync_trackers if t.last_sync_time and t.last_sync_time > recent_cutoff]
        
        print(f"✅ Recently Synced (24h): {len(recent_syncs)}")
        
        # Check stocks that need syncing
        needs_sync = []
        for stock in stocks:
            tracker = next((t for t in sync_trackers if t.stock_id == stock.id), None)
            if not tracker or not tracker.last_sync_time or tracker.last_sync_time < recent_cutoff:
                needs_sync.append(stock)
        
        print(f"⚠️  Needs Sync: {len(needs_sync)}")
        
        if needs_sync:
            print("\n📋 Stocks that need syncing:")
            for stock in needs_sync[:10]:  # Show first 10
                tracker = next((t for t in sync_trackers if t.stock_id == stock.id), None)
                last_sync = tracker.last_sync_time.strftime('%Y-%m-%d %H:%M') if tracker and tracker.last_sync_time else 'Never'
                print(f"  • {stock.nse_symbol} ({stock.name}) - Last sync: {last_sync}")
            
            if len(needs_sync) > 10:
                print(f"  ... and {len(needs_sync) - 10} more")
        
        # Show recent sync summary
        if recent_syncs:
            print(f"\n📊 Recent Sync Summary (Last 24h):")
            total_records = sum(t.records_count or 0 for t in recent_syncs)
            print(f"  • Total Records Synced: {total_records:,}")
            print(f"  • Average Records per Stock: {total_records // len(recent_syncs) if recent_syncs else 0:,}")
            
            # Show latest syncs
            latest_syncs = sorted(recent_syncs, key=lambda x: x.last_sync_time, reverse=True)[:5]
            print(f"\n🕒 Latest Syncs:")
            for tracker in latest_syncs:
                stock = next((s for s in stocks if s.id == tracker.stock_id), None)
                if stock:
                    sync_time = tracker.last_sync_time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  • {stock.nse_symbol}: {sync_time} ({tracker.records_count or 0} records)")
        
        # Check for errors
        error_trackers = [t for t in sync_trackers if t.sync_status == 'error']
        if error_trackers:
            print(f"\n❌ Sync Errors: {len(error_trackers)}")
            for tracker in error_trackers[:5]:
                stock = next((s for s in stocks if s.id == tracker.stock_id), None)
                if stock:
                    print(f"  • {stock.nse_symbol}: {tracker.error_message}")
        
        print(f"\n💡 To run sync: python scripts/daily_ohlcv_syncer.py")
        print(f"💡 To sync specific stock: python scripts/daily_ohlcv_syncer.py --symbol SYMBOL")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_sync_status()
