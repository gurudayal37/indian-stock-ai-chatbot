#!/usr/bin/env python3
"""
Nifty 50 Stock Database Populator

This script populates the database with all Nifty 50 stocks using Yahoo Finance ticker.info.
It automatically handles new stocks added to the list and updates existing stock information.
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.stock import Stock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nifty50_population.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Nifty 50 stock symbols (with .NS suffix for Yahoo Finance)
NIFTY_50_SYMBOLS = [
    "ABB.NS", "ACC.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "AMBUJACEM.NS",
    "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS",
    "BANDHANBNK.NS", "BANKBARODA.NS", "BERGEPAINT.NS", "BHARTIARTL.NS", "BIOCON.NS",
    "BPCL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "COLPAL.NS",
    "CONCOR.NS", "DABUR.NS", "DIVISLAB.NS", "DLF.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GAIL.NS", "GLAND.NS", "GLENMARK.NS", "GMRINFRA.NS",
    "GODREJCP.NS", "GRASIM.NS", "HAVELLS.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "HINDPETRO.NS", "HINDUNILVR.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "ICICIBANK.NS", "ICICIPRULI.NS", "INDHOTEL.NS", "INDIGO.NS", "INDUSINDBK.NS",
    "INFY.NS", "IOC.NS", "ITC.NS", "JSWSTEEL.NS", "JUBLFOOD.NS",
    "KOTAKBANK.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "MARICO.NS",
    "MARUTI.NS", "MFSL.NS", "NAUKRI.NS", "NAVINFLUOR.NS",
    "NESTLEIND.NS", "NMDC.NS", "ONGC.NS", "PIIND.NS", "PIDILITIND.NS",
    "PNB.NS", "POWERGRID.NS", "RELIANCE.NS", "SBICARD.NS", "SBILIFE.NS",
    "SBIN.NS", "SHREECEM.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS",
    "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS",
    "TITAN.NS", "TORNTPHARM.NS", "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS",
    "WIPRO.NS", "ZEEL.NS"
]

class Nifty50StockPopulator:
    """Populates database with Nifty 50 stocks using Yahoo Finance data"""
    
    def __init__(self):
        self.db: Optional[Session] = None
        self.stats = {
            'total_processed': 0,
            'new_stocks_added': 0,
            'existing_stocks_updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def get_db_session(self) -> Session:
        """Get a fresh database session"""
        return SessionLocal()
    
    def close_session(self, session: Session):
        """Close database session"""
        if session:
            session.close()
    
    def safe_db_operation(self, operation_func, *args, **kwargs):
        """Safely execute database operations with proper session handling"""
        session = self.get_db_session()
        try:
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)
    
    def get_stock_info_from_yahoo(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock information from Yahoo Finance ticker.info"""
        try:
            logger.info(f"Fetching info for {symbol}")
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"No valid info found for {symbol}")
                return None
            
            # Extract and clean the data
            stock_data = {
                'nse_symbol': symbol.replace('.NS', ''),
                'name': info.get('longName', info.get('shortName', 'Unknown')),
                'isin': info.get('isin') or f"IN_{symbol.replace('.NS', '')}_YF",  # Generate unique ISIN-like identifier
                'bse_symbol': f"{info.get('symbol', '').replace('.NS', '')}_{symbol.replace('.NS', '')}",  # Make BSE symbol unique by appending NSE symbol
                'current_price': info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'face_value': info.get('faceValue', 10.0),
                'high_52_week': info.get('fiftyTwoWeekHigh'),
                'low_52_week': info.get('fiftyTwoWeekLow'),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'book_value': info.get('bookValue'),
                'dividend_yield': info.get('dividendYield'),
                'roce': None,  # Not available in Yahoo Finance
                'roe': info.get('returnOnEquity'),
                'industry': info.get('industry'),
                'sector': info.get('sector'),
                'subsector': None,  # Not available in Yahoo Finance
                'subsector1': None,
                'subsector2': None,
                'subsector3': None,
                'is_active': True
            }
            
            # Clean up None values
            stock_data = {k: v for k, v in stock_data.items() if v is not None}
            
            logger.info(f"Successfully fetched info for {symbol}: {stock_data['name']}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None
    
    def check_stock_exists(self, session: Session, nse_symbol: str) -> Optional[Stock]:
        """Check if stock already exists in database"""
        return session.query(Stock).filter(Stock.nse_symbol == nse_symbol).first()
    
    def add_new_stock(self, session: Session, stock_data: Dict[str, Any]) -> Stock:
        """Add new stock to database"""
        stock = Stock(**stock_data)
        session.add(stock)
        session.flush()  # Get the ID
        logger.info(f"Added new stock: {stock_data['name']} ({stock_data['nse_symbol']})")
        return stock
    
    def update_existing_stock(self, session: Session, stock: Stock, stock_data: Dict[str, Any]) -> Stock:
        """Update existing stock information"""
        # Update fields that might have changed
        updateable_fields = [
            'current_price', 'market_cap', 'high_52_week', 'low_52_week',
            'pe_ratio', 'pb_ratio', 'book_value', 'dividend_yield', 'roe',
            'industry', 'sector', 'name'
        ]
        
        updated = False
        for field in updateable_fields:
            if field in stock_data and getattr(stock, field) != stock_data[field]:
                setattr(stock, field, stock_data[field])
                updated = True
        
        if updated:
            stock.last_updated = datetime.utcnow()
            stock.updated_at = datetime.utcnow()
            logger.info(f"Updated stock: {stock_data['name']} ({stock_data['nse_symbol']})")
        
        return stock
    
    def process_stock(self, symbol: str) -> bool:
        """Process a single stock symbol"""
        try:
            # Get stock info from Yahoo Finance
            stock_data = self.get_stock_info_from_yahoo(symbol)
            if not stock_data:
                self.stats['errors'] += 1
                return False
            
            # Process in database
            def _process_stock_db(session):
                nse_symbol = stock_data['nse_symbol']
                existing_stock = self.check_stock_exists(session, nse_symbol)
                
                if existing_stock:
                    # Update existing stock
                    self.update_existing_stock(session, existing_stock, stock_data)
                    self.stats['existing_stocks_updated'] += 1
                    logger.info(f"Updated existing stock: {stock_data['name']} ({nse_symbol})")
                else:
                    # Add new stock
                    self.add_new_stock(session, stock_data)
                    self.stats['new_stocks_added'] += 1
                    logger.info(f"Added new stock: {stock_data['name']} ({nse_symbol})")
                
                return True
            
            success = self.safe_db_operation(_process_stock_db)
            if success:
                self.stats['total_processed'] += 1
                logger.info(f"✅ Successfully processed {symbol}")
            return success
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_current_database_stocks(self) -> List[str]:
        """Get list of NSE symbols currently in database"""
        def _get_stocks(session):
            stocks = session.query(Stock.nse_symbol).all()
            return [stock[0] for stock in stocks]
        
        return self.safe_db_operation(_get_stocks)
    
    def find_new_stocks(self) -> List[str]:
        """Find stocks that are in Nifty 50 but not in database"""
        current_stocks = set(self.get_current_database_stocks())
        nifty_stocks = set([symbol.replace('.NS', '') for symbol in NIFTY_50_SYMBOLS])
        
        new_stocks = nifty_stocks - current_stocks
        return [f"{symbol}.NS" for symbol in new_stocks]
    
    def find_removed_stocks(self) -> List[str]:
        """Find stocks that are in database but no longer in Nifty 50"""
        current_stocks = set(self.get_current_database_stocks())
        nifty_stocks = set([symbol.replace('.NS', '') for symbol in NIFTY_50_SYMBOLS])
        
        removed_stocks = current_stocks - nifty_stocks
        return list(removed_stocks)
    
    def fix_duplicate_isin_issues(self):
        """Fix stocks with duplicate or problematic ISIN values"""
        def _fix_isin(session):
            # Find stocks with 'Unknown' ISIN
            problematic_stocks = session.query(Stock).filter(Stock.isin == 'Unknown').all()
            
            for stock in problematic_stocks:
                # Generate unique ISIN-like identifier
                new_isin = f"IN_{stock.nse_symbol}_YF"
                stock.isin = new_isin
                stock.updated_at = datetime.utcnow()
                logger.info(f"Fixed ISIN for {stock.nse_symbol}: {new_isin}")
            
            return len(problematic_stocks)
        
        try:
            fixed_count = self.safe_db_operation(_fix_isin)
            if fixed_count > 0:
                logger.info(f"🔧 Fixed ISIN issues for {fixed_count} stocks")
            return fixed_count
        except Exception as e:
            logger.error(f"Error fixing ISIN issues: {e}")
            return 0
    
    def fix_duplicate_bse_symbol_issues(self):
        """Fix stocks with duplicate BSE symbol values"""
        def _fix_bse_symbol(session):
            # Find stocks with duplicate BSE symbols
            from sqlalchemy import func
            duplicate_bse = session.query(
                Stock.bse_symbol, 
                func.count(Stock.id)
            ).group_by(Stock.bse_symbol).having(func.count(Stock.id) > 1).all()
            
            fixed_count = 0
            for bse_symbol, count in duplicate_bse:
                if bse_symbol and '_' not in bse_symbol:  # Only fix if not already fixed
                    stocks_with_duplicate = session.query(Stock).filter(
                        Stock.bse_symbol == bse_symbol
                    ).all()
                    
                    for i, stock in enumerate(stocks_with_duplicate):
                        if i > 0:  # Keep first one as is, fix others
                            new_bse_symbol = f"{bse_symbol}_{stock.nse_symbol}"
                            stock.bse_symbol = new_bse_symbol
                            stock.updated_at = datetime.utcnow()
                            logger.info(f"Fixed BSE symbol for {stock.nse_symbol}: {new_bse_symbol}")
                            fixed_count += 1
            
            return fixed_count
        
        try:
            fixed_count = self.safe_db_operation(_fix_bse_symbol)
            if fixed_count > 0:
                logger.info(f"🔧 Fixed BSE symbol issues for {fixed_count} stocks")
            return fixed_count
        except Exception as e:
            logger.error(f"Error fixing BSE symbol issues: {e}")
            return 0
    
    def populate_all_stocks(self):
        """Populate database with all Nifty 50 stocks"""
        logger.info("🚀 Starting Nifty 50 Stock Database Population")
        logger.info(f"📊 Total symbols to process: {len(NIFTY_50_SYMBOLS)}")
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Check for new and removed stocks
        new_stocks = self.find_new_stocks()
        removed_stocks = self.find_removed_stocks()
        
        if new_stocks:
            logger.info(f"🆕 Found {len(new_stocks)} new stocks to add: {', '.join(new_stocks)}")
        
        if removed_stocks:
            logger.info(f"🗑️ Found {len(removed_stocks)} stocks no longer in Nifty 50: {', '.join(removed_stocks)}")
        
        # Fix any existing ISIN issues first
        logger.info("🔧 Checking for existing ISIN issues...")
        fixed_count = self.fix_duplicate_isin_issues()
        if fixed_count > 0:
            logger.info(f"✅ Fixed {fixed_count} ISIN issues before proceeding")
        
        # Fix any existing BSE symbol issues
        logger.info("🔧 Checking for existing BSE symbol issues...")
        bse_fixed_count = self.fix_duplicate_bse_symbol_issues()
        if bse_fixed_count > 0:
            logger.info(f"✅ Fixed {bse_fixed_count} BSE symbol issues before proceeding")
        
        # Process all stocks
        for i, symbol in enumerate(NIFTY_50_SYMBOLS, 1):
            logger.info(f"🔄 Processing {i}/{len(NIFTY_50_SYMBOLS)}: {symbol}")
            
            success = self.process_stock(symbol)
            
            if success:
                logger.info(f"✅ Successfully processed {symbol}")
            else:
                logger.error(f"❌ Failed to process {symbol}")
            
            # Add delay to avoid overwhelming Yahoo Finance
            if i < len(NIFTY_50_SYMBOLS):
                time.sleep(1)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary"""
        logger.info("🎉 Nifty 50 Stock Population Complete!")
        logger.info("=" * 50)
        logger.info(f"📊 Total Processed: {self.stats['total_processed']}")
        logger.info(f"🆕 New Stocks Added: {self.stats['new_stocks_added']}")
        logger.info(f"🔄 Existing Stocks Updated: {self.stats['existing_stocks_updated']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"⏭️ Skipped: {self.stats['skipped']}")
        logger.info("=" * 50)
        
        if self.stats['errors'] > 0:
            logger.warning(f"⚠️ {self.stats['errors']} stocks had errors. Check logs for details.")
        
        if self.stats['new_stocks_added'] > 0:
            logger.info(f"🎯 Successfully added {self.stats['new_stocks_added']} new stocks to database!")
        
        if self.stats['existing_stocks_updated'] > 0:
            logger.info(f"🔄 Updated information for {self.stats['existing_stocks_updated']} existing stocks!")

def main():
    """Main function"""
    try:
        populator = Nifty50StockPopulator()
        populator.populate_all_stocks()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
