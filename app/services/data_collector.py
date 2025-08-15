import asyncio
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.stock import Stock, DailyPrice, QuarterlyResult, FinancialStatement
from app.core.database import get_db

logger = logging.getLogger(__name__)


class DataCollectorService:
    """Service for collecting stock market data from various sources."""
    
    def __init__(self):
        """Initialize the data collector service."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_nse_data(self, db: Session) -> List[Dict[str, Any]]:
        """Collect data from NSE website."""
        try:
            logger.info("Starting NSE data collection...")
            
            # NSE equity list URL
            nse_url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
            
            # Add delay to respect rate limits
            time.sleep(settings.request_delay)
            
            response = self.session.get(nse_url)
            if response.status_code != 200:
                logger.error(f"NSE API request failed: {response.status_code}")
                return []
            
            data = response.json()
            stocks_data = []
            
            for item in data.get('data', []):
                stock_info = {
                    'name': item.get('symbol'),
                    'nse_symbol': item.get('symbol'),
                    'isin': item.get('isin'),
                    'current_price': float(item.get('lastPrice', 0)),
                    'high_1_day': float(item.get('dayHigh', 0)),
                    'low_1_day': float(item.get('dayLow', 0)),
                    'volume': int(item.get('totalTradedVolume', 0)),
                    'turnover': float(item.get('totalTradedValue', 0)),
                    'face_value': 10.0  # Default face value for Indian stocks
                }
                stocks_data.append(stock_info)
            
            logger.info(f"Collected {len(stocks_data)} stocks from NSE")
            return stocks_data
            
        except Exception as e:
            logger.error(f"Error collecting NSE data: {e}")
            return []
    
    def collect_bse_data(self, db: Session) -> List[Dict[str, Any]]:
        """Collect data from BSE website."""
        try:
            logger.info("Starting BSE data collection...")
            
            # BSE equity list URL (this is a simplified approach)
            bse_url = "https://www.bseindia.com/markets/equity/EQReports/bulk_deals.aspx"
            
            # Add delay to respect rate limits
            time.sleep(settings.request_delay)
            
            # Note: BSE has more complex data structure, this is a placeholder
            # In practice, you'd need to parse the HTML or use their API
            stocks_data = []
            
            logger.info(f"Collected {len(stocks_data)} stocks from BSE")
            return stocks_data
            
        except Exception as e:
            logger.error(f"Error collecting BSE data: {e}")
            return []
    
    def collect_yahoo_finance_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Collect data from Yahoo Finance."""
        try:
            logger.info(f"Starting Yahoo Finance data collection for {len(symbols)} symbols...")
            
            stocks_data = []
            
            for symbol in symbols:
                try:
                    # Add .NS suffix for NSE stocks
                    ticker = yf.Ticker(f"{symbol}.NS")
                    info = ticker.info
                    
                    # Get historical data for technical indicators
                    hist = ticker.history(period="1y")
                    
                    stock_info = {
                        'nse_symbol': symbol,
                        'name': info.get('longName', symbol),
                        'current_price': info.get('currentPrice', 0),
                        'market_cap': info.get('marketCap', 0) / 10000000,  # Convert to crores
                        'pe_ratio': info.get('trailingPE', 0),
                        'pb_ratio': info.get('priceToBook', 0),
                        'book_value': info.get('bookValue', 0),
                        'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                        'face_value': 10.0,
                        'high_52_week': hist['High'].max() if not hist.empty else 0,
                        'low_52_week': hist['Low'].min() if not hist.empty else 0,
                        'industry': info.get('industry', ''),
                        'sector': info.get('sector', '')
                    }
                    
                    stocks_data.append(stock_info)
                    
                    # Add delay to respect rate limits
                    time.sleep(settings.request_delay)
                    
                except Exception as e:
                    logger.warning(f"Error collecting data for {symbol}: {e}")
                    continue
            
            logger.info(f"Collected {len(stocks_data)} stocks from Yahoo Finance")
            return stocks_data
            
        except Exception as e:
            logger.error(f"Error collecting Yahoo Finance data: {e}")
            return []
    
    def collect_daily_prices(self, db: Session, stock_symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Collect daily price data for a specific stock."""
        try:
            logger.info(f"Collecting daily prices for {stock_symbol}")
            
            # Use Yahoo Finance for historical data
            ticker = yf.Ticker(f"{stock_symbol}.NS")
            hist = ticker.history(period=f"{days}d")
            
            prices_data = []
            for date, row in hist.iterrows():
                price_info = {
                    'date': date.to_pydatetime(),
                    'open_price': float(row['Open']),
                    'high_price': float(row['High']),
                    'low_price': float(row['Low']),
                    'close_price': float(row['Close']),
                    'volume': int(row['Volume']),
                    'turnover': float(row['Open'] * row['Volume'])  # Approximate
                }
                prices_data.append(price_info)
            
            logger.info(f"Collected {len(prices_data)} daily prices for {stock_symbol}")
            return prices_data
            
        except Exception as e:
            logger.error(f"Error collecting daily prices for {stock_symbol}: {e}")
            return []
    
    def collect_quarterly_results(self, db: Session, stock_symbol: str) -> List[Dict[str, Any]]:
        """Collect quarterly financial results."""
        try:
            logger.info(f"Collecting quarterly results for {stock_symbol}")
            
            # Use Yahoo Finance for financial data
            ticker = yf.Ticker(f"{stock_symbol}.NS")
            
            # Get quarterly earnings
            quarterly_earnings = ticker.quarterly_earnings
            quarterly_financials = ticker.quarterly_financials
            
            results_data = []
            
            if not quarterly_earnings.empty:
                for date, row in quarterly_earnings.iterrows():
                    quarter_info = {
                        'quarter': f"Q{date.quarter} {date.year}",
                        'year': date.year,
                        'quarter_number': date.quarter,
                        'eps': float(row['Earnings']) if 'Earnings' in row else 0,
                        'is_consolidated': True
                    }
                    results_data.append(quarter_info)
            
            if not quarterly_financials.empty:
                for date, row in quarterly_financials.iterrows():
                    # Find matching quarter result
                    quarter = f"Q{date.quarter} {date.year}"
                    existing_result = next((r for r in results_data if r['quarter'] == quarter), None)
                    
                    if existing_result:
                        existing_result.update({
                            'revenue': float(row.get('Total Revenue', 0)) / 10000000,  # Convert to crores
                            'net_profit': float(row.get('Net Income', 0)) / 10000000,
                            'ebitda': float(row.get('EBITDA', 0)) / 10000000 if 'EBITDA' in row else 0,
                            'operating_profit': float(row.get('Operating Income', 0)) / 10000000 if 'Operating Income' in row else 0
                        })
            
            logger.info(f"Collected {len(results_data)} quarterly results for {stock_symbol}")
            return results_data
            
        except Exception as e:
            logger.error(f"Error collecting quarterly results for {stock_symbol}: {e}")
            return []
    
    def collect_financial_statements(self, db: Session, stock_symbol: str) -> List[Dict[str, Any]]:
        """Collect financial statements (P&L, Balance Sheet, Cash Flow)."""
        try:
            logger.info(f"Collecting financial statements for {stock_symbol}")
            
            # Use Yahoo Finance for financial data
            ticker = yf.Ticker(f"{stock_symbol}.NS")
            
            # Get annual financials
            annual_financials = ticker.financials
            annual_balance = ticker.balance_sheet
            annual_cashflow = ticker.cashflow
            
            statements_data = []
            
            # Process P&L statement
            if not annual_financials.empty:
                for date in annual_financials.columns:
                    year = date.year
                    data = {
                        'statement_type': 'P&L',
                        'period': 'Annual',
                        'year': year,
                        'quarter': None,
                        'data': annual_financials[date].to_json(),
                        'is_consolidated': True
                    }
                    statements_data.append(data)
            
            # Process Balance Sheet
            if not annual_balance.empty:
                for date in annual_balance.columns:
                    year = date.year
                    data = {
                        'statement_type': 'Balance Sheet',
                        'period': 'Annual',
                        'year': year,
                        'quarter': None,
                        'data': annual_balance[date].to_json(),
                        'is_consolidated': True
                    }
                    statements_data.append(data)
            
            # Process Cash Flow
            if not annual_cashflow.empty:
                for date in annual_cashflow.columns:
                    year = date.year
                    data = {
                        'statement_type': 'Cash Flow',
                        'period': 'Annual',
                        'year': year,
                        'quarter': None,
                        'data': annual_cashflow[date].to_json(),
                        'is_consolidated': True
                    }
                    statements_data.append(data)
            
            logger.info(f"Collected {len(statements_data)} financial statements for {stock_symbol}")
            return statements_data
            
        except Exception as e:
            logger.error(f"Error collecting financial statements for {stock_symbol}: {e}")
            return []
    
    def update_stock_database(self, db: Session, stocks_data: List[Dict[str, Any]]) -> int:
        """Update the stock database with collected data."""
        try:
            logger.info("Updating stock database...")
            
            updated_count = 0
            
            for stock_data in stocks_data:
                try:
                    # Check if stock exists
                    stock = db.query(Stock).filter(
                        (Stock.nse_symbol == stock_data.get('nse_symbol')) |
                        (Stock.bse_symbol == stock_data.get('bse_symbol'))
                    ).first()
                    
                    if stock:
                        # Update existing stock
                        for key, value in stock_data.items():
                            if hasattr(stock, key) and value is not None:
                                setattr(stock, key, value)
                        stock.updated_at = datetime.now()
                    else:
                        # Create new stock
                        stock = Stock(**stock_data)
                        db.add(stock)
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error updating stock {stock_data.get('nse_symbol', 'Unknown')}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Successfully updated {updated_count} stocks in database")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating stock database: {e}")
            db.rollback()
            return 0
    
    def collect_all_data(self, db: Session) -> Dict[str, int]:
        """Collect all types of data for all stocks."""
        try:
            logger.info("Starting comprehensive data collection...")
            
            results = {
                'stocks_updated': 0,
                'daily_prices_collected': 0,
                'quarterly_results_collected': 0,
                'financial_statements_collected': 0
            }
            
            # Collect basic stock data
            nse_data = self.collect_nse_data(db)
            bse_data = self.collect_bse_data(db)
            
            # Combine and deduplicate data
            all_stocks_data = nse_data + bse_data
            results['stocks_updated'] = self.update_stock_database(db, all_stocks_data)
            
            # Get list of active stocks
            active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
            
            # Collect detailed data for each stock
            for stock in active_stocks[:10]:  # Limit to first 10 for demo
                symbol = stock.nse_symbol or stock.bse_symbol
                if not symbol:
                    continue
                
                # Collect daily prices
                daily_prices = self.collect_daily_prices(db, symbol)
                results['daily_prices_collected'] += len(daily_prices)
                
                # Collect quarterly results
                quarterly_results = self.collect_quarterly_results(db, symbol)
                results['quarterly_results_collected'] += len(quarterly_results)
                
                # Collect financial statements
                financial_statements = self.collect_financial_statements(db, symbol)
                results['financial_statements_collected'] += len(financial_statements)
                
                # Add delay between stocks
                time.sleep(settings.request_delay)
            
            logger.info(f"Data collection completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive data collection: {e}")
            return {'error': str(e)}
    
    def schedule_data_collection(self):
        """Schedule regular data collection."""
        try:
            logger.info("Setting up scheduled data collection...")
            
            # This would typically be handled by a task scheduler like Celery
            # For now, we'll just log the intention
            logger.info(f"Data collection scheduled every {settings.data_collection_interval} seconds")
            
        except Exception as e:
            logger.error(f"Error setting up scheduled data collection: {e}")


# Global instance
data_collector = DataCollectorService()
