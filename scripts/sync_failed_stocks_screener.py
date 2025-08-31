#!/usr/bin/env python3
"""
Sync Only Failed Stocks - Screener.in Quarterly Results

This script identifies and syncs only the stocks that failed in the previous comprehensive sync.
It's designed to be run after the main sync to catch the failed stocks.

Usage:
    python scripts/sync_failed_stocks_screener.py
"""

import logging
from typing import List
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.stock import Stock, QuarterlyResult
from scripts.screener_quarterly_syncer import ScreenerQuarterlySyncer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_failed_stocks_screener.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FailedStocksScreenerSyncer:
    def __init__(self):
        self.syncer = ScreenerQuarterlySyncer()
        self.db = SessionLocal()
        
    def get_failed_stocks(self) -> List[Stock]:
        """Get stocks that don't have Screener.in quarterly data"""
        try:
            # Get stocks that already have Screener.in data
            existing_screener_stocks = self.db.query(QuarterlyResult.stock_id).filter(
                QuarterlyResult.source == 'Screener'
            ).distinct().subquery()
            
            # Get stocks that don't have Screener.in data
            failed_stocks = self.db.query(Stock).filter(
                ~Stock.id.in_(existing_screener_stocks)
            ).all()
            
            logger.info(f"📊 Found {len(failed_stocks)} stocks without Screener.in data")
            return failed_stocks
            
        except Exception as e:
            logger.error(f"❌ Error getting failed stocks: {e}")
            return []
    
    def sync_stock(self, stock: Stock) -> bool:
        """Sync a single stock with Screener.in"""
        try:
            logger.info(f"🔄 Syncing {stock.nse_symbol} ({stock.name})")
            
            # Use the existing syncer logic
            success = self.syncer.sync_stock_quarterly_results(stock)
            
            if success:
                logger.info(f"✅ Successfully synced {stock.nse_symbol}")
                return True
            else:
                logger.warning(f"⚠️ Failed to sync {stock.nse_symbol}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error syncing {stock.nse_symbol}: {e}")
            return False
    
    def sync_failed_stocks(self) -> None:
        """Sync all failed stocks"""
        try:
            failed_stocks = self.get_failed_stocks()
            
            if not failed_stocks:
                logger.info("🎉 All stocks already have Screener.in data!")
                return
            
            total_stocks = len(failed_stocks)
            total_success = 0
            
            logger.info(f"🚀 Starting sync of {total_stocks} failed stocks")
            
            for i, stock in enumerate(failed_stocks, 1):
                logger.info(f"📈 Progress: {i}/{total_stocks} - {stock.nse_symbol}")
                
                if self.sync_stock(stock):
                    total_success += 1
                
                # Small delay between stocks to be respectful
                if i < total_stocks:
                    logger.info("⏳ Waiting 3 seconds before next stock...")
                    import time
                    time.sleep(3)
            
            # Final summary
            logger.info("🎉 Failed stocks sync completed!")
            logger.info(f"📊 Final results:")
            logger.info(f"   Total stocks processed: {total_stocks}")
            logger.info(f"   Successful syncs: {total_success}")
            logger.info(f"   Failed syncs: {total_stocks - total_success}")
            logger.info(f"   Success rate: {(total_success/total_stocks)*100:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Error during failed stocks sync: {e}")
        finally:
            self.db.close()
            self.syncer.close()

def main():
    logger.info("🚀 Starting Failed Stocks Screener.in Syncer")
    
    syncer = FailedStocksScreenerSyncer()
    syncer.sync_failed_stocks()

if __name__ == "__main__":
    main()
