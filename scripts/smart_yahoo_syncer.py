#!/usr/bin/env python3
"""
Smart Incremental Yahoo Finance Data Syncer
Features:
- Tracks last update times for each data type
- Only fetches new/updated data
- Implements smart caching
- Efficient incremental syncing
"""

import logging
import sys
import os
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache
import yfinance as yf
import pandas as pd

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.stock import Stock, DailyPrice, FinancialStatement, News, Announcement, SyncTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/smart_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = 300  # 5 minutes cache TTL
CACHE_SIZE = 1000  # Maximum cache entries

class SmartYahooSyncer:
    """Smart incremental data syncer with caching"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
    
    def get_db_session(self):
        """Get a fresh database session"""
        return SessionLocal()
    
    def close_session(self, session):
        """Safely close a database session"""
        try:
            if session:
                session.close()
        except Exception as e:
            logger.warning(f"Error closing session: {e}")
    
    def safe_db_operation(self, operation_func, *args, **kwargs):
        """Safely execute database operations with session management"""
        session = None
        try:
            session = self.get_db_session()
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            if session:
                try:
                    session.rollback()
                except:
                    pass
            raise e
        finally:
            self.close_session(session)
    
    def get_cache_key(self, symbol: str, data_type: str, **kwargs) -> str:
        """Generate cache key for data"""
        key_parts = [symbol, data_type] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < CACHE_TTL:
                logger.debug(f"Cache hit for {cache_key}")
                return self.cache[cache_key]
            else:
                # Expired cache, remove it
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]
        return None
    
    def set_cached_data(self, cache_key: str, data: Any):
        """Set data in cache with timestamp"""
        # Implement LRU cache eviction
        if len(self.cache) >= CACHE_SIZE:
            # Remove oldest entry
            oldest_key = min(self.cache_timestamps.keys(), key=lambda k: self.cache_timestamps[k])
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
        
        self.cache[cache_key] = data
        self.cache_timestamps[cache_key] = time.time()
        logger.debug(f"Cached data for {cache_key}")
    
    def get_sync_tracker(self, stock_id: int, data_type: str) -> Optional[Dict[str, Any]]:
        """Get or create sync tracker for a stock and data type, return as dictionary to avoid session binding issues"""
        def _get_tracker(session):
            tracker = session.query(SyncTracker).filter(
                SyncTracker.stock_id == stock_id,
                SyncTracker.data_type == data_type
            ).first()
            
            if not tracker:
                tracker = SyncTracker(
                    stock_id=stock_id,
                    data_type=data_type,
                    last_sync_time=datetime.utcnow()
                )
                session.add(tracker)
                # Flush to get the ID
                session.flush()
            
            return {
                'id': tracker.id,
                'stock_id': tracker.stock_id,
                'data_type': tracker.data_type,
                'last_sync_time': tracker.last_sync_time,
                'last_data_date': tracker.last_data_date,
                'records_count': tracker.records_count,
                'sync_status': tracker.sync_status,
                'error_message': tracker.error_message
            }
        
        return self.safe_db_operation(_get_tracker)
    
    def update_sync_tracker(self, stock_id: int, data_type: str, last_data_date: datetime, 
                           records_count: int, status: str = 'success', error_msg: str = None):
        """Update sync tracker with latest sync information"""
        def _update_tracker(session):
            # Get fresh tracker from the session
            tracker = session.query(SyncTracker).filter(
                SyncTracker.stock_id == stock_id,
                SyncTracker.data_type == data_type
            ).first()
            
            if tracker:
                tracker.last_sync_time = datetime.utcnow()
                tracker.last_data_date = last_data_date
                tracker.records_count = records_count
                tracker.sync_status = status
                tracker.error_message = error_msg
        
        self.safe_db_operation(_update_tracker)
    
    def get_stock_from_db(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock from database and return as dictionary to avoid session binding issues"""
        def _get_stock(session):
            stock = session.query(Stock).filter(Stock.nse_symbol == symbol).first()
            if stock:
                return {
                    'id': stock.id,
                    'nse_symbol': stock.nse_symbol,
                    'name': stock.name
                }
            return None
        
        return self.safe_db_operation(_get_stock)
    
    def smart_sync_ohlcv(self, stock_id: int, stock_symbol: str, ticker: yf.Ticker) -> int:
        """Smart sync OHLCV data - only fetch new data"""
        try:
            tracker = self.get_sync_tracker(stock_id, 'ohlcv')
            
            # Determine start date for data fetch
            if tracker['last_data_date']:
                start_date = tracker['last_data_date'] + timedelta(days=1)
                logger.info(f"Fetching OHLCV data for {stock_symbol} from {start_date}")
            else:
                start_date = datetime.now() - timedelta(days=365)  # First time sync
                logger.info(f"First time OHLCV sync for {stock_symbol} from {start_date}")
            
            # Check if we need to fetch data
            if tracker['last_data_date'] and (datetime.now() - tracker['last_data_date']).days < 1:
                logger.info(f"OHLCV data for {stock_symbol} is up to date (last update: {tracker['last_data_date']})")
                return 0
            
            # Fetch data with caching
            cache_key = self.get_cache_key(stock_symbol, 'ohlcv', start_date=start_date.strftime('%Y-%m-%d'))
            cached_data = self.get_cached_data(cache_key)
            
            if cached_data is not None:
                historical_data = cached_data
            else:
                historical_data = ticker.history(start=start_date, end=datetime.now())
                self.set_cached_data(cache_key, historical_data)
            
            if historical_data.empty:
                logger.warning(f"No new OHLCV data for {stock_symbol}")
                return 0
            
            def _save_ohlcv_data(session):
                saved_count = 0
                last_date = None
                
                for date, row in historical_data.iterrows():
                    # Check if price data already exists
                    existing = session.query(DailyPrice).filter(
                        DailyPrice.stock_id == stock_id,
                        DailyPrice.date == date.date()
                    ).first()
                    
                    if not existing:
                        # Create new daily price record
                        daily_price = DailyPrice(
                            stock_id=stock_id,
                            date=date.date(),
                            open_price=float(row['Open']),
                            high_price=float(row['High']),
                            low_price=float(row['Low']),
                            close_price=float(row['Close']),
                            volume=int(row['Volume'])
                        )
                        session.add(daily_price)
                        saved_count += 1
                        last_date = date
                
                return saved_count, last_date
            
            saved_count, last_date = self.safe_db_operation(_save_ohlcv_data)
            
            if saved_count > 0:
                logger.info(f"✅ Saved {saved_count} new OHLCV records for {stock_symbol}")
                
                # Update sync tracker
                if last_date:
                    self.update_sync_tracker(stock_id, 'ohlcv', last_date, saved_count)
            else:
                logger.info(f"No new OHLCV data to save for {stock_symbol}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error syncing OHLCV for {stock_symbol}: {e}")
            # Get last_data_date safely
            tracker = self.get_sync_tracker(stock_id, 'ohlcv')
            last_data_date = tracker['last_data_date'] if tracker else None
            self.update_sync_tracker(stock_id, 'ohlcv', last_data_date, 0, 'failed', str(e))
            return 0
    
    def smart_sync_news(self, stock_id: int, stock_symbol: str, ticker: yf.Ticker) -> int:
        """Smart sync news data - only fetch new articles"""
        def _save_news_data(session):
            tracker = self.get_sync_tracker(stock_id, 'news')
            
            # Check if we need to fetch news (news changes frequently)
            if tracker['last_sync_time'] and (datetime.utcnow() - tracker['last_sync_time']).total_seconds() < 3600:  # 1 hour
                logger.info(f"News for {stock_symbol} was recently synced (last sync: {tracker['last_sync_time']})")
                return 0, None
            
            # Fetch news with caching
            cache_key = self.get_cache_key(stock_symbol, 'news')
            cached_data = self.get_cached_data(cache_key)
            
            if cached_data is not None:
                news_data = cached_data
            else:
                news_data = ticker.news
                self.set_cached_data(cache_key, news_data)
            
            if not news_data:
                logger.warning(f"No news data for {stock_symbol}")
                return 0, None
            
            saved_count = 0
            latest_news_date = None
            
            for news_item in news_data:
                if 'content' in news_item and isinstance(news_item['content'], dict):
                    content_data = news_item['content']
                    
                    # Extract news information
                    title = content_data.get('title') or content_data.get('headline') or 'No Title'
                    content = content_data.get('summary') or content_data.get('description') or 'No content'
                    source = content_data.get('source') or 'Unknown'
                    url = content_data.get('url') or ''
                    
                    # Parse published date
                    try:
                        published_date = pd.to_datetime(content_data.get('publishedTime', datetime.now()))
                    except:
                        published_date = datetime.now()
                    
                    # Check if news already exists
                    existing = session.query(News).filter(
                        News.stock_id == stock_id,
                        News.title == title,
                        News.published_date == published_date
                    ).first()
                    
                    if not existing:
                        # Create new news record
                        news = News(
                            stock_id=stock_id,
                            title=title,
                            content=content,
                            source=source,
                            url=url,
                            published_date=published_date
                        )
                        session.add(news)
                        saved_count += 1
                        
                        if not latest_news_date or published_date > latest_news_date:
                            latest_news_date = published_date
            
            return saved_count, latest_news_date
        
        try:
            saved_count, latest_news_date = self.safe_db_operation(_save_news_data)
            
            if saved_count > 0:
                logger.info(f"✅ Saved {saved_count} new news records for {stock_symbol}")
                
                # Update sync tracker
                if latest_news_date:
                    self.update_sync_tracker(stock_id, 'news', latest_news_date, saved_count)
            else:
                logger.info(f"No new news to save for {stock_symbol}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error syncing news for {stock_symbol}: {e}")
            # Get last_data_date safely
            tracker = self.get_sync_tracker(stock_id, 'news')
            last_data_date = tracker['last_data_date'] if tracker else None
            self.update_sync_tracker(stock_id, 'news', last_data_date, 0, 'failed', str(e))
            return 0
    
    def smart_sync_financials(self, stock_id: int, stock_symbol: str, ticker: yf.Ticker) -> int:
        """Smart sync financial data - only fetch new statements"""
        def _save_financials_data(session):
            tracker = self.get_sync_tracker(stock_id, 'financials')
            
            # Financial data doesn't change frequently, check weekly
            if tracker['last_sync_time'] and (datetime.utcnow() - tracker['last_sync_time']).days < 7:
                logger.info(f"Financials for {stock_symbol} were recently synced (last sync: {tracker['last_sync_time']})")
                return 0, None
            
            saved_count = 0
            latest_date = None
            
            # Sync quarterly financials
            try:
                quarterly_data = ticker.quarterly_financials
                if not quarterly_data.empty:
                    for date, row in quarterly_data.iterrows():
                        # Check if financial statement already exists
                        existing = session.query(FinancialStatement).filter(
                            FinancialStatement.stock_id == stock_id,
                            FinancialStatement.statement_type == 'quarterly_financials',
                            FinancialStatement.year == date.year,
                            FinancialStatement.quarter == (date.month - 1) // 3 + 1
                        ).first()
                        
                        if not existing:
                            financial = FinancialStatement(
                                stock_id=stock_id,
                                statement_type='quarterly_financials',
                                period='Quarterly',
                                year=date.year,
                                quarter=(date.month - 1) // 3 + 1,
                                data=row.to_json(),
                                is_consolidated=True,
                                filing_date=date
                            )
                            session.add(financial)
                            saved_count += 1
                            
                            if not latest_date or date > latest_date:
                                latest_date = date
            except Exception as e:
                logger.warning(f"Error fetching quarterly financials for {stock_symbol}: {e}")
            
            # Sync cash flow
            try:
                cashflow_data = ticker.cashflow
                if not cashflow_data.empty:
                    for date, row in cashflow_data.iterrows():
                        existing = session.query(FinancialStatement).filter(
                            FinancialStatement.stock_id == stock_id,
                            FinancialStatement.statement_type == 'cash_flow',
                            FinancialStatement.year == date.year
                        ).first()
                        
                        if not existing:
                            cashflow = FinancialStatement(
                                stock_id=stock_id,
                                statement_type='cash_flow',
                                period='Annual',
                                year=date.year,
                                quarter=None,
                                data=row.to_json(),
                                is_consolidated=True,
                                filing_date=date
                            )
                            session.add(cashflow)
                            saved_count += 1
                            
                            if not latest_date or date > latest_date:
                                latest_date = date
            except Exception as e:
                logger.warning(f"Error fetching cash flow for {stock_symbol}: {e}")
            
            return saved_count, latest_date
        
        try:
            saved_count, latest_date = self.safe_db_operation(_save_financials_data)
            
            if saved_count > 0:
                logger.info(f"✅ Saved {saved_count} new financial records for {stock_symbol}")
                
                # Update sync tracker
                if latest_date:
                    self.update_sync_tracker(stock_id, 'financials', latest_date, saved_count)
            else:
                logger.info(f"No new financial data to save for {stock_symbol}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error syncing financials for {stock_symbol}: {e}")
            # Get last_data_date safely
            tracker = self.get_sync_tracker(stock_id, 'financials')
            last_data_date = tracker['last_data_date'] if tracker else None
            self.update_sync_tracker(stock_id, 'financials', last_data_date, 0, 'failed', str(e))
            return 0
    
    def smart_sync_earnings(self, stock_id: int, stock_symbol: str, ticker: yf.Ticker) -> int:
        """Smart sync earnings data"""
        def _save_earnings_data(session):
            tracker = self.get_sync_tracker(stock_id, 'earnings')
            
            # Earnings data changes quarterly, check monthly
            if tracker['last_sync_time'] and (datetime.utcnow() - tracker['last_sync_time']).days < 30:
                logger.info(f"Earnings for {stock_symbol} were recently synced (last sync: {tracker['last_sync_time']})")
                return 0, None
            
            saved_count = 0
            latest_date = None
            
            # Sync earnings dates
            try:
                earnings_dates = ticker.earnings_dates
                if not earnings_dates.empty:
                    for date, row in earnings_dates.iterrows():
                        # Check if earnings date already exists
                        existing = session.query(Announcement).filter(
                            Announcement.stock_id == stock_id,
                            Announcement.title.like('%Earnings%'),
                            Announcement.announcement_date == date
                        ).first()
                        
                        if not existing:
                            announcement = Announcement(
                                stock_id=stock_id,
                                title=f"Earnings Announcement - {date.strftime('%B %Y')}",
                                content=f"Earnings date: {date.strftime('%B %d, %Y')}",
                                announcement_date=date,
                                announcement_type='Earnings'
                            )
                            session.add(announcement)
                            saved_count += 1
                            
                            if not latest_date or date > latest_date:
                                latest_date = date
            except Exception as e:
                logger.warning(f"Error fetching earnings dates for {stock_symbol}: {e}")
            
            return saved_count, latest_date
        
        try:
            saved_count, latest_date = self.safe_db_operation(_save_earnings_data)
            
            if saved_count > 0:
                logger.info(f"✅ Saved {saved_count} new earnings records for {stock_symbol}")
                
                # Update sync tracker
                if latest_date:
                    self.update_sync_tracker(stock_id, 'earnings', latest_date, saved_count)
            else:
                logger.info(f"No new earnings data to save for {stock_symbol}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error syncing earnings for {stock_symbol}: {e}")
            # Get last_data_date safely
            tracker = self.get_sync_tracker(stock_id, 'earnings')
            last_data_date = tracker['last_data_date'] if tracker else None
            self.update_sync_tracker(stock_id, 'earnings', last_data_date, 0, 'failed', str(e))
            return 0
    
    def sync_stock_data(self, symbol: str) -> Dict[str, int]:
        """Sync all data type for a single stock"""
        try:
            logger.info(f"🔄 Smart syncing data for {symbol}")
            
            # Get stock from database
            stock_data = self.get_stock_from_db(symbol)
            if not stock_data:
                logger.warning(f"Stock {symbol} not found in database, skipping")
                return {}
            
            # Extract stock info from dictionary
            stock_id = stock_data['id']
            stock_symbol = stock_data['nse_symbol']
            
            # Initialize Yahoo Finance ticker
            ticker = yf.Ticker(symbol)
            
            results = {}
            
            # Sync each data type with smart logic
            results['ohlcv'] = self.smart_sync_ohlcv(stock_id, stock_symbol, ticker)
            results['news'] = self.smart_sync_news(stock_id, stock_symbol, ticker)
            results['financials'] = self.smart_sync_financials(stock_id, stock_symbol, ticker)
            results['earnings'] = self.smart_sync_earnings(stock_id, stock_symbol, ticker)
            
            logger.info(f"✅ Completed smart sync for {symbol}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error syncing data for {symbol}: {e}")
            return {}
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get summary of sync status for all stocks"""
        def _get_summary(session):
            summary = {
                'total_stocks': 0,
                'sync_status': {},
                'last_sync_times': {},
                'data_counts': {}
            }
            
            stocks = session.query(Stock).all()
            summary['total_stocks'] = len(stocks)
            
            for stock in stocks:
                trackers = session.query(SyncTracker).filter(SyncTracker.stock_id == stock.id).all()
                
                summary['sync_status'][stock.nse_symbol] = {}
                summary['last_sync_times'][stock.nse_symbol] = {}
                summary['data_counts'][stock.nse_symbol] = {}
                
                for tracker in trackers:
                    summary['sync_status'][stock.nse_symbol][tracker.data_type] = tracker.sync_status
                    summary['last_sync_times'][stock.nse_symbol][tracker.data_type] = tracker.last_sync_time
                    summary['data_counts'][stock.nse_symbol][tracker.data_type] = tracker.records_count
            
            return summary
        
        try:
            return self.safe_db_operation(_get_summary)
        except Exception as e:
            logger.error(f"Error getting sync summary: {e}")
            return {}

def main():
    """Main function to run smart sync"""
    logger.info("🚀 Starting Smart Yahoo Finance Data Sync")
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Initialize syncer
    syncer = SmartYahooSyncer()
    
    try:
        # Test with a few stocks first
        test_symbols = [
    "ASIANPAINT.NS", "BAJFINANCE.NS", "BRITANNIA.NS", "CIPLA.NS",
    "EICHERMOT.NS", "HDFCBANK.NS", "INDHOTEL.NS", "INDIGO.NS", 
    "RELIANCE.NS", "TITAN.NS", "WIPRO.NS", "ZEEL.NS"
]
        
        total_results = {
            'ohlcv': 0,
            'news': 0,
            'financials': 0,
            'earnings': 0
        }
        
        success_count = 0
        error_count = 0
        
        for i, symbol in enumerate(test_symbols, 1):
            logger.info(f"🔄 Processing {i}/{len(test_symbols)}: {symbol}")
            
            try:
                # Sync data for this stock
                results = syncer.sync_stock_data(symbol)
                
                if results:
                    # Update totals
                    for key in total_results:
                        total_results[key] += results.get(key, 0)
                    success_count += 1
                else:
                    error_count += 1
                
                # Add delay to avoid overwhelming Yahoo Finance
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error processing {symbol}: {e}")
                error_count += 1
                continue
        
        # Summary
        logger.info("🎉 Smart sync completed!")
        logger.info(f"✅ Success: {success_count}")
        logger.info(f"❌ Errors: {error_count}")
        logger.info("📊 Total data synced:")
        for key, value in total_results.items():
            logger.info(f"  • {key}: {value}")
        
        # Get sync summary
        summary = syncer.get_sync_summary()
        logger.info("📋 Sync Summary:")
        logger.info(f"  • Total stocks: {summary['total_stocks']}")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        
    finally:
        # Clean up
        pass

if __name__ == "__main__":
    main()
