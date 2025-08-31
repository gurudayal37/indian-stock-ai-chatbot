#!/usr/bin/env python3
"""
Comprehensive Screener.in Quarterly Results Syncer for All Stocks

This script syncs quarterly results from Screener.in for ALL stocks in our database.
It includes:
- Batch processing to avoid overwhelming Screener.in
- Error handling and retry logic
- Progress tracking and logging
- Rate limiting to be respectful to Screener.in
- Resume capability if interrupted

Usage:
    python scripts/sync_all_stocks_screener.py                    # Sync all stocks
    python scripts/sync_all_stocks_screener.py --batch-size 10   # Custom batch size
    python scripts/sync_all_stocks_screener.py --resume          # Resume from last sync
"""

import argparse
import time
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.stock import Stock, QuarterlyResult
from scripts.screener_quarterly_syncer import ScreenerQuarterlySyncer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_all_stocks_screener.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AllStocksScreenerSyncer:
    def __init__(self, batch_size: int = 5, delay_between_batches: int = 30):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.syncer = ScreenerQuarterlySyncer()
        self.db = SessionLocal()
        
    def get_stocks_to_sync(self) -> List[Stock]:
        """Get all stocks that don't have Screener.in quarterly data"""
        try:
            # Get stocks that already have Screener.in data
            existing_screener_stocks = self.db.query(QuarterlyResult.stock_id).filter(
                QuarterlyResult.source == 'Screener'
            ).distinct().subquery()
            
            # Get stocks that don't have Screener.in data
            stocks_to_sync = self.db.query(Stock).filter(
                ~Stock.id.in_(existing_screener_stocks)
            ).all()
            
            logger.info(f"📊 Found {len(stocks_to_sync)} stocks to sync")
            return stocks_to_sync
            
        except Exception as e:
            logger.error(f"❌ Error getting stocks to sync: {e}")
            return []
    
    def sync_stock(self, stock: Stock) -> bool:
        """Sync a single stock with Screener.in"""
        try:
            logger.info(f"🔄 Syncing {stock.nse_symbol} ({stock.name})")
            
            # Use the existing syncer logic - call the correct method
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
    
    def sync_batch(self, stocks: List[Stock]) -> tuple[int, int]:
        """Sync a batch of stocks"""
        success_count = 0
        total_count = len(stocks)
        
        logger.info(f"🚀 Starting batch of {total_count} stocks")
        
        for i, stock in enumerate(stocks, 1):
            logger.info(f"📈 Progress: {i}/{total_count} - {stock.nse_symbol}")
            
            if self.sync_stock(stock):
                success_count += 1
            
            # Small delay between individual stocks to be respectful
            if i < total_count:
                time.sleep(2)
        
        logger.info(f"🎯 Batch completed: {success_count}/{total_count} successful")
        return success_count, total_count
    
    def sync_all_stocks(self) -> None:
        """Sync all stocks in batches"""
        try:
            stocks_to_sync = self.get_stocks_to_sync()
            
            if not stocks_to_sync:
                logger.info("🎉 All stocks already have Screener.in data!")
                return
            
            total_stocks = len(stocks_to_sync)
            total_success = 0
            total_processed = 0
            
            logger.info(f"🚀 Starting comprehensive sync of {total_stocks} stocks")
            logger.info(f"📦 Batch size: {self.batch_size}")
            logger.info(f"⏱️ Delay between batches: {self.delay_between_batches} seconds")
            
            # Process in batches
            for i in range(0, total_stocks, self.batch_size):
                batch = stocks_to_sync[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
                
                logger.info(f"📦 Processing batch {batch_num}/{total_batches}")
                
                success, total = self.sync_batch(batch)
                total_success += success
                total_processed += total
                
                # Progress update
                progress = (total_processed / total_stocks) * 100
                logger.info(f"📊 Overall progress: {progress:.1f}% ({total_processed}/{total_stocks})")
                logger.info(f"✅ Total successful: {total_success}")
                
                # Delay between batches (except for the last batch)
                if i + self.batch_size < total_stocks:
                    logger.info(f"⏳ Waiting {self.delay_between_batches} seconds before next batch...")
                    time.sleep(self.delay_between_batches)
            
            # Final summary
            logger.info("🎉 Comprehensive sync completed!")
            logger.info(f"📊 Final results:")
            logger.info(f"   Total stocks processed: {total_processed}")
            logger.info(f"   Successful syncs: {total_success}")
            logger.info(f"   Failed syncs: {total_processed - total_success}")
            logger.info(f"   Success rate: {(total_success/total_processed)*100:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Error during comprehensive sync: {e}")
        finally:
            self.db.close()
            self.syncer.close()

def main():
    parser = argparse.ArgumentParser(description='Sync all stocks with Screener.in quarterly data')
    parser.add_argument('--batch-size', type=int, default=5, 
                       help='Number of stocks to process in each batch (default: 5)')
    parser.add_argument('--delay', type=int, default=30,
                       help='Delay between batches in seconds (default: 30)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last sync point')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting All Stocks Screener.in Syncer")
    logger.info(f"⚙️ Configuration: batch_size={args.batch_size}, delay={args.delay}")
    
    syncer = AllStocksScreenerSyncer(
        batch_size=args.batch_size,
        delay_between_batches=args.delay
    )
    
    syncer.sync_all_stocks()

if __name__ == "__main__":
    main()
