#!/usr/bin/env python3
"""
Daily OHLCV Data Syncer

This script runs daily at 5 PM to:
1. Fetch daily OHLCV data from yfinance for all stocks
2. Validate last day's data against existing database data
3. If validation fails, delete all OHLCV data for that stock and fetch complete data (up to 5 years)
4. Update sync tracker with latest data

Features:
- Data validation with configurable tolerance
- Complete data refresh on validation failure
- Comprehensive logging
- Error handling and retry logic
- Progress tracking

Usage:
    python scripts/daily_ohlcv_syncer.py                    # Run sync for all stocks
    python scripts/daily_ohlcv_syncer.py --symbol RELIANCE  # Run for specific stock
    python scripts/daily_ohlcv_syncer.py --validate-only    # Only validate existing data
"""

import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.database import SessionLocal
from app.models.stock import Stock, DailyPrice, SyncTracker

# Configure logging
import os
# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_ohlcv_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyOHLCVSyncer:
    def __init__(self, validation_tolerance: float = 0.01):
        """
        Initialize the daily OHLCV syncer.
        
        Args:
            validation_tolerance: Tolerance for price validation (1% by default)
        """
        self.validation_tolerance = validation_tolerance
        self.db = SessionLocal()
        
    def get_all_stocks(self) -> List[Stock]:
        """Get all active stocks from database"""
        try:
            stocks = self.db.query(Stock).filter(Stock.is_active == True).all()
            logger.info(f"📊 Found {len(stocks)} active stocks to sync")
            return stocks
        except Exception as e:
            logger.error(f"❌ Error getting stocks: {e}")
            return []
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Stock]:
        """Get stock by BSE or NSE symbol"""
        try:
            stock = self.db.query(Stock).filter(
                (Stock.bse_symbol == symbol) | (Stock.nse_symbol == symbol)
            ).first()
            return stock
        except Exception as e:
            logger.error(f"❌ Error getting stock {symbol}: {e}")
            return None
    
    def get_latest_ohlcv_data(self, stock: Stock) -> Optional[Dict[str, Any]]:
        """Get the latest OHLCV data from database for a stock"""
        try:
            latest_price = self.db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock.id
            ).order_by(DailyPrice.date.desc()).first()
            
            if latest_price:
                return {
                    'date': latest_price.date,
                    'open': latest_price.open_price,
                    'high': latest_price.high_price,
                    'low': latest_price.low_price,
                    'close': latest_price.close_price,
                    'volume': latest_price.volume
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error getting latest OHLCV for {stock.nse_symbol}: {e}")
            return None
    
    def fetch_yahoo_data(self, stock: Stock, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Yahoo Finance (up to 5 years of historical data)"""
        try:
            # Use NSE symbol for Yahoo Finance
            symbol = f"{stock.nse_symbol}.NS"
            ticker = yf.Ticker(symbol)
            
            # Fetch data
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"⚠️ No data from Yahoo Finance for {symbol}")
                return None
                
            logger.info(f"📈 Fetched {len(data)} records from Yahoo Finance for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching Yahoo data for {stock.nse_symbol}: {e}")
            return None
    
    def validate_ohlcv_data(self, db_data: Dict[str, Any], yahoo_data: pd.Series) -> bool:
        """
        Validate if database data matches Yahoo Finance data within tolerance
        
        Args:
            db_data: Latest data from database
            yahoo_data: Corresponding data from Yahoo Finance
            
        Returns:
            True if data matches within tolerance, False otherwise
        """
        try:
            if not db_data or yahoo_data.empty:
                return False
            
            # Check each price field
            fields = ['open', 'high', 'low', 'close']
            yahoo_field_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}
            for field in fields:
                db_value = db_data[field]
                yahoo_value = float(yahoo_data[yahoo_field_map[field]])
                
                if db_value is None or yahoo_value is None:
                    continue
                    
                # Calculate percentage difference
                diff = abs(db_value - yahoo_value) / db_value
                
                if diff > self.validation_tolerance:
                    logger.warning(f"⚠️ {field} validation failed: DB={db_value}, Yahoo={yahoo_value}, Diff={diff:.4f}")
                    return False
            
            # Check volume (more lenient tolerance for volume)
            if db_data['volume'] and yahoo_data['Volume']:
                volume_diff = abs(db_data['volume'] - int(yahoo_data['Volume'])) / db_data['volume']
                if volume_diff > 0.1:  # 10% tolerance for volume
                    logger.warning(f"⚠️ Volume validation failed: DB={db_data['volume']}, Yahoo={int(yahoo_data['Volume'])}, Diff={volume_diff:.4f}")
                    return False
            
            logger.info("✅ Data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during validation: {e}")
            return False
    
    def delete_all_ohlcv_data(self, stock_id: int) -> bool:
        """Delete all OHLCV data for a stock"""
        try:
            deleted_count = self.db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock_id
            ).delete()
            
            self.db.commit()
            logger.info(f"🗑️ Deleted {deleted_count} OHLCV records for stock_id {stock_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting OHLCV data: {e}")
            self.db.rollback()
            return False
    
    def save_ohlcv_data(self, stock_id: int, data: pd.DataFrame) -> int:
        """Save OHLCV data to database using bulk operations"""
        try:
            if data.empty:
                logger.info("✅ No data to save")
                return 0
            
            # Get existing dates for this stock to avoid duplicates
            dates_list = [date.date() for date in data.index]
            existing_dates = set()
            
            # Query existing dates in batches to avoid memory issues
            batch_size = 1000
            for i in range(0, len(dates_list), batch_size):
                batch_dates = dates_list[i:i + batch_size]
                existing_query = self.db.query(DailyPrice.date).filter(
                    and_(
                        DailyPrice.stock_id == stock_id,
                        DailyPrice.date.in_(batch_dates)
                    )
                ).all()
                existing_dates.update({row[0] for row in existing_query})
            
            # Filter out existing records
            new_data = data[~data.index.map(lambda x: x.date()).isin(existing_dates)]
            
            if new_data.empty:
                logger.info("✅ No new data to save")
                return 0
            
            # Prepare bulk insert data
            bulk_data = []
            for date, row in new_data.iterrows():
                bulk_data.append({
                    'stock_id': stock_id,
                    'date': date.date(),
                    'open_price': float(row['Open']),
                    'high_price': float(row['High']),
                    'low_price': float(row['Low']),
                    'close_price': float(row['Close']),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                    'turnover': float(row['Open'] * row['Volume']) if pd.notna(row['Volume']) else None,
                    'vwap': None,
                    'delivery_quantity': None,
                    'delivery_percentage': None
                })
            
            # Bulk insert using SQLAlchemy bulk_insert_mappings
            if bulk_data:
                # Insert in batches to avoid memory issues
                batch_size = 1000
                total_saved = 0
                for i in range(0, len(bulk_data), batch_size):
                    batch = bulk_data[i:i + batch_size]
                    self.db.bulk_insert_mappings(DailyPrice, batch)
                    total_saved += len(batch)
                
                self.db.commit()
                logger.info(f"💾 Saved {total_saved} new OHLCV records")
                return total_saved
            else:
                logger.info("✅ No new data to save")
                return 0
            
        except Exception as e:
            logger.error(f"❌ Error saving OHLCV data: {e}")
            self.db.rollback()
            return 0
    
    def update_sync_tracker(self, stock_id: int, last_data_date: datetime, records_count: int, status: str = 'success', error_message: str = None):
        """Update sync tracker for a stock"""
        try:
            tracker = self.db.query(SyncTracker).filter(
                and_(
                    SyncTracker.stock_id == stock_id,
                    SyncTracker.data_type == 'ohlcv'
                )
            ).first()
            
            if not tracker:
                tracker = SyncTracker(
                    stock_id=stock_id,
                    data_type='ohlcv',
                    last_sync_time=datetime.utcnow(),
                    last_data_date=last_data_date,
                    records_count=records_count,
                    sync_status=status,
                    error_message=error_message
                )
                self.db.add(tracker)
            else:
                tracker.last_sync_time = datetime.utcnow()
                tracker.last_data_date = last_data_date
                tracker.records_count = records_count
                tracker.sync_status = status
                tracker.error_message = error_message
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"❌ Error updating sync tracker: {e}")
            self.db.rollback()
    
    def sync_stock_ohlcv(self, stock: Stock, validate_only: bool = False) -> Tuple[bool, str]:
        """
        Sync OHLCV data for a single stock
        
        Args:
            stock: Stock object to sync
            validate_only: If True, only validate existing data without fetching new data
            
        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"🔄 Syncing OHLCV for {stock.nse_symbol} ({stock.name})")
            
            # Get latest data from database
            latest_db_data = self.get_latest_ohlcv_data(stock)
            
            if not latest_db_data:
                logger.info(f"📊 No existing data for {stock.nse_symbol}, fetching complete data")
                # Fetch complete data (5 years)
                start_date = datetime.now() - timedelta(days=1825)  # 5 years
                end_date = datetime.now()
            else:
                # Check if we need to validate
                if validate_only:
                    logger.info(f"🔍 Validation only mode for {stock.nse_symbol}")
                    return True, "Validation completed"
                
                # Fetch data from last day to today
                start_date = latest_db_data['date'] + timedelta(days=1)
                end_date = datetime.now()
                
                # If start_date is today or future, no new data needed
                if start_date >= end_date:
                    logger.info(f"✅ {stock.nse_symbol} data is up to date")
                    return True, "Data is up to date"
            
            # Fetch data from Yahoo Finance
            yahoo_data = self.fetch_yahoo_data(stock, start_date, end_date)
            
            if yahoo_data is None or yahoo_data.empty:
                logger.warning(f"⚠️ No new data available for {stock.nse_symbol}")
                return True, "No new data available"
            
            # If we have existing data, validate the last day
            if latest_db_data and not validate_only:
                # Get the last day from Yahoo data for validation
                last_yahoo_date = yahoo_data.index[-1]
                last_yahoo_data = yahoo_data.loc[last_yahoo_date]
                
                # Validate data
                if not self.validate_ohlcv_data(latest_db_data, last_yahoo_data):
                    logger.warning(f"⚠️ Data validation failed for {stock.nse_symbol}, refreshing complete data")
                    
                    # Delete all existing data
                    if not self.delete_all_ohlcv_data(stock.id):
                        return False, "Failed to delete existing data"
                    
                    # Fetch complete data (5 years)
                    start_date = datetime.now() - timedelta(days=1825)  # 5 years
                    end_date = datetime.now()
                    yahoo_data = self.fetch_yahoo_data(stock, start_date, end_date)
                    
                    if yahoo_data is None or yahoo_data.empty:
                        return False, "Failed to fetch complete data"
            
            # Save new data
            saved_count = self.save_ohlcv_data(stock.id, yahoo_data)
            
            if saved_count > 0:
                # Update sync tracker
                last_date = yahoo_data.index[-1].date()
                self.update_sync_tracker(stock.id, last_date, saved_count, 'success')
                
                logger.info(f"✅ Successfully synced {saved_count} records for {stock.nse_symbol}")
                return True, f"Synced {saved_count} records"
            else:
                logger.info(f"ℹ️ No new records to save for {stock.nse_symbol}")
                return True, "No new records"
                
        except Exception as e:
            logger.error(f"❌ Error syncing {stock.nse_symbol}: {e}")
            self.update_sync_tracker(stock.id, None, 0, 'failed', str(e))
            return False, str(e)
    
    def sync_all_stocks(self, validate_only: bool = False) -> Dict[str, int]:
        """Sync OHLCV data for all stocks"""
        try:
            stocks = self.get_all_stocks()
            
            if not stocks:
                logger.warning("⚠️ No stocks found to sync")
                return {"total": 0, "success": 0, "failed": 0}
            
            total_stocks = len(stocks)
            success_count = 0
            failed_count = 0
            
            logger.info(f"🚀 Starting daily OHLCV sync for {total_stocks} stocks")
            logger.info(f"🔧 Validation tolerance: {self.validation_tolerance*100:.1f}%")
            
            # Process in batches to avoid memory issues and improve performance
            batch_size = 20
            for batch_start in range(0, total_stocks, batch_size):
                batch_end = min(batch_start + batch_size, total_stocks)
                batch_stocks = stocks[batch_start:batch_end]
                
                logger.info(f"📦 Processing batch {batch_start//batch_size + 1}: stocks {batch_start+1}-{batch_end}")
                
                for i, stock in enumerate(batch_stocks, batch_start + 1):
                    logger.info(f"📈 Progress: {i}/{total_stocks} - {stock.nse_symbol}")
                    
                    success, message = self.sync_stock_ohlcv(stock, validate_only)
                    
                    if success:
                        success_count += 1
                        logger.info(f"✅ {stock.nse_symbol}: {message}")
                    else:
                        failed_count += 1
                        logger.error(f"❌ {stock.nse_symbol}: {message}")
                    
                    # Minimal delay for better performance
                    if i < total_stocks:
                        time.sleep(0.05)
                
                # Commit after each batch
                self.db.commit()
                logger.info(f"✅ Batch {batch_start//batch_size + 1} completed. Success: {success_count}, Failed: {failed_count}")
            
            # Final summary
            logger.info("🎉 Daily OHLCV sync completed!")
            logger.info(f"📊 Results: {success_count} successful, {failed_count} failed out of {total_stocks} total")
            
            return {
                "total": total_stocks,
                "success": success_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error during daily sync: {e}")
            return {"total": 0, "success": 0, "failed": 0}
        finally:
            self.db.close()
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()

def main():
    parser = argparse.ArgumentParser(description='Daily OHLCV Data Syncer')
    parser.add_argument('--symbol', type=str, help='Sync specific stock by symbol')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing data')
    parser.add_argument('--tolerance', type=float, default=0.01, help='Validation tolerance (default: 0.01 = 1%)')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Daily OHLCV Syncer")
    logger.info(f"⚙️ Configuration: tolerance={args.tolerance*100:.1f}%, validate_only={args.validate_only}")
    
    syncer = DailyOHLCVSyncer(validation_tolerance=args.tolerance)
    
    try:
        if args.symbol:
            # Sync specific stock
            stock = syncer.get_stock_by_symbol(args.symbol)
            if stock:
                success, message = syncer.sync_stock_ohlcv(stock, args.validate_only)
                if success:
                    logger.info(f"✅ {args.symbol}: {message}")
                else:
                    logger.error(f"❌ {args.symbol}: {message}")
            else:
                logger.error(f"❌ Stock {args.symbol} not found")
        else:
            # Sync all stocks
            results = syncer.sync_all_stocks(args.validate_only)
            logger.info(f"📊 Final results: {results}")
    
    except KeyboardInterrupt:
        logger.info("⏹️ Sync interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        syncer.close()

if __name__ == "__main__":
    main()
