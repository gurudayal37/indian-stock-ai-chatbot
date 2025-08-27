#!/usr/bin/env python3
"""
Check Sync Status Utility
Shows sync status, last update times, and data counts for all stocks
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.stock import Stock, SyncTracker

def check_sync_status():
    """Check and display sync status for all stocks"""
    db = SessionLocal()
    
    try:
        print("🔍 Checking Sync Status for All Stocks")
        print("=" * 60)
        
        # Get all stocks
        stocks = db.query(Stock).all()
        
        if not stocks:
            print("❌ No stocks found in database")
            return
        
        print(f"📊 Total Stocks: {len(stocks)}")
        print()
        
        # Check sync status for each stock
        for stock in stocks:
            print(f"🏢 {stock.nse_symbol} - {stock.name}")
            print(f"   Sector: {stock.sector}")
            
            # Get sync trackers for this stock
            trackers = db.query(SyncTracker).filter(SyncTracker.stock_id == stock.id).all()
            
            if not trackers:
                print("   ⚠️  No sync tracking data found")
            else:
                for tracker in trackers:
                    status_emoji = "✅" if tracker.sync_status == "success" else "❌" if tracker.sync_status == "failed" else "⚠️"
                    
                    print(f"   {status_emoji} {tracker.data_type.upper()}:")
                    print(f"      Last Sync: {tracker.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if tracker.last_sync_time else 'Never'}")
                    print(f"      Last Data: {tracker.last_data_date.strftime('%Y-%m-%d') if tracker.last_data_date else 'None'}")
                    print(f"      Records: {tracker.records_count}")
                    print(f"      Status: {tracker.sync_status}")
                    
                    if tracker.error_message:
                        print(f"      Error: {tracker.error_message}")
            
            print()
        
        # Summary statistics
        print("📈 SYNC SUMMARY STATISTICS")
        print("=" * 60)
        
        # Count sync statuses
        success_count = db.query(SyncTracker).filter(SyncTracker.sync_status == 'success').count()
        failed_count = db.query(SyncTracker).filter(SyncTracker.sync_status == 'failed').count()
        total_trackers = db.query(SyncTracker).count()
        
        print(f"✅ Successful Syncs: {success_count}")
        print(f"❌ Failed Syncs: {failed_count}")
        print(f"📊 Total Trackers: {total_trackers}")
        
        if total_trackers > 0:
            success_rate = (success_count / total_trackers) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        # Check for stale data
        print("\n⏰ STALE DATA CHECK")
        print("=" * 60)
        
        stale_threshold = datetime.utcnow() - timedelta(days=7)
        stale_trackers = db.query(SyncTracker).filter(
            SyncTracker.last_sync_time < stale_threshold
        ).all()
        
        if stale_trackers:
            print(f"⚠️  Found {len(stale_trackers)} trackers with stale data (>7 days):")
            for tracker in stale_trackers:
                stock = db.query(Stock).filter(Stock.id == tracker.stock_id).first()
                days_old = (datetime.utcnow() - tracker.last_sync_time).days
                print(f"   • {stock.nse_symbol if stock else 'Unknown'} - {tracker.data_type}: {days_old} days old")
        else:
            print("✅ All sync trackers are up to date")
        
        # Data type statistics
        print("\n📊 DATA TYPE STATISTICS")
        print("=" * 60)
        
        data_types = ['ohlcv', 'news', 'financials', 'earnings']
        for data_type in data_types:
            trackers = db.query(SyncTracker).filter(SyncTracker.data_type == data_type).all()
            if trackers:
                total_records = sum(t.records_count for t in trackers)
                avg_records = total_records / len(trackers) if trackers else 0
                print(f"📊 {data_type.upper()}: {len(trackers)} stocks, {total_records} total records, {avg_records:.1f} avg per stock")
        
    except Exception as e:
        print(f"❌ Error checking sync status: {e}")
    
    finally:
        db.close()

def check_stock_sync_status(symbol: str):
    """Check sync status for a specific stock"""
    db = SessionLocal()
    
    try:
        print(f"🔍 Checking Sync Status for {symbol}")
        print("=" * 60)
        
        # Get stock
        stock = db.query(Stock).filter(Stock.nse_symbol == symbol).first()
        if not stock:
            print(f"❌ Stock {symbol} not found in database")
            return
        
        print(f"🏢 {stock.nse_symbol} - {stock.name}")
        print(f"   Sector: {stock.sector}")
        print(f"   Industry: {stock.industry}")
        print()
        
        # Get sync trackers
        trackers = db.query(SyncTracker).filter(SyncTracker.stock_id == stock.id).all()
        
        if not trackers:
            print("⚠️  No sync tracking data found for this stock")
            return
        
        for tracker in trackers:
            status_emoji = "✅" if tracker.sync_status == "success" else "❌" if tracker.sync_status == "failed" else "⚠️"
            
            print(f"{status_emoji} {tracker.data_type.upper()}:")
            print(f"   Last Sync: {tracker.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if tracker.last_sync_time else 'Never'}")
            print(f"   Last Data: {tracker.last_data_date.strftime('%Y-%m-%d') if tracker.last_data_date else 'None'}")
            print(f"   Records: {tracker.records_count}")
            print(f"   Status: {tracker.sync_status}")
            
            if tracker.error_message:
                print(f"   Error: {tracker.error_message}")
            
            # Check if data is stale
            if tracker.last_sync_time:
                days_old = (datetime.utcnow() - tracker.last_sync_time).days
                if days_old > 7:
                    print(f"   ⚠️  Data is {days_old} days old (stale)")
                elif days_old > 1:
                    print(f"   ⚠️  Data is {days_old} days old")
                else:
                    print(f"   ✅ Data is fresh ({days_old} days old)")
            
            print()
        
    except Exception as e:
        print(f"❌ Error checking sync status for {symbol}: {e}")
    
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Check specific stock
        symbol = sys.argv[1]
        check_stock_sync_status(symbol)
    else:
        # Check all stocks
        check_sync_status()

if __name__ == "__main__":
    main()
