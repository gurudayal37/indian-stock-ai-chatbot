#!/usr/bin/env python3
"""
BSE Quarterly Results Syncer
Scrapes quarterly results from BSE website with Yahoo Finance fallback

TRANSFORMATION LOGIC - BSE Raw to Screener/Analyst Values:

IMPORTANT: BSE displays all financial values in crores (e.g., "52,788.00" = 52,788 crores)
All values are stored and processed in crores scale. No scaling is applied during parsing.
Simple sequential column parsing since all BSE data is in crores.

Based on the mapping table provided, this syncer implements the following transformations:

1. Sales/Revenue: Same (no change needed)
   - BSE Raw: "Sales" 
   - Screener Analyst: "Sales"
   - Adjustment: No change

2. Operating Expenses (excl. Interest): BSE Expenditure - Interest
   - BSE Raw: "Expenditure (includes Interest)"
   - Screener Analyst: "Operating Expenses (excl. Interest)"
   - Adjustment: BSE Expenditure - Interest

3. Operating Profit (EBITDA): BSE PBDT + Depreciation
   - BSE Raw: "Operating Profit (shown lower)"
   - Screener Analyst: "EBITDA (correct)"
   - Adjustment: BSE PBDT + Depreciation
   - Note: BSE shows PBDT (Profit Before Depreciation and Tax)

4. OPM %: Recalculate using corrected EBITDA
   - BSE Raw: "(Operating Profit ÷ Sales) but understated"
   - Screener Analyst: "EBITDA ÷ Sales"
   - Adjustment: Recalculate using corrected EBITDA

5. Other Income: Same (no change needed)
   - BSE Raw: "Other Income"
   - Screener Analyst: "Other Income"
   - Adjustment: No change

6. Interest: Separate line item
   - BSE Raw: "Already included inside Expenditure"
   - Screener Analyst: "Separate line item"
   - Adjustment: Take directly from BSE "Interest" row

7. Depreciation: Same (no change needed)
   - BSE Raw: "Depreciation"
   - Screener Analyst: "Depreciation"
   - Adjustment: No change

8. Profit Before Tax (PBT): Matches (no change needed)
   - BSE Raw: "Matches"
   - Screener Analyst: "Matches"
   - Adjustment: No change

9. Tax %: Calculate if we have tax amount and PBT
   - BSE Raw: "Matches"
   - Screener Analyst: "Matches"
   - Adjustment: Calculate as (Tax / PBT) * 100

10. Net Profit: Same (no change needed)
    - BSE Raw: "Matches"
    - Screener Analyst: "Matches"
    - Adjustment: No change

11. EPS: Same (no change needed)
    - BSE Raw: "Matches"
    - Screener Analyst: "Matches"
    - Adjustment: No change

Additional Derived Metrics:
- Net Margin %: (Net Profit / Revenue) * 100
- Total Income: Revenue + Other Income

This ensures that all financial metrics stored in the database are in the Screener/Analyst format,
making them directly comparable with other financial data sources and analysis tools.
"""

import sys
import os
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
# import yfinance as yf
import pandas as pd
from bs4 import BeautifulSoup
import logging

# Selenium for JavaScript-rendered content
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available. Install with: pip install selenium")

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.stock import Stock, QuarterlyResult, SyncTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bse_quarterly_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BSEQuarterlySyncer:
    """BSE Quarterly Results Syncer (BSE only - Yahoo Finance fallback commented out)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://www.bseindia.com/stock-share-price"
        
        # Initialize Selenium driver if available
        self.driver = None
        if SELENIUM_AVAILABLE:
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')  # Run in background
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ Selenium Chrome driver initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Selenium driver: {e}")
                self.driver = None
        
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
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("✅ Selenium driver closed")
        except Exception as e:
            logger.warning(f"Error closing Selenium driver: {e}")
    
    def safe_db_operation(self, operation_func, *args, **kwargs):
        """Safely execute database operations with session management"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
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
                
                if "server closed the connection" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database connection lost, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise e
            finally:
                self.close_session(session)
    
    def get_sync_tracker(self, stock_id: int, data_type: str) -> Optional[Dict[str, Any]]:
        """Get or create sync tracker for a stock and data type"""
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
    
    def scrape_bse_quarterly_results(self, stock: Stock) -> List[Dict[str, Any]]:
        """Scrape quarterly results from BSE website using Selenium for JavaScript content
        
        BSE displays financial values in crores (e.g., "52,788.00" = 52,788 crores)
        All scraped values are stored in crores scale, no scaling applied.
        """
        try:
            # Construct BSE URL
            # Format: https://www.bseindia.com/stock-share-price/company-name/nse-symbol/bse-code/financials-results/
            company_name = stock.name.lower().replace(' ', '-').replace('&', 'and').replace('.', '')
            nse_symbol = stock.nse_symbol.lower()
            bse_code = stock.bse_symbol
            
            if not bse_code:
                logger.warning(f"No BSE code for {stock.nse_symbol}, skipping BSE scraping")
                return []
            
            # Clean company name for URL
            company_name = re.sub(r'[^a-z0-9\-]', '', company_name)
            
            url = f"{self.base_url}/{company_name}/{nse_symbol}/{bse_code}/financials-results/"
            logger.info(f"🔍 Scraping BSE URL: {url}")
            
            # Use Selenium if available, otherwise fall back to requests
            if self.driver and SELENIUM_AVAILABLE:
                return self._scrape_with_selenium(url, stock)
            else:
                return self._scrape_with_requests(url, stock)
                
        except Exception as e:
            logger.error(f"❌ Error scraping BSE for {stock.nse_symbol}: {e}")
            return []
    
    def _scrape_with_selenium(self, url: str, stock: Stock) -> List[Dict[str, Any]]:
        """Scrape BSE using Selenium for JavaScript-rendered content"""
        try:
            logger.info(f"🚀 Using Selenium to scrape {stock.nse_symbol}")
            
            # Navigate to the page
            self.driver.get(url)
            logger.info(f"📄 Navigated to BSE page for {stock.nse_symbol}")
            
            # Wait for page to load and look for quarterly results
            wait = WebDriverWait(self.driver, 30)
            
            # Wait for page to fully load
            time.sleep(5)
            logger.info(f"⏳ Waited for page to load for {stock.nse_symbol}")
            
            # Try to wait for quarterly results table to load dynamically
            try:
                # Look for the quarterly trends tab or table with AngularJS binding
                quarterly_table = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//table[contains(@ng-bind-html, 'reportData') or contains(@ng-bind-html, 'trustAsHtml')]"))
                )
                logger.info(f"✅ Found quarterly results table for {stock.nse_symbol}")
                
                # Additional wait for dynamic content to populate
                time.sleep(3)
                
            except Exception as e:
                logger.info(f"⏳ Quarterly results table not immediately visible for {stock.nse_symbol}: {e}")
                # Continue anyway, the content might be loaded differently
            
            # First, let's debug what's actually on the page
            logger.info(f"🔍 Debugging page content for {stock.nse_symbol}")
            
            # Get current page source for debugging
            page_source = self.driver.page_source
            
            # Save the JavaScript-rendered HTML for debugging
            with open(f'debug_selenium_{stock.nse_symbol}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info(f"💾 Saved Selenium HTML to debug_selenium_{stock.nse_symbol}.html")
            
            # Debug: Check page title and URL
            page_title = self.driver.title
            current_url = self.driver.current_url
            logger.info(f"📋 Page title: {page_title}")
            logger.info(f"🔗 Current URL: {current_url}")
            
            # Debug: Look for any text containing financial keywords
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                financial_keywords = ['revenue', 'profit', 'quarterly', 'financial', 'results', 'eps', 'opm', 'npm']
                found_keywords = [kw for kw in financial_keywords if kw.lower() in page_text.lower()]
                logger.info(f"🔍 Found financial keywords: {found_keywords}")
                
                # Show first 500 characters of page text for debugging
                preview_text = page_text[:500].replace('\n', ' ').strip()
                logger.info(f"📝 Page text preview: {preview_text}...")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not extract page text: {e}")
            
            # Debug: Check for tables
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                logger.info(f"📊 Found {len(tables)} tables on the page")
                
                # Analyze each table briefly
                for i, table in enumerate(tables[:5]):  # Check first 5 tables
                    try:
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        cols = table.find_elements(By.TAG_NAME, "th")
                        logger.info(f"📋 Table {i+1}: {len(rows)} rows, {len(cols)} columns")
                        
                        if cols:
                            header_texts = [col.text.strip() for col in cols[:3]]  # First 3 headers
                            logger.info(f"📋 Table {i+1} headers: {header_texts}")
                    except Exception as e:
                        logger.debug(f"Error analyzing table {i+1}: {e}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Could not analyze tables: {e}")
            
            # Debug: Check for divs with financial content
            try:
                financial_divs = self.driver.find_elements(By.XPATH, "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'financial') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'quarterly') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'results')]")
                logger.info(f"🔍 Found {len(financial_divs)} divs with financial content")
                
                # Show text from first few financial divs
                for i, div in enumerate(financial_divs[:3]):
                    try:
                        div_text = div.text.strip()[:200]  # First 200 characters
                        logger.info(f"📋 Financial div {i+1}: {div_text}...")
                    except Exception as e:
                        logger.debug(f"Error reading div {i+1}: {e}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Could not analyze financial divs: {e}")
            
            # Try to find quarterly results with improved selectors
            quarterly_results = self._find_quarterly_results_with_selenium(stock)
            
            if quarterly_results:
                logger.info(f"✅ Found {len(quarterly_results)} quarterly results using Selenium")
                return quarterly_results
            else:
                logger.warning(f"⚠️ No quarterly results found with Selenium for {stock.nse_symbol}")
                # Try parsing the HTML as fallback
                soup = BeautifulSoup(page_source, 'html.parser')
                return self._parse_bse_html(soup, stock)
                
        except Exception as e:
            logger.error(f"❌ Selenium error for {stock.nse_symbol}: {e}")
            return []
    
    def _find_quarterly_results_with_selenium(self, stock: Stock) -> List[Dict[str, Any]]:
        """Find quarterly results using improved Selenium selectors"""
        try:
            logger.info(f"🔍 Searching for quarterly results with improved selectors for {stock.nse_symbol}")
            
            # Improved selectors based on common BSE patterns
            improved_selectors = [
                # Look for tables with financial data
                "//table[.//th[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'revenue') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'profit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'eps')]]",
                
                # Look for divs containing quarterly data
                "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'quarterly trends') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'financial results')]",
                
                # Look for any element with month abbreviations (Jun, Mar, Dec, Sep)
                "//*[contains(text(), 'Jun-') or contains(text(), 'Mar-') or contains(text(), 'Dec-') or contains(text(), 'Sep-')]",
                
                # Look for tables with specific column headers
                "//table[.//th[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jun') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mar') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dec') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sep')]]",
                
                # Look for any table that might contain financial data
                "//table[count(.//tr) > 2 and count(.//th) > 3]",
                
                # Look for AngularJS tables with quarterly data binding
                "//table[contains(@ng-bind-html, 'reportData') or contains(@ng-bind-html, 'trustAsHtml')]",
                
                # Look for tables within quarterly trends section
                "//div[contains(@id, 'qtly')]//table",
                
                # Look for tables with quarterly trends tab
                "//div[contains(@class, 'tab-pane') and contains(@class, 'active')]//table"
            ]
            
            for i, selector in enumerate(improved_selectors):
                try:
                    logger.info(f"🔍 Trying selector {i+1}: {selector}")
                    elements = self.driver.find_elements(By.XPATH, selector)
                    
                    if elements:
                        logger.info(f"✅ Selector {i+1} found {len(elements)} elements")
                        
                        # If we found a table, try to extract data from it
                        if 'table' in selector:
                            for table in elements:
                                try:
                                    # Get table HTML and parse it
                                    table_html = table.get_attribute('outerHTML')
                                    soup = BeautifulSoup(table_html, 'html.parser')
                                    
                                    # Check if this table has quarterly data
                                    if self._is_quarterly_table(soup):
                                        logger.info(f"✅ Found quarterly results table with selector {i+1}")
                                        return self._parse_bse_html(soup, stock)
                                except Exception as e:
                                    logger.debug(f"Error processing table: {e}")
                                    continue
                        
                        # If we found divs with financial content, look for tables within them
                        elif 'div' in selector or 'qtly' in selector or 'tab-pane' in selector:
                            for div in elements:
                                try:
                                    # Look for tables within this div
                                    tables = div.find_elements(By.TAG_NAME, "table")
                                    for table in tables:
                                        table_html = table.get_attribute('outerHTML')
                                        soup = BeautifulSoup(table_html, 'html.parser')
                                        if self._is_quarterly_table(soup):
                                            logger.info(f"✅ Found quarterly results table within div using selector {i+1}")
                                            return self._parse_bse_html(soup, stock)
                                except Exception as e:
                                    logger.debug(f"Error processing div: {e}")
                                    continue
                        
                        # If we found AngularJS tables, handle them specially
                        elif 'ng-bind-html' in selector or 'reportData' in selector:
                            logger.info(f"🔍 Processing AngularJS table with selector {i+1}")
                            for table in elements:
                                try:
                                    # For AngularJS tables, we need to wait for content to load
                                    # and then get the actual rendered content
                                    table_html = table.get_attribute('outerHTML')
                                    soup = BeautifulSoup(table_html, 'html.parser')
                                    
                                    # Check if this table has quarterly data
                                    if self._is_quarterly_table(soup):
                                        logger.info(f"✅ Found quarterly results table with AngularJS selector {i+1}")
                                        return self._parse_bse_html(soup, stock)
                                    else:
                                        # Try to wait a bit more for content to load
                                        time.sleep(2)
                                        table_html = table.get_attribute('outerHTML')
                                        soup = BeautifulSoup(table_html, 'html.parser')
                                        if self._is_quarterly_table(soup):
                                            logger.info(f"✅ Found quarterly results table after waiting with AngularJS selector {i+1}")
                                            return self._parse_bse_html(soup, stock)
                                except Exception as e:
                                    logger.debug(f"Error processing AngularJS table: {e}")
                                    continue
                        
                        # If we found month abbreviations, look for the containing table
                        elif any(month in selector.lower() for month in ['jun', 'mar', 'dec', 'sep']):
                            logger.info(f"🔍 Processing {len(elements)} month abbreviation elements")
                            for j, element in enumerate(elements):
                                try:
                                    logger.info(f"🔍 Processing month element {j+1}: {element.text.strip()}")
                                    
                                    # Try multiple approaches to find the parent table
                                    parent_table = None
                                    
                                    # Approach 1: Direct ancestor table
                                    try:
                                        parent_table = element.find_element(By.XPATH, "./ancestor::table")
                                        logger.info(f"✅ Found parent table using ancestor::table")
                                    except:
                                        pass
                                    
                                    # Approach 2: Look for table in parent div
                                    if not parent_table:
                                        try:
                                            parent_div = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'table') or contains(@class, 'financial') or contains(@class, 'quarterly')]")
                                            tables = parent_div.find_elements(By.TAG_NAME, "table")
                                            if tables:
                                                parent_table = tables[0]
                                                logger.info(f"✅ Found parent table in financial div")
                                        except:
                                            pass
                                    
                                    # Approach 3: Look for any nearby table
                                    if not parent_table:
                                        try:
                                            # Look for table within 5 levels up
                                            for level in range(1, 6):
                                                try:
                                                    parent_table = element.find_element(By.XPATH, f"./ancestor::*[{level}]//table")
                                                    if parent_table:
                                                        logger.info(f"✅ Found nearby table at level {level}")
                                                        break
                                                except:
                                                    continue
                                        except:
                                            pass
                                    
                                    if parent_table:
                                        table_html = parent_table.get_attribute('outerHTML')
                                        soup = BeautifulSoup(table_html, 'html.parser')
                                        
                                        # Check if this table has quarterly data
                                        if self._is_quarterly_table(soup):
                                            logger.info(f"✅ Found quarterly results table from month abbreviation using selector {i+1}")
                                            return self._parse_bse_html(soup, stock)
                                        else:
                                            logger.debug(f"Table found but doesn't contain quarterly data")
                                    else:
                                        logger.debug(f"Could not find parent table for month element {j+1}")
                                        
                                except Exception as e:
                                    logger.debug(f"Error processing month element {j+1}: {e}")
                                    continue
                    
                except Exception as e:
                    logger.debug(f"Selector {i+1} failed: {e}")
                    continue
            
            logger.warning(f"⚠️ No quarterly results found with any selector for {stock.nse_symbol}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error in improved selector search for {stock.nse_symbol}: {e}")
            return []
    
    def _is_quarterly_table(self, soup: BeautifulSoup) -> bool:
        """Check if a table contains quarterly results data"""
        try:
            # Look for table headers - BSE uses both <th> and <td class="tableheading">
            headers = soup.find_all(['th', 'td'], class_='tableheading')
            if not headers:
                # Fallback: look for any <th> elements
                headers = soup.find_all('th')
            
            if not headers:
                logger.debug("🔍 No headers found in table")
                return False
            
            header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
            logger.info(f"🔍 Table headers: {header_text}")
            
            # Check for quarterly indicators
            quarterly_indicators = ['jun', 'mar', 'dec', 'sep', 'q1', 'q2', 'q3', 'q4']
            financial_indicators = ['revenue', 'profit', 'eps', 'opm', 'npm']
            
            has_quarterly = any(indicator in header_text for indicator in quarterly_indicators)
            has_financial = any(indicator in header_text for indicator in financial_indicators)
            
            # Also check table rows for month patterns
            rows = soup.find_all('tr')
            has_month_patterns = False
            month_patterns_found = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    first_cell_text = cells[0].get_text(strip=True).lower()
                    if any(month in first_cell_text for month in ['jun-', 'mar-', 'dec-', 'sep-']):
                        has_month_patterns = True
                        month_patterns_found.append(first_cell_text)
                        break
            
            # Check if table has enough structure to be quarterly results
            has_enough_data = len(rows) >= 3 and len(headers) >= 3
            
            # For BSE tables, we're more lenient - if we see month patterns, it's likely quarterly
            is_quarterly = (has_quarterly or has_financial or has_month_patterns) and has_enough_data
            
            logger.info(f"🔍 Table analysis: quarterly={has_quarterly}, financial={has_financial}, month_patterns={has_month_patterns} ({month_patterns_found}), enough_data={has_enough_data}, is_quarterly={is_quarterly}")
            
            return is_quarterly
            
        except Exception as e:
            logger.debug(f"Error analyzing table: {e}")
            return False
    
    def _scrape_with_requests(self, url: str, stock: Stock) -> List[Dict[str, Any]]:
        """Fallback scraping using requests (for when Selenium is not available)"""
        try:
            logger.info(f"📡 Using requests fallback for {stock.nse_symbol}")
            
            # Add delay to be respectful to BSE servers
            time.sleep(2)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Save HTML content for inspection
            with open(f'debug_bse_{stock.nse_symbol}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"🔍 Saved HTML content to debug_bse_{stock.nse_symbol}.html")
            
            return self._parse_bse_html(soup, stock)
            
        except Exception as e:
            logger.error(f"❌ Requests scraping failed for {stock.nse_symbol}: {e}")
            return []
    
    def _parse_bse_html(self, soup: BeautifulSoup, stock: Stock) -> List[Dict[str, Any]]:
        """Parse BSE HTML content for quarterly results"""
        quarterly_results = []
        
        logger.info(f"🔍 Parsing BSE HTML for {stock.nse_symbol}")
        
        # Method 1: Look for tables with specific BSE patterns
        tables = soup.find_all('table')
        logger.info(f"📊 Found {len(tables)} tables to analyze")
        
        for i, table in enumerate(tables):
            try:
                # Look for table headers - BSE uses both <th> and <td class="tableheading">
                headers = table.find_all(['th', 'td'], class_='tableheading')
                if not headers:
                    # Fallback: look for any <th> elements
                    headers = table.find_all('th')
                
                if not headers:
                    continue
                    
                header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
                
                # Check if this looks like a quarterly results table
                if any(keyword in header_text for keyword in ['jun', 'mar', 'dec', 'sep', 'revenue', 'profit', 'eps']):
                    logger.info(f"📊 Found potential quarterly results table {i+1} with headers: {header_text}")
                    
                    # Parse the table rows
                    rows = table.find_all('tr')
                    logger.info(f"📋 Table {i+1} has {len(rows)} rows")
                    
                    # Find the header row (first row with month/quarter headers)
                    header_row = None
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            cell_text = ' '.join([c.get_text(strip=True).lower() for c in cells])
                            if any(month in cell_text for month in ['jun-', 'mar-', 'dec-', 'sep-']):
                                header_row = row
                                break
                    
                    if not header_row:
                        logger.debug(f"Table {i+1}: No header row found with month patterns")
                        continue
                    
                    # Extract quarter information from header row
                    header_cells = header_row.find_all(['td', 'th'])
                    quarters = []
                    
                    # BSE shows all values in crores - just parse all columns that look like quarters
                    for cell in header_cells:
                        cell_text = cell.get_text(strip=True).strip()
                        if any(month in cell_text.lower() for month in ['jun-', 'mar-', 'dec-', 'sep-']):
                            quarters.append(cell_text)
                    logger.info(f"📅 Found {len(quarters)} quarters: {quarters}")
                    
                    # Parse data rows
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 3:  # Need at least metric name + some data
                            continue
                            
                        # First cell should contain the metric name
                        metric_cell = cells[0]
                        metric_name = metric_cell.get_text(strip=True).lower()
                        
                        # Skip header rows and empty rows
                        if not metric_name or metric_name in ['income statement', 'standalone', 'consolidated', 'segment']:
                            continue
                        
                        # Check if this is a financial metric we care about
                        if any(keyword in metric_name for keyword in ['revenue', 'sales', 'other income', 'total income', 'expenditure', 'expenses', 'interest', 'pbdt', 'depreciation', 'pbt', 'profit before tax', 'tax', 'net profit', 'equity', 'eps', 'ceps', 'opm %', 'npm %']):
                            logger.debug(f"📊 Processing metric: {metric_name}")
                            
                            # Extract values for each quarter (simple sequential indexing)
                            for quarter_idx, quarter in enumerate(quarters):
                                # Use simple sequential indexing since all values are in crores
                                value_cell_idx = quarter_idx + 1
                                
                                if value_cell_idx < len(cells):  # Ensure we have enough cells
                                    value_cell = cells[value_cell_idx]
                                    value_text = value_cell.get_text(strip=True).strip()
                                    
                                    # Skip if no value or if it's a link
                                    if not value_text or value_text in ['--', 'standalone', 'consolidated', 'segment']:
                                        continue
                                    
                                    try:
                                        # Parse the quarter to get year and quarter number
                                        quarter_data = self._parse_quarter_from_text(quarter)
                                        if quarter_data:
                                            year, quarter_num = quarter_data
                                            
                                            # Create quarterly result record
                                            quarter_record = self._create_quarterly_record_from_bse(
                                                stock, year, quarter_num, metric_name, value_text
                                            )
                                            
                                            if quarter_record:
                                                # Check if we already have this quarter
                                                existing_quarter = next(
                                                    (qr for qr in quarterly_results 
                                                     if qr['year'] == year and qr['quarter_number'] == quarter_num), 
                                                    None
                                                )
                                                
                                                if existing_quarter:
                                                    # Update existing record with new metric
                                                    existing_quarter.update(quarter_record)
                                                    logger.debug(f"✅ Updated existing {quarter_record['quarter']} record")
                                                else:
                                                    # Add new record
                                                    quarterly_results.append(quarter_record)
                                                    logger.debug(f"✅ Added new {quarter_record['quarter']} record")
                                    
                                    except Exception as e:
                                        logger.warning(f"Error processing quarter {quarter} for {metric_name}: {e}")
                                        continue
                                        
            except Exception as e:
                logger.debug(f"Error processing table {i+1}: {e}")
                continue
        
        if quarterly_results:
            # Apply Screener transformations after all metrics are collected
            logger.info(f"🔄 Applying Screener transformations to {len(quarterly_results)} quarterly results...")
            for quarter_record in quarterly_results:
                self._apply_screener_transformations(quarter_record)
            
            logger.info(f"✅ Successfully parsed and transformed {len(quarterly_results)} quarterly results from BSE")
            return quarterly_results
        else:
            logger.warning(f"⚠️ No quarterly results found in BSE table for {stock.nse_symbol}")
            return []
    
    def _parse_quarter_from_text(self, quarter_text: str) -> Optional[Tuple[int, int]]:
        """Parse quarter text to extract year and quarter number"""
        try:
            # Handle formats like "Jun-25", "Mar-25", "Dec-24", "Sep-24"
            month_quarter_map = {
                'jun': 2, 'mar': 1, 'dec': 4, 'sep': 3
            }
            
            month_match = re.search(r'(jun|mar|dec|sep)-(\d{2})', quarter_text.lower())
            if month_match:
                month = month_match.group(1)
                year_short = month_match.group(2)
                quarter_num = month_quarter_map[month]
                year = 2000 + int(year_short)  # Convert "25" to 2025
                return year, quarter_num
            
            # Handle formats like "Q1 2025", "Q2 2024"
            quarter_match = re.search(r'q(\d)\s*(\d{4})', quarter_text.lower())
            if quarter_match:
                quarter_num = int(quarter_match.group(1))
                year = int(quarter_match.group(2))
                return year, quarter_num
                
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing quarter text '{quarter_text}': {e}")
            return None
    
    def _apply_screener_transformations(self, quarter_record: Dict[str, Any]):
        """Apply Screener transformations to a quarterly record after all metrics are collected
        
        All financial values in quarter_record are expected to be in crores.
        This method applies Screener transformation rules to convert BSE raw values
        to Screener/Analyst equivalent values, maintaining the crores scale.
        
        TRANSFORMATION RULES:
        1. Expenses = BSE_Expenses – BSE_Interest
        2. OperatingProfit = Revenue - (Expenditure - Interest)  # Since BSE doesn't show Operating Profit directly
        3. OPM% = (Screener_OperatingProfit / BSE_Sales) * 100
        """
        try:
            logger.info(f"🔄 Applying Screener transformations for {quarter_record.get('quarter', 'unknown')}")
            
            # Rule 1: Expenses = BSE_Expenses – BSE_Interest
            if (quarter_record.get('expenditure') is not None and 
                quarter_record.get('interest') is not None):
                
                # Store original BSE expenditure before transformation
                bse_expenditure = quarter_record['expenditure']
                
                # Apply Screener transformation: Expenses = BSE_Expenses – BSE_Interest
                screener_expenses = bse_expenditure - abs(quarter_record['interest'])
                quarter_record['expenditure'] = screener_expenses
                
                logger.info(f"✅ Rule 1 - Expenses: BSE_Expenses({bse_expenditure}) – BSE_Interest({abs(quarter_record['interest'])}) = {screener_expenses}")
            else:
                logger.warning(f"⚠️ Missing fields for Expenses calculation: expenditure={quarter_record.get('expenditure')}, interest={quarter_record.get('interest')}")
            
            # Rule 2: OperatingProfit calculation
            # Since BSE doesn't show Operating Profit directly, we calculate it as:
            # Operating Profit = Revenue - (Expenditure - Interest)
            if (quarter_record.get('revenue') is not None and 
                quarter_record.get('expenditure') is not None and 
                quarter_record.get('interest') is not None):
                
                # Calculate Operating Profit using Screener formula
                screener_operating_profit = quarter_record['revenue'] - (quarter_record['expenditure'] - abs(quarter_record['interest']))
                quarter_record['operating_profit'] = screener_operating_profit
                quarter_record['ebitda'] = screener_operating_profit  # EBITDA = Operating Profit
                
                logger.info(f"✅ Rule 2 - Operating Profit: Revenue({quarter_record['revenue']}) - (Expenditure({quarter_record['expenditure']}) - Interest({abs(quarter_record['interest'])})) = {screener_operating_profit}")
            else:
                logger.warning(f"⚠️ Missing fields for Operating Profit calculation: revenue={quarter_record.get('revenue')}, expenditure={quarter_record.get('expenditure')}, interest={quarter_record.get('interest')}")
            
            # Rule 3: OPM% = (Screener_OperatingProfit / BSE_Sales) * 100
            if (quarter_record.get('operating_profit') is not None and 
                quarter_record.get('revenue') is not None and 
                quarter_record['revenue'] > 0):
                
                opm_percent = (quarter_record['operating_profit'] / quarter_record['revenue']) * 100
                quarter_record['opm_percent'] = opm_percent
                
                logger.info(f"✅ Rule 3 - OPM%: (Screener_OperatingProfit({quarter_record['operating_profit']}) / BSE_Sales({quarter_record['revenue']})) * 100 = {opm_percent:.2f}%")
            else:
                logger.warning(f"⚠️ Missing fields for OPM% calculation: operating_profit={quarter_record.get('operating_profit')}, revenue={quarter_record.get('revenue')}")
            
            # Additional derived calculations
            # Tax %
            if (quarter_record.get('pbt') is not None and 
                quarter_record['pbt'] > 0 and 
                quarter_record.get('tax') is not None):
                
                tax_percent = (abs(quarter_record['tax']) / quarter_record['pbt']) * 100
                quarter_record['tax_percent'] = tax_percent
                logger.info(f"✅ Tax %: (|Tax({abs(quarter_record['tax'])}| / PBT({quarter_record['pbt']})) * 100 = {tax_percent:.2f}%")
            
            # Net Margin %
            if (quarter_record.get('net_profit') is not None and 
                quarter_record.get('revenue') is not None and 
                quarter_record['revenue'] > 0):
                
                net_margin = (quarter_record['net_profit'] / quarter_record['revenue']) * 100
                quarter_record['net_margin'] = net_margin
                logger.info(f"✅ Net Margin %: (Net Profit({quarter_record['net_profit']}) / Revenue({quarter_record['revenue']})) * 100 = {net_margin:.2f}%")
            
            # Total Income
            if (quarter_record.get('revenue') is not None and 
                quarter_record.get('other_income') is not None):
                
                total_income = quarter_record['revenue'] + quarter_record['other_income']
                quarter_record['total_income'] = total_income
                logger.info(f"✅ Total Income: Revenue({quarter_record['revenue']}) + Other Income({quarter_record['other_income']}) = {total_income}")
            
            logger.info(f"✅ Successfully applied all Screener transformations for {quarter_record.get('quarter', 'unknown')}")
                
        except Exception as e:
            logger.error(f"❌ Error applying Screener transformations to {quarter_record.get('quarter', 'unknown')}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _show_transformation_summary(self, raw_values: Dict[str, float], analyst_values: Dict[str, float], quarter: str):
        """Show a summary of transformations from BSE raw to Screener/Analyst values"""
        logger.info(f"🔄 Transformation Summary for {quarter}:")
        logger.info("=" * 60)
        
        # Show key transformations
        if 'expenditure' in raw_values and 'interest' in raw_values:
            raw_exp = raw_values['expenditure']
            interest = raw_values['interest']
            analyst_exp = analyst_values.get('operating_expenses', 'N/A')
            logger.info(f"📊 Operating Expenses: {raw_exp} (BSE Raw) - {interest} (Interest) = {analyst_exp} (Analyst)")
        
        if 'pbdt' in raw_values and 'depreciation' in raw_values:
            pbdt = raw_values['pbdt']
            dep = raw_values['depreciation']
            ebitda = analyst_values.get('ebitda', 'N/A')
            logger.info(f"📊 EBITDA: {pbdt} (BSE PBDT) + {abs(dep)} (Depreciation) = {ebitda} (Analyst)")
        
        if 'revenue' in raw_values and 'operating_profit' in analyst_values:
            revenue = raw_values['revenue']
            operating_profit = analyst_values['operating_profit']
            opm = analyst_values.get('opm_percent', 'N/A')
            logger.info(f"📊 Screener OPM %: ({operating_profit} / {revenue}) * 100 = {opm}% (Analyst)")
        
        if 'net_profit' in raw_values and 'revenue' in raw_values:
            net_profit = raw_values['net_profit']
            revenue = raw_values['revenue']
            npm = analyst_values.get('net_margin', 'N/A')
            logger.info(f"📊 Net Margin %: ({net_profit} / {revenue}) * 100 = {npm}% (Analyst)")
        
        logger.info("=" * 60)
    
    def _create_quarterly_record_from_bse(self, stock: Stock, year: int, quarter_num: int, metric_name: str, value_text: str) -> Optional[Dict[str, Any]]:
        """Create a quarterly record from BSE data with proper transformations to Screener/Analyst values
        
        BSE provides financial values in crores (e.g., "52,788.00" = 52,788 crores)
        We store these values as-is in crores, then apply Screener transformations.
        """
        try:
            # Convert value text to numeric
            raw_value = self._parse_numeric_value(value_text)
            if raw_value is None:
                return None
            
            # Create base quarterly record
            quarter_record = {
                'stock_id': stock.id,
                'quarter': f"Q{quarter_num} {year}",
                'year': year,
                'quarter_number': quarter_num,
                'quarterly_result_link': f"https://www.bseindia.com/stock-share-price/{stock.name.lower().replace(' ', '-')}/{stock.nse_symbol.lower()}/{stock.bse_symbol}/financials-results/",
                'source': 'BSE',
                'filing_date': datetime.now().date(),
                'announcement_date': datetime.now().date(),
                'is_consolidated': False
            }
            
            # Store raw BSE values for reference and calculations
            raw_values = {}
            
            # Map metric names to database fields and store raw values
            metric_mapping = {
                'revenue': 'revenue',
                'sales': 'revenue',  # BSE sometimes uses 'Sales' instead of 'Revenue'
                'other income': 'other_income',
                'total income': 'total_income',
                'expenditure': 'expenditure',
                'expenses': 'expenditure',  # BSE sometimes uses 'Expenses'
                'interest': 'interest',
                'pbdt': 'pbdt',
                'depreciation': 'depreciation',
                'pbt': 'pbt',
                'profit before tax': 'pbt',  # Alternative name
                'tax': 'tax',
                'net profit': 'net_profit',
                'equity': 'equity',
                'eps': 'eps',
                'ceps': 'ceps',
                'opm %': 'opm_percent',
                'npm %': 'npm_percent'
            }
            
            # Set the raw metric value and store for calculations
            db_field = metric_mapping.get(metric_name)
            if db_field:
                # Store raw BSE value in both raw_values and quarter_record
                raw_values[db_field] = raw_value
                quarter_record[db_field] = raw_value
                logger.debug(f"✅ Set {db_field} = {raw_value} (raw BSE value) for Q{quarter_num} {year}")
            
            # Note: All Screener transformations are now handled in _apply_screener_transformations
            # after all metrics for a quarter are collected
            
            return quarter_record
            
        except Exception as e:
            logger.debug(f"Error creating quarterly record: {e}")
            return None
    

    
    def _parse_numeric_value(self, value_text: str) -> Optional[float]:
        """Parse numeric value from text, handling BSE's format
        
        BSE displays financial values in crores (e.g., "52,788.00" = 52,788 crores)
        This method parses the text and returns the value in crores, no scaling applied.
        """
        try:
            # Remove common non-numeric characters
            cleaned_text = value_text.replace(',', '').replace('(', '').replace(')', '').strip()
            
            # Handle negative values (BSE uses parentheses for negatives)
            is_negative = value_text.startswith('(') and value_text.endswith(')')
            
            # Extract numeric part
            numeric_match = re.search(r'([\d,]+\.?\d*)', cleaned_text)
            if numeric_match:
                numeric_value = float(numeric_match.group(1).replace(',', ''))
                
                # BSE shows values in crores (e.g., "52,788.00" means 52,788 crores)
                # We store these values as-is in crores, no scaling needed
                # The values should match exactly what BSE displays
                
                logger.debug(f"🔍 Parsed '{value_text}' -> cleaned: '{cleaned_text}' -> extracted: '{numeric_match.group(1)}' -> final: {numeric_value}")
                
                # BSE shows all values in crores - no scaling validation needed
                # Values like 52,788.00 are correctly 52,788 crores
                
                return -numeric_value if is_negative else numeric_value
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing numeric value '{value_text}': {e}")
            return None
            
            # Look for quarterly results table
            quarterly_results = []
            
            # Try to find the quarterly results table
            # BSE has specific table structure for quarterly results
            quarterly_results = []
            
            # Method 1: Look for tables with specific BSE patterns
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for table headers that might indicate quarterly results
                headers = table.find_all('th')
                if not headers:
                    continue
                    
                header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
                
                # Check if this looks like a quarterly results table
                if any(keyword in header_text for keyword in ['jun', 'mar', 'dec', 'sep', 'revenue', 'profit', 'eps']):
                    logger.info(f"📊 Found potential quarterly results table with headers: {header_text}")
                    
                    # Parse the table rows
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:  # Need at least quarter, revenue, profit
                            try:
                                quarter_data = self._parse_quarterly_row(cells, stock)
                                if quarter_data:
                                    quarterly_results.append(quarter_data)
                            except Exception as e:
                                logger.warning(f"Error parsing row: {e}")
                                continue
            
            # Method 2: Look for specific BSE div containers
            if not quarterly_results:
                logger.info("🔍 Trying alternative BSE parsing method...")
                # Look for divs that might contain quarterly data
                financial_divs = soup.find_all('div', class_=lambda x: x and any(keyword in x.lower() for keyword in ['financial', 'quarterly', 'results']))
                
                for div in financial_divs:
                    tables = div.find_all('table')
                    for table in tables:
                        headers = table.find_all('th')
                        if headers:
                            header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
                            if any(keyword in header_text for keyword in ['jun', 'mar', 'dec', 'sep']):
                                logger.info(f"📊 Found quarterly results in div: {header_text}")
                                rows = table.find_all('tr')
                                for row in rows[1:]:
                                    cells = row.find_all(['td', 'th'])
                                    if len(cells) >= 3:
                                        try:
                                            quarter_data = self._parse_quarterly_row(cells, stock)
                                            if quarter_data:
                                                quarterly_results.append(quarter_data)
                                        except Exception as e:
                                            logger.warning(f"Error parsing row: {e}")
                                            continue
            
            if quarterly_results:
                logger.info(f"✅ Successfully parsed {len(quarterly_results)} quarterly results from BSE")
                return quarterly_results
            else:
                logger.warning(f"⚠️ No quarterly results found in BSE table for {stock.nse_symbol}")
                return []
    
    def _parse_quarterly_row(self, cells, stock: Stock) -> Optional[Dict[str, Any]]:
        """Parse a row of quarterly results data with proper transformations to Screener/Analyst values"""
        try:
            # Extract quarter and year from first cell
            quarter_text = cells[0].get_text(strip=True)
            
            # Try multiple quarter formats used by BSE
            quarter_match = None
            quarter_num = None
            year = None
            
            # Format 1: "Q1 2025", "Q2 2024"
            quarter_match = re.search(r'Q(\d)\s*(\d{4})', quarter_text, re.IGNORECASE)
            if quarter_match:
                quarter_num = int(quarter_match.group(1))
                year = int(quarter_match.group(2))
            
            # Format 2: "Jun-25", "Mar-25", "Dec-24", "Sep-24"
            if not quarter_match:
                month_quarter_map = {
                    'jun': 2, 'mar': 1, 'dec': 4, 'sep': 3
                }
                month_match = re.search(r'(jun|mar|dec|sep)-(\d{2})', quarter_text.lower())
                if month_match:
                    month = month_match.group(1)
                    year_short = month_match.group(2)
                    quarter_num = month_quarter_map[month]
                    year = 2000 + int(year_short)  # Convert "25" to 2025
                    quarter_match = True
            
            if not quarter_match:
                logger.debug(f"Could not parse quarter from: {quarter_text}")
                return None
            
            quarter_str = f"Q{quarter_num} {year}"
            
            # Parse financial data from remaining cells
            # Instead of position-based mapping, let's try to identify columns by their headers
            raw_values = {}
            
            # First, let's log what we're seeing for debugging
            logger.debug(f"Parsing row for {quarter_str}: {len(cells)} cells")
            for i, cell in enumerate(cells):
                cell_text = cell.get_text(strip=True)
                logger.debug(f"Cell {i}: '{cell_text}'")
            
            # Try to extract values based on column headers or position
            # BSE tables typically have: Quarter | Revenue | Other Income | Total Income | Expenditure | Interest | PBDT | Depreciation | PBT | Tax | Net Profit | Equity | EPS | CEPS | OPM% | NPM%
            # IMPORTANT: BSE shows data in both "in Cr." and "in Million" columns. We only want the "in Cr." columns.
            
            # Find the number of "in Cr." columns by looking at the table structure
            # BSE typically has: Quarter | (in Cr.) columns | (in Million) columns
            # We only want the "in Cr." columns, not the "in Million" columns
            
            for i, cell in enumerate(cells[1:], 1):  # Skip first cell (quarter)
                cell_text = cell.get_text(strip=True)
                
                # Try to convert to numeric value
                try:
                    # Use our proper parsing method to handle BSE format correctly
                    numeric_value = self._parse_numeric_value(cell_text)
                    if numeric_value is None:
                        logger.debug(f"Cell {i} not numeric: '{cell_text}'")
                        continue
                    logger.debug(f"Cell {i} parsed as: {numeric_value}")
                    
                    # Based on typical BSE table structure, map columns to raw values
                    if i == 1:  # First column after quarter is usually Revenue
                        raw_values['revenue'] = numeric_value
                        logger.debug(f"Set raw revenue = {numeric_value}")
                    elif i == 2:  # Second might be Other Income
                        raw_values['other_income'] = numeric_value
                        logger.debug(f"Set raw other_income = {numeric_value}")
                    elif i == 3:  # Third might be Total Income
                        raw_values['total_income'] = numeric_value
                        logger.debug(f"Set raw total_income = {numeric_value}")
                    elif i == 4:  # Fourth might be Expenditure
                        raw_values['expenditure'] = numeric_value
                        logger.debug(f"Set raw expenditure = {numeric_value}")
                    elif i == 5:  # Fifth might be Interest
                        raw_values['interest'] = numeric_value
                        logger.debug(f"Set raw interest = {numeric_value}")
                    elif i == 6:  # Sixth might be PBDT
                        raw_values['pbdt'] = numeric_value
                        logger.debug(f"Set raw pbdt = {numeric_value}")
                    elif i == 7:  # Seventh might be Depreciation
                        raw_values['depreciation'] = numeric_value
                        logger.debug(f"Set raw depreciation = {numeric_value}")
                    elif i == 8:  # Eighth might be PBT
                        raw_values['pbt'] = numeric_value
                        logger.debug(f"Set raw pbt = {numeric_value}")
                    elif i == 9:  # Ninth might be Tax
                        raw_values['tax'] = numeric_value
                        logger.debug(f"Set raw tax = {numeric_value}")
                    elif i == 10:  # Tenth might be Net Profit
                        raw_values['net_profit'] = numeric_value
                        logger.debug(f"Set raw net_profit = {numeric_value}")
                    elif i == 11:  # Eleventh might be Equity
                        raw_values['equity'] = numeric_value
                        logger.debug(f"Set raw equity = {numeric_value}")
                    elif i == 12:  # Twelfth might be EPS
                        raw_values['eps'] = numeric_value
                        logger.debug(f"Set raw eps = {numeric_value}")
                    elif i == 13:  # Thirteenth might be CEPS
                        raw_values['ceps'] = numeric_value
                        logger.debug(f"Set raw ceps = {numeric_value}")
                    elif i == 14:  # Fourteenth might be OPM %
                        raw_values['opm_percent'] = numeric_value
                        logger.debug(f"Set raw opm_percent = {numeric_value}")
                    elif i == 15:  # Fifteenth might be NPM %
                        raw_values['npm_percent'] = numeric_value
                        logger.debug(f"Set raw npm_percent = {numeric_value}")
                    
                except ValueError:
                    # Not a numeric value, skip
                    logger.debug(f"Cell {i} not numeric: '{cell_text}'")
                    continue
            
            # Now apply the Screener/Analyst transformations based on the mapping table
            quarter_record = {
                'stock_id': stock.id,
                'quarter': quarter_str,
                'year': year,
                'quarter_number': quarter_num,
                'quarterly_result_link': f"https://www.bseindia.com/stock-share-price/{stock.name.lower().replace(' ', '-')}/{stock.nse_symbol.lower()}/{stock.bse_symbol}/financials-results/",
                'source': 'BSE',
                'filing_date': datetime.now().date(),
                'announcement_date': datetime.now().date(),
                'is_consolidated': True
            }
            
            # Apply transformations from BSE raw to Screener/Analyst values
            
            # 1. Sales/Revenue: Same (no change needed)
            if 'revenue' in raw_values:
                quarter_record['revenue'] = raw_values['revenue']
                logger.debug(f"✅ Sales/Revenue: {raw_values['revenue']} (same as BSE raw)")
            
            # 2. Expenses (exclude Interest): BSE Expenditure - Interest
            if 'expenditure' in raw_values and 'interest' in raw_values:
                screener_expenses = raw_values['expenditure'] - raw_values['interest']
                quarter_record['operating_expenses'] = screener_expenses
                logger.debug(f"✅ Screener Expenses (excl. Interest): {raw_values['expenditure']} - {raw_values['interest']} = {screener_expenses}")
            
            # 3. Operating Profit (EBITDA): Apply Screener transformation rule
            # Screener definition: Operating Profit = Revenue - (Expenditure - Interest)
            if 'revenue' in raw_values and 'expenditure' in raw_values and 'interest' in raw_values:
                screener_operating_profit = raw_values['revenue'] - (raw_values['expenditure'] - abs(raw_values['interest']))
                quarter_record['ebitda'] = screener_operating_profit
                quarter_record['operating_profit'] = screener_operating_profit
                logger.debug(f"✅ Screener Operating Profit: Revenue ({raw_values['revenue']}) - (Expenditure ({raw_values['expenditure']}) - Interest ({abs(raw_values['interest'])})) = {screener_operating_profit}")
            elif 'pbdt' in raw_values:
                # Fallback: If no expenditure data, use PBDT + Interest
                screener_operating_profit = raw_values['pbdt'] + abs(raw_values['interest'])
                quarter_record['ebitda'] = screener_operating_profit
                quarter_record['operating_profit'] = screener_operating_profit
                logger.debug(f"✅ Screener Operating Profit (fallback): PBDT ({raw_values['pbdt']}) + Interest ({abs(raw_values['interest'])}) = {screener_operating_profit}")
            
            # 4. OPM %: Calculate using Screener Operating Profit
            if 'operating_profit' in quarter_record and 'revenue' in quarter_record and quarter_record['revenue'] > 0:
                opm_percent = (quarter_record['operating_profit'] / quarter_record['revenue']) * 100
                quarter_record['opm_percent'] = opm_percent
                logger.debug(f"✅ Screener OPM %: ({quarter_record['operating_profit']} / {quarter_record['revenue']}) * 100 = {opm_percent:.2f}%")
            
            # 5. Other Income: Same (no change needed)
            if 'other_income' in raw_values:
                quarter_record['other_income'] = raw_values['other_income']
                logger.debug(f"✅ Other Income: {raw_values['other_income']} (same as BSE raw)")
            
            # 6. Interest: Separate line item (take directly from BSE)
            if 'interest' in raw_values:
                quarter_record['interest'] = raw_values['interest']
                logger.debug(f"✅ Interest: {raw_values['interest']} (separate line item)")
            
            # 6a. Expenditure: Store raw BSE expenditure for reference
            if 'expenditure' in raw_values:
                quarter_record['expenditure'] = raw_values['expenditure']
                logger.debug(f"✅ Expenditure: {raw_values['expenditure']} (raw BSE value)")
            
            # 7. Depreciation: Same (no change needed)
            if 'depreciation' in raw_values:
                quarter_record['depreciation'] = raw_values['depreciation']
                logger.debug(f"✅ Depreciation: {raw_values['depreciation']} (same as BSE raw)")
            
            # 8. Profit Before Tax (PBT): Matches (no change needed)
            if 'pbt' in raw_values:
                quarter_record['pbt'] = raw_values['pbt']
                logger.debug(f"✅ PBT: {raw_values['pbt']} (matches BSE raw)")
            
            # 9. Tax %: Calculate if we have tax amount and PBT
            if 'tax' in raw_values and 'pbt' in raw_values and raw_values['pbt'] > 0:
                tax_percent = (abs(raw_values['tax']) / raw_values['pbt']) * 100
                quarter_record['tax_percent'] = tax_percent
                logger.debug(f"✅ Tax %: ({abs(raw_values['tax'])} / {raw_values['pbt']}) * 100 = {tax_percent:.2f}%")
            
            # 10. Net Profit: Same (no change needed)
            if 'net_profit' in raw_values:
                quarter_record['net_profit'] = raw_values['net_profit']
                logger.debug(f"✅ Net Profit: {raw_values['net_profit']} (same as BSE raw)")
            
            # 11. EPS: Same (no change needed)
            if 'eps' in raw_values:
                quarter_record['eps'] = raw_values['eps']
                logger.debug(f"✅ EPS: {raw_values['eps']} (same as BSE raw)")
            
            # Calculate additional derived metrics for Screener/Analyst view
            
            # Net Margin %: Net Profit / Revenue
            if 'net_profit' in quarter_record and 'revenue' in quarter_record and quarter_record['revenue'] > 0:
                net_margin = (quarter_record['net_profit'] / quarter_record['revenue']) * 100
                quarter_record['net_margin'] = net_margin
                logger.debug(f"✅ Net Margin %: ({quarter_record['net_profit']} / {quarter_record['revenue']}) * 100 = {net_margin:.2f}%")
            
            # Total Income: Revenue + Other Income
            if 'revenue' in quarter_record and 'other_income' in quarter_record:
                total_income = quarter_record['revenue'] + quarter_record['other_income']
                quarter_record['total_income'] = total_income
                logger.debug(f"✅ Total Income: {quarter_record['revenue']} + {quarter_record['other_income']} = {total_income}")
            
            # Store raw BSE values for reference (optional - you can remove if not needed)
            # quarter_record['raw_bse_values'] = raw_values  # Removed - not a valid database field
            
            # Show transformation summary
            self._show_transformation_summary(raw_values, quarter_record, quarter_str)
            
            logger.info(f"Created quarter record for {quarter_str}: revenue={quarter_record.get('revenue')}, net_profit={quarter_record.get('net_profit')}, ebitda={quarter_record.get('ebitda')}")
            return quarter_record
            
        except Exception as e:
            logger.error(f"Error parsing quarterly row: {e}")
            return None
    
    # def get_yahoo_finance_fallback(self, stock: Stock) -> List[Dict[str, Any]]:
    #     """Get quarterly results from Yahoo Finance as fallback"""
    #     try:
    #         logger.info(f"🔄 Using Yahoo Finance fallback for {stock.nse_symbol}")
    #         
    #         # Add .NS suffix for Yahoo Finance
    #         symbol = f"{stock.nse_symbol}.NS"
    #         ticker = yf.Ticker(symbol)
    #         
    #         quarterly_data = ticker.quarterly_financials
    #         
    #         if quarterly_data is None or quarterly_data.empty:
    #         logger.warning(f"No quarterly data available from Yahoo Finance for {stock.nse_symbol}")
    #         return []
    #         
    #         quarterly_results = []
    #         
    #         for date_col in quarterly_data.columns:
    #             try:
    #                 # Extract quarter and year
    #                 if hasattr(date_col, 'strftime'):
    #                     quarter_date = date_col
    #                 else:
    #                     quarter_date = pd.to_datetime(date_col)
    #                 
    #                 quarter_num = (quarter_date.month - 1) // 3 + 1
    #                 year = quarter_date.year
    #                 quarter_str = f"Q{quarter_num} {year}"
    #                 
    #                 # Extract financial metrics
    #                 quarter_series = quarterly_data[date_col]
    #         revenue = quarter_series.get('Total Revenue', quarter_series.get('Revenue', None))
    #         net_profit = quarter_series.get('Net Income', quarter_series.get('Net Profit', None))
    #         operating_profit = quarter_series.get('Operating Income', quarter_series.get('Operating Profit', None))
    #         
    #         # Skip if critical metrics are missing
    #         if pd.isna(revenue) or revenue == 0 or pd.isna(net_profit) or net_profit == 0:
    #             continue
    #         
    #         # Calculate derived metrics
    #         revenue_val = float(revenue) if not pd.isna(revenue) else None
    #         net_profit_val = float(net_profit) if not pd.isna(net_profit) else None
    #         operating_profit_val = float(operating_profit) if not pd.isna(operating_profit) else None
    #         
    #         # Calculate margins
    #         opm_percent = None
    #         npm_percent = None
    #         if revenue_val and revenue_val > 0:
    #             if operating_profit_val:
    #                 opm_percent = (operating_profit_val / revenue_val) * 100
    #             if net_profit_val:
    #                 npm_percent = (net_profit_val / revenue_val) * 100
    #         
    #         # Try to get EPS from Yahoo Finance
    #         eps = None
    #         try:
    #             eps_data = ticker.quarterly_earnings
    #             if not eps_data.empty:
    #                 # Find matching quarter
    #                 for date, row in eps_data.iterrows():
    #                     if date.year == year and (date.month - 1) // 3 + 1 == quarter_num:
    #                         eps = float(row.get('Earnings', 0)) if not pd.isna(row.get('Earnings', 0)) else None
    #                         break
    #         except:
    #             pass
    #         
    #         # Create quarterly result record
    #         quarter_record = {
    #             'stock_id': stock.id,
    #             'quarter': quarter_str,
    #             'year': year,
    #             'quarter_number': quarter_num,
    #             'revenue': revenue_val,
    #             'net_profit': net_profit_val,
    #             'operating_profit': operating_profit_val,
    #             'eps': eps,
    #             'opm_percent': opm_percent,
    #             'npm_percent': npm_percent,
    #             'quarterly_result_link': None,
    #             'source': 'Yahoo Finance',
    #             'filing_date': quarter_date.date(),
    #             'announcement_date': quarter_date.date(),
    #             'is_consolidated': True
    #         }
    #         
    #         quarterly_results.append(quarter_record)
    #         
    #     except Exception as e:
    #         logger.warning(f"Error processing Yahoo Finance quarter: {e}")
    #         continue
    #         
    #     logger.info(f"✅ Retrieved {len(quarterly_results)} quarterly results from Yahoo Finance")
    #     return quarterly_results
    #     
    # except Exception as e:
    #     logger.error(f"❌ Error getting Yahoo Finance data for {stock.nse_symbol}: {e}")
    #     return []
    
    def save_quarterly_results(self, stock_id: int, quarterly_results: List[Dict[str, Any]]) -> int:
        """Save quarterly results to database"""
        def _save_results(session):
            saved_count = 0
            
            for quarter_data in quarterly_results:
                try:
                    # Check if quarter already exists
                    existing = session.query(QuarterlyResult).filter(
                        QuarterlyResult.stock_id == stock_id,
                        QuarterlyResult.quarter == quarter_data['quarter'],
                        QuarterlyResult.year == quarter_data['year']
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in quarter_data.items():
                            if hasattr(existing, key) and key != 'id':
                                setattr(existing, key, value)
                        logger.debug(f"Updated existing quarter: {quarter_data['quarter']}")
                    else:
                        # Create new record
                        new_quarter = QuarterlyResult(**quarter_data)
                        session.add(new_quarter)
                        saved_count += 1
                        logger.debug(f"Added new quarter: {quarter_data['quarter']}")
                
                except Exception as e:
                    logger.error(f"Error saving quarter {quarter_data.get('quarter', 'Unknown')}: {e}")
                    continue
            
            return saved_count
        
        try:
            return self.safe_db_operation(_save_results)
        except Exception as e:
            logger.error(f"Error in save operation: {e}")
            return 0
    
    def sync_stock_quarterly_results(self, stock: Stock) -> int:
        """Sync quarterly results for a single stock from BSE only
        
        BSE provides financial values in crores. All values are stored in crores scale.
        Screener transformations are applied to convert BSE raw values to Screener format.
        """
        try:
            logger.info(f"🔄 Syncing quarterly results for {stock.nse_symbol} ({stock.name}) from BSE")
            
            # Only try BSE scraping
            quarterly_results = self.scrape_bse_quarterly_results(stock)
            
            if quarterly_results:
                # Save to database
                saved_count = self.save_quarterly_results(stock.id, quarterly_results)
                
                if saved_count > 0:
                    logger.info(f"✅ Successfully saved {saved_count} quarterly results for {stock.nse_symbol}")
                    
                    # Update sync tracker
                    latest_date = max([qr.get('filing_date', datetime.now().date()) for qr in quarterly_results])
                    self.update_sync_tracker(stock.id, 'quarterly_results', latest_date, saved_count)
                    
                    return saved_count
                else:
                    logger.warning(f"⚠️ No new quarterly results saved for {stock.nse_symbol}")
                    return 0
            else:
                logger.warning(f"⚠️ No quarterly results found for {stock.nse_symbol} on BSE")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Error syncing quarterly results for {stock.nse_symbol} from BSE: {e}")
            # Update sync tracker with error
            self.update_sync_tracker(stock.id, 'quarterly_results', None, 0, 'failed', str(e))
            return 0
    
    def sync_all_stocks(self, limit: int = None):
        """Sync quarterly results for all stocks"""
        logger.info("🚀 Starting BSE Quarterly Results Sync")
        
        db = SessionLocal()
        
        try:
            # Get all stocks with BSE codes
            query = db.query(Stock).filter(Stock.bse_symbol.isnot(None))
            if limit:
                query = query.limit(limit)
            
            stocks = query.all()
            logger.info(f"📊 Found {len(stocks)} stocks to sync")
            
            total_synced = 0
            total_errors = 0
            
            for i, stock in enumerate(stocks, 1):
                logger.info(f"🔄 Processing {i}/{len(stocks)}: {stock.nse_symbol}")
                
                try:
                    synced_count = self.sync_stock_quarterly_results(stock)
                    if synced_count > 0:
                        total_synced += synced_count
                    else:
                        total_errors += 1
                    
                    # Add delay between requests
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {stock.nse_symbol}: {e}")
                    total_errors += 1
                    continue
            
            logger.info("🎉 BSE Quarterly Results Sync completed!")
            logger.info(f"✅ Total quarters synced: {total_synced}")
            logger.info(f"❌ Total errors: {total_errors}")
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            db.close()

def main():
    """Main function"""
    # Test with a few stocks first
    syncer = BSEQuarterlySyncer()
    
    try:
        # Test stocks: Reliance, TCS, Infosys
        test_stocks = ['HDFCBANK', 'ITC', 'DLF']
        
        logger.info(f"🧪 Testing with {len(test_stocks)} stocks: {', '.join(test_stocks)}")
        
        db = SessionLocal()
        try:
            for symbol in test_stocks:
                stock = db.query(Stock).filter(Stock.nse_symbol == symbol).first()
                if stock:
                    logger.info(f"🧪 Testing {symbol}...")
                    syncer.sync_stock_quarterly_results(stock)
                else:
                    logger.warning(f"Stock {symbol} not found in database")
        finally:
            db.close()
        
        # If testing successful, ask user if they want to proceed with all stocks
        response = input("\n🧪 Test completed. Proceed with syncing all stocks? (y/n): ")
        if response.lower() == 'y':
            syncer.sync_all_stocks()
        else:
            logger.info("⏹️ Sync cancelled by user")
            
    finally:
        # Always cleanup resources
        syncer.cleanup()

if __name__ == "__main__":
    main()
