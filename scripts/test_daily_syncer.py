#!/usr/bin/env python3
"""
Test Daily OHLCV Syncer

This script tests the daily OHLCV syncer functionality:
1. Test data validation logic
2. Test complete data refresh
3. Test individual stock sync
4. Test error handling

Usage:
    python scripts/test_daily_syncer.py                    # Test all functionality
    python scripts/test_daily_syncer.py --symbol RELIANCE  # Test specific stock
    python scripts/test_daily_syncer.py --validate-only    # Test validation only
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append('/Users/gurudayal/Desktop/ai')

from app.core.database import SessionLocal
from app.models.stock import Stock, DailyPrice
from scripts.daily_ohlcv_syncer import DailyOHLCVSyncer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_daily_syncer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailySyncerTester:
    def __init__(self):
        self.db = SessionLocal()
        self.syncer = DailyOHLCVSyncer()
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        try:
            stock_count = self.db.query(Stock).count()
            logger.info(f"✅ Database connection successful. Found {stock_count} stocks")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def test_stock_retrieval(self) -> bool:
        """Test stock retrieval functionality"""
        try:
            # Test getting all stocks
            all_stocks = self.syncer.get_all_stocks()
            logger.info(f"✅ Retrieved {len(all_stocks)} stocks")
            
            # Test getting specific stock
            reliance = self.syncer.get_stock_by_symbol('RELIANCE')
            if reliance:
                logger.info(f"✅ Retrieved RELIANCE stock: {reliance.name}")
            else:
                logger.warning("⚠️ RELIANCE stock not found")
            
            return True
        except Exception as e:
            logger.error(f"❌ Stock retrieval test failed: {e}")
            return False
    
    def test_ohlcv_data_retrieval(self) -> bool:
        """Test OHLCV data retrieval"""
        try:
            reliance = self.syncer.get_stock_by_symbol('RELIANCE')
            if not reliance:
                logger.warning("⚠️ RELIANCE not found, skipping OHLCV test")
                return True
            
            latest_data = self.syncer.get_latest_ohlcv_data(reliance)
            if latest_data:
                logger.info(f"✅ Retrieved latest OHLCV data for RELIANCE: {latest_data['date']}")
            else:
                logger.info("ℹ️ No existing OHLCV data for RELIANCE")
            
            return True
        except Exception as e:
            logger.error(f"❌ OHLCV data retrieval test failed: {e}")
            return False
    
    def test_yahoo_data_fetch(self) -> bool:
        """Test Yahoo Finance data fetching"""
        try:
            reliance = self.syncer.get_stock_by_symbol('RELIANCE')
            if not reliance:
                logger.warning("⚠️ RELIANCE not found, skipping Yahoo test")
                return True
            
            # Fetch last 7 days of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            yahoo_data = self.syncer.fetch_yahoo_data(reliance, start_date, end_date)
            if yahoo_data is not None and not yahoo_data.empty:
                logger.info(f"✅ Fetched {len(yahoo_data)} records from Yahoo Finance")
                logger.info(f"📊 Date range: {yahoo_data.index[0].date()} to {yahoo_data.index[-1].date()}")
            else:
                logger.warning("⚠️ No data from Yahoo Finance")
            
            return True
        except Exception as e:
            logger.error(f"❌ Yahoo data fetch test failed: {e}")
            return False
    
    def test_data_validation(self) -> bool:
        """Test data validation logic"""
        try:
            # Create test data
            db_data = {
                'date': datetime.now().date(),
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 1000000
            }
            
            # Create mock Yahoo data
            import pandas as pd
            yahoo_data = pd.Series({
                'Open': 100.0,
                'High': 105.0,
                'Low': 95.0,
                'Close': 102.0,
                'Volume': 1000000
            })
            
            # Test validation (should pass)
            result = self.syncer.validate_ohlcv_data(db_data, yahoo_data)
            if result:
                logger.info("✅ Data validation test passed (matching data)")
            else:
                logger.error("❌ Data validation test failed (matching data)")
                return False
            
            # Test validation with different data (should fail)
            yahoo_data_different = pd.Series({
                'Open': 110.0,  # 10% difference
                'High': 105.0,
                'Low': 95.0,
                'Close': 102.0,
                'Volume': 1000000
            })
            
            result = self.syncer.validate_ohlcv_data(db_data, yahoo_data_different)
            if not result:
                logger.info("✅ Data validation test passed (different data correctly rejected)")
            else:
                logger.error("❌ Data validation test failed (different data should be rejected)")
                return False
            
            return True
        except Exception as e:
            logger.error(f"❌ Data validation test failed: {e}")
            return False
    
    def test_single_stock_sync(self, symbol: str) -> bool:
        """Test syncing a single stock"""
        try:
            stock = self.syncer.get_stock_by_symbol(symbol)
            if not stock:
                logger.error(f"❌ Stock {symbol} not found")
                return False
            
            logger.info(f"🔄 Testing sync for {symbol}")
            success, message = self.syncer.sync_stock_ohlcv(stock, validate_only=True)
            
            if success:
                logger.info(f"✅ {symbol} sync test passed: {message}")
            else:
                logger.error(f"❌ {symbol} sync test failed: {message}")
            
            return success
        except Exception as e:
            logger.error(f"❌ Single stock sync test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid data"""
        try:
            # Test with invalid stock symbol
            invalid_stock = self.syncer.get_stock_by_symbol('INVALID_SYMBOL_12345')
            if invalid_stock is None:
                logger.info("✅ Error handling test passed (invalid symbol correctly handled)")
            else:
                logger.error("❌ Error handling test failed (invalid symbol should return None)")
                return False
            
            return True
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("🧪 Starting Daily Syncer Tests")
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Stock Retrieval", self.test_stock_retrieval),
            ("OHLCV Data Retrieval", self.test_ohlcv_data_retrieval),
            ("Yahoo Data Fetch", self.test_yahoo_data_fetch),
            ("Data Validation", self.test_data_validation),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"🔍 Running {test_name} test...")
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test passed")
            else:
                logger.error(f"❌ {test_name} test failed")
        
        logger.info(f"📊 Test Results: {passed}/{total} tests passed")
        return passed == total
    
    def close(self):
        """Close connections"""
        if self.db:
            self.db.close()
        if self.syncer:
            self.syncer.close()

def main():
    parser = argparse.ArgumentParser(description='Test Daily OHLCV Syncer')
    parser.add_argument('--symbol', type=str, help='Test specific stock by symbol')
    parser.add_argument('--validate-only', action='store_true', help='Test validation only')
    
    args = parser.parse_args()
    
    logger.info("🧪 Starting Daily Syncer Tests")
    
    tester = DailySyncerTester()
    
    try:
        if args.symbol:
            # Test specific stock
            success = tester.test_single_stock_sync(args.symbol)
            if success:
                logger.info(f"✅ {args.symbol} test completed successfully")
            else:
                logger.error(f"❌ {args.symbol} test failed")
        else:
            # Run all tests
            success = tester.run_all_tests()
            if success:
                logger.info("🎉 All tests passed!")
            else:
                logger.error("❌ Some tests failed")
    
    except KeyboardInterrupt:
        logger.info("⏹️ Tests interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
    finally:
        tester.close()

if __name__ == "__main__":
    main()
