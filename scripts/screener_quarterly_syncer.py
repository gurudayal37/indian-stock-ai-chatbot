#!/usr/bin/env python3
"""
Screener.in Quarterly Results Syncer

This script scrapes quarterly financial results from Screener.in website
and stores them exactly as provided without any transformations.

DATA STORAGE LOGIC - Screener.in Raw Values (NO TRANSFORMATIONS):

IMPORTANT: Screener.in displays all financial values in crores (e.g., "52,788" = 52,788 crores)
All values are stored exactly as provided by Screener.in without any modifications.
Screener.in already provides the correct financial metrics that financial analysts use.

This syncer stores the following fields exactly as provided by Screener.in:

1. Sales: Screener_Sales (no change)
2. Expenses: Screener_Expenses (no change) 
3. Operating Profit: Screener_OperatingProfit (no change)
4. OPM %: Screener_OPM% (no change)
5. Other Income: Screener_OtherIncome (no change)
6. Interest: Screener_Interest (no change)
7. Depreciation: Screener_Depreciation (no change)
8. Profit Before Tax: Screener_PBT (no change)
9. Tax %: Screener_Tax% (no change)
10. Net Profit: Screener_NetProfit (no change)
11. EPS: Screener_EPS (no change)

NO CALCULATIONS OR TRANSFORMATIONS ARE PERFORMED - DATA IS STORED AS-IS

The syncer handles both consolidated and standalone results, defaulting to consolidated.
"""

import time
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

from app.core.database import SessionLocal
from app.models.stock import Stock, QuarterlyResult, SyncTracker
from app.schemas.stock import QuarterlyResultCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScreenerQuarterlySyncer:
    """Scrapes quarterly results from Screener.in website"""
    
    def __init__(self):
        self.base_url = "https://www.screener.in"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Initialize Selenium driver for dynamic content
        self.driver = None
        self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium Chrome driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Selenium Chrome driver initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium: {e}")
            self.driver = None
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Selenium driver closed")
            except Exception as e:
                logger.debug(f"Error closing Selenium driver: {e}")
    
    def sync_stock_quarterly_results(self, stock: Stock) -> bool:
        """Sync quarterly results for a specific stock from Screener.in"""
        try:
            logger.info(f"🔄 Syncing quarterly results for {stock.nse_symbol} ({stock.name}) from Screener.in")
            
            # Construct Screener.in URL
            screener_url = f"{self.base_url}/company/{stock.nse_symbol}/consolidated/#quarters"
            logger.info(f"🔍 Scraping Screener.in URL: {screener_url}")
            
            # Scrape quarterly results
            quarterly_results = self._scrape_screener_quarterly_results(screener_url, stock)
            
            if not quarterly_results:
                logger.warning(f"⚠️ No quarterly results found for {stock.nse_symbol}")
                return False
            
            # Store Screener.in data exactly as provided
            logger.info(f"📊 Storing {len(quarterly_results)} quarterly results exactly as provided by Screener.in...")
            processed_results = self._apply_screener_transformations(quarterly_results)
            
            # Save to database
            success = self._save_quarterly_results(stock, processed_results)
            
            if success:
                logger.info(f"✅ Successfully synced {len(processed_results)} quarterly results for {stock.nse_symbol}")
                return True
            else:
                logger.error(f"❌ Failed to save quarterly results for {stock.nse_symbol}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error syncing quarterly results for {stock.nse_symbol}: {e}")
            return False
    
    def _scrape_screener_quarterly_results(self, url: str, stock: Stock) -> List[Dict[str, Any]]:
        """Scrape quarterly results from Screener.in using Selenium"""
        try:
            if not self.driver:
                logger.warning(f"⚠️ Selenium not available, using requests fallback for {stock.nse_symbol}")
                return self._scrape_with_requests(url, stock)
            
            logger.info(f"🚀 Using Selenium to scrape {stock.nse_symbol}")
            
            # Navigate to the page
            self.driver.get(url)
            logger.info(f"📄 Navigated to Screener.in page for {stock.nse_symbol}")
            
            # Wait for page to load
            time.sleep(5)
            logger.info(f"⏳ Waited for page to load for {stock.nse_symbol}")
            
            # Check if quarterly results table is present
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                )
                logger.info(f"✅ Found quarterly results table for {stock.nse_symbol}")
            except TimeoutException:
                logger.warning(f"⚠️ Quarterly results table not found for {stock.nse_symbol}")
                return []
            
            # Debug page content
            logger.info(f"🔍 Debugging page content for {stock.nse_symbol}")
            page_title = self.driver.title
            current_url = self.driver.current_url
            logger.info(f"📋 Page title: {page_title}")
            logger.info(f"🔗 Current URL: {current_url}")
            
            # Save HTML for debugging
            html_content = self.driver.page_source
            with open(f'debug_screener_{stock.nse_symbol}.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"💾 Saved Selenium HTML to debug_screener_{stock.nse_symbol}.html")
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            return self._parse_screener_html(soup, stock)
            
        except Exception as e:
            logger.error(f"❌ Selenium scraping failed for {stock.nse_symbol}: {e}")
            return self._scrape_with_requests(url, stock)
    
    def _scrape_with_requests(self, url: str, stock: Stock) -> List[Dict[str, Any]]:
        """Fallback scraping using requests (for when Selenium is not available)"""
        try:
            logger.info(f"📡 Using requests fallback for {stock.nse_symbol}")
            
            # Add delay to be respectful to Screener.in servers
            time.sleep(2)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Save HTML content for inspection
            with open(f'debug_screener_{stock.nse_symbol}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"🔍 Saved HTML content to debug_screener_{stock.nse_symbol}.html")
            
            return self._parse_screener_html(soup, stock)
            
        except Exception as e:
            logger.error(f"❌ Requests scraping failed for {stock.nse_symbol}: {e}")
            return []
    
    def _parse_screener_html(self, soup: BeautifulSoup, stock: Stock) -> List[Dict[str, Any]]:
        """Parse Screener.in HTML content for quarterly results"""
        quarterly_results = []
        
        logger.info(f"🔍 Parsing Screener.in HTML for {stock.nse_symbol}")
        
        # Look for the quarterly results table
        # Screener.in has a specific table structure for quarterly results
        tables = soup.find_all('table')
        logger.info(f"📊 Found {len(tables)} tables to analyze")
        
        for i, table in enumerate(tables):
            try:
                # Look for table headers
                headers = table.find_all(['th', 'td'])
                if not headers:
                    continue
                
                # Check if this looks like a quarterly results table
                header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
                
                # Screener.in quarterly tables typically have month/quarter headers
                if any(keyword in header_text for keyword in ['jun', 'mar', 'dec', 'sep', 'sales', 'expenses', 'operating profit']):
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
                            if any(month in cell_text for month in ['jun', 'mar', 'dec', 'sep']):
                                header_row = row
                                break
                    
                    if not header_row:
                        logger.debug(f"Table {i+1}: No header row found with month patterns")
                        continue
                    
                    # Extract quarter information from header row
                    header_cells = header_row.find_all(['td', 'th'])
                    quarters = []
                    
                    # Screener.in shows all values in crores - just parse all columns that look like quarters
                    for cell in header_cells:
                        cell_text = cell.get_text(strip=True).strip()
                        if any(month in cell_text.lower() for month in ['jun', 'mar', 'dec', 'sep']):
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
                        if not metric_name or metric_name in ['quarterly results', 'consolidated', 'standalone']:
                            continue
                        
                        # Check if this is a financial metric we care about
                        if any(keyword in metric_name for keyword in ['sales', 'expenses', 'operating profit', 'opm %', 'other income', 'interest', 'depreciation', 'profit before tax', 'tax', 'tax %', 'net profit', 'eps']):
                            logger.debug(f"📊 Processing metric: {metric_name}")
                            
                            # Extract values for each quarter (simple sequential indexing)
                            for quarter_idx, quarter in enumerate(quarters):
                                # Use simple sequential indexing since all values are in crores
                                value_cell_idx = quarter_idx + 1
                                
                                if value_cell_idx < len(cells):  # Ensure we have enough cells
                                    value_cell = cells[value_cell_idx]
                                    value_text = value_cell.get_text(strip=True).strip()
                                    
                                    # Skip if no value or if it's a link
                                    if not value_text or value_text in ['--', 'consolidated', 'standalone']:
                                        continue
                                    
                                    try:
                                        # Parse the quarter to get year and quarter number
                                        quarter_data = self._parse_quarter_from_text(quarter)
                                        if quarter_data:
                                            year, quarter_num = quarter_data
                                            
                                            # Create quarterly result record
                                            quarter_record = self._create_quarterly_record_from_screener(
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
                    
                    # If we found quarterly results, break out of table loop
                    if quarterly_results:
                        break
                        
            except Exception as e:
                logger.debug(f"Error parsing table {i+1}: {e}")
                continue
        
        if quarterly_results:
            logger.info(f"✅ Successfully parsed and transformed {len(quarterly_results)} quarterly results from Screener.in")
            return quarterly_results
        else:
            logger.warning(f"⚠️ No quarterly results found in any table for {stock.nse_symbol}")
            return []
    
    def _parse_quarter_from_text(self, quarter_text: str) -> Optional[Tuple[int, int]]:
        """Parse quarter text to extract year and quarter number"""
        try:
            # Screener.in format: "Jun 2025", "Mar 2024", etc.
            quarter_text = quarter_text.strip()
            
            # Extract month and year
            month_match = re.search(r'(jun|mar|dec|sep)\s+(\d{4})', quarter_text.lower())
            if month_match:
                month = month_match.group(1)
                year = int(month_match.group(2))
                
                # Map month to quarter number
                month_to_quarter = {
                    'jun': 2,  # Q2
                    'sep': 3,  # Q3  
                    'dec': 4,  # Q4
                    'mar': 1   # Q1
                }
                
                quarter_num = month_to_quarter.get(month)
                if quarter_num:
                    return year, quarter_num
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing quarter text '{quarter_text}': {e}")
            return None
    
    def _create_quarterly_record_from_screener(self, stock: Stock, year: int, quarter_num: int, 
                                            metric_name: str, value_text: str) -> Optional[Dict[str, Any]]:
        """Create quarterly result record from Screener.in data"""
        try:
            # Create quarter display string
            quarter = f"Q{quarter_num} {year}"
            
            # Initialize quarter record
            quarter_record = {
                'quarter': quarter,
                'year': year,
                'quarter_number': quarter_num,
                'source': 'Screener',
                'quarterly_result_link': f"https://www.screener.in/company/{stock.nse_symbol}/consolidated/#quarters",
                'announcement_date': date.today(),
                'filing_date': date.today(),
                'is_consolidated': True  # Default to consolidated for Screener.in
            }
            
            # Store raw Screener.in values for reference and calculations
            raw_values = {}
            
            # Map metric names to database fields and store raw values
            metric_mapping = {
                'sales': 'revenue',
                'sales+': 'revenue',  # Screener.in uses "Sales+" format
                'expenses': 'expenditure',
                'expenses+': 'expenditure',  # Screener.in uses "Expenses+" format
                'operating profit': 'operating_profit',
                'opm %': 'opm_percent',  # Screener.in uses "opm %" format (lowercase)
                'other income': 'other_income',
                'other income+': 'other_income',  # Screener.in uses "Other Income+" format
                'interest': 'interest',
                'depreciation': 'depreciation',
                'profit before tax': 'pbt',
                'tax': 'tax',
                'tax %': 'tax_percent',  # Screener.in uses "tax %" format (lowercase)
                'net profit': 'net_profit',
                'net profit+': 'net_profit',  # Screener.in uses "Net Profit+" format
                'npm %': 'npm_percent',  # Screener.in uses "NPM %" format (if available)
                'eps': 'eps',
                'eps in rs': 'eps'  # Screener.in uses "EPS in Rs" format
            }
            
            # Set the raw metric value and store for calculations
            logger.debug(f"🔍 Processing metric: '{metric_name}' -> looking for match in mapping")
            db_field = metric_mapping.get(metric_name)
            if db_field:
                # Parse numeric value
                raw_value = self._parse_numeric_value(value_text)
                if raw_value is not None:
                    # Store raw Screener.in value in both raw_values and quarter_record
                    raw_values[db_field] = raw_value
                    quarter_record[db_field] = raw_value
                    logger.debug(f"✅ Set {db_field} = {raw_value} (raw Screener.in value) for Q{quarter_num} {year}")
            else:
                logger.debug(f"⚠️ No mapping found for metric: '{metric_name}'")
            
            # Note: All Screener transformations are now handled in _apply_screener_transformations
            # after all metrics for a quarter are collected
            
            return quarter_record
            
        except Exception as e:
            logger.debug(f"Error creating quarterly record: {e}")
            return None
    
    def _parse_numeric_value(self, value_text: str) -> Optional[float]:
        """Parse numeric value from text, handling Screener.in's format
        
        Screener.in displays financial values in crores (e.g., "52,788" = 52,788 crores)
        This method parses the text and returns the value in crores, no scaling applied.
        """
        try:
            # Remove common non-numeric characters
            cleaned_text = value_text.replace(',', '').replace('(', '').replace(')', '').strip()
            
            # Handle negative values (Screener.in uses parentheses for negatives)
            is_negative = value_text.startswith('(') and value_text.endswith(')')
            
            # Extract numeric part
            numeric_match = re.search(r'([\d,]+\.?\d*)', cleaned_text)
            if numeric_match:
                numeric_value = float(numeric_match.group(1).replace(',', ''))
                
                # Screener.in shows values in crores (e.g., "52,788" means 52,788 crores)
                # We store these values as-is in crores, no scaling needed
                # The values should match exactly what Screener.in displays
                
                logger.debug(f"🔍 Parsed '{value_text}' -> cleaned: '{cleaned_text}' -> extracted: '{numeric_match.group(1)}' -> final: {numeric_value}")
                
                # Screener.in shows all values in crores - no scaling validation needed
                # Values like 52,788.00 are correctly 52,788 crores
                
                return -numeric_value if is_negative else numeric_value
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing numeric value '{value_text}': {e}")
            return None
    
    def _apply_screener_transformations(self, quarterly_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store Screener.in data exactly as provided - NO TRANSFORMATIONS NEEDED"""
        logger.info(f"📊 Storing {len(quarterly_results)} quarterly results exactly as provided by Screener.in...")
        
        for quarter_record in quarterly_results:
            logger.info(f"📊 Storing {quarter_record['quarter']} data from Screener.in without modifications")
            
            try:
                # Screener.in already provides correct financial metrics - no transformations needed
                # Just ensure we have the required fields for our database
                if quarter_record.get('operating_profit') is not None:
                    quarter_record['ebitda'] = quarter_record['operating_profit']  # EBITDA = Operating Profit
                
                # Set operating_margin and net_margin to match the percentages from Screener.in
                if quarter_record.get('opm_percent') is not None:
                    quarter_record['operating_margin'] = quarter_record['opm_percent']
                if quarter_record.get('npm_percent') is not None:
                    quarter_record['net_margin'] = quarter_record['npm_percent']
                
                # Ensure tax_percent is properly set
                if quarter_record.get('tax_percent') is not None:
                    quarter_record['tax_percent'] = quarter_record['tax_percent']
                
                logger.info(f"✅ Stored {quarter_record['quarter']} data exactly as provided by Screener.in")
                
            except Exception as e:
                logger.error(f"❌ Error processing {quarter_record['quarter']}: {e}")
        
        return quarterly_results
    
    def _save_quarterly_results(self, stock: Stock, quarterly_results: List[Dict[str, Any]]) -> bool:
        """Save quarterly results to database"""
        try:
            db = SessionLocal()
            
            # Check for existing quarterly results
            existing_quarters = set()
            existing_records = db.query(QuarterlyResult).filter(
                QuarterlyResult.stock_id == stock.id,
                QuarterlyResult.source == 'Screener'
            ).all()
            
            for record in existing_records:
                existing_quarters.add((record.quarter, record.year))
            
            # Insert new quarterly results
            new_records = []
            for quarter_data in quarterly_results:
                quarter_key = (quarter_data['quarter'], quarter_data['year'])
                
                if quarter_key not in existing_quarters:
                    # Create new record
                    quarter_record = QuarterlyResult(
                        stock_id=stock.id,
                        quarter=quarter_data['quarter'],
                        year=quarter_data['year'],
                        quarter_number=quarter_data['quarter_number'],
                        revenue=quarter_data.get('revenue'),
                        net_profit=quarter_data.get('net_profit'),
                        ebitda=quarter_data.get('ebitda'),
                        operating_profit=quarter_data.get('operating_profit'),
                        other_income=quarter_data.get('other_income'),
                        total_income=quarter_data.get('total_income'),
                        expenditure=quarter_data.get('expenditure'),
                        interest=quarter_data.get('interest'),
                        depreciation=quarter_data.get('depreciation'),
                        pbt=quarter_data.get('pbt'),
                        tax=quarter_data.get('tax'),
                        equity=quarter_data.get('equity'),
                        eps=quarter_data.get('eps'),
                        operating_margin=quarter_data.get('operating_margin'),
                        net_margin=quarter_data.get('net_margin'),
                        opm_percent=quarter_data.get('opm_percent'),
                        npm_percent=quarter_data.get('npm_percent'),
                        tax_percent=quarter_data.get('tax_percent'),
                        is_consolidated=quarter_data.get('is_consolidated', True),
                        announcement_date=quarter_data.get('announcement_date'),
                        filing_date=quarter_data.get('filing_date'),
                        quarterly_result_link=quarter_data.get('quarterly_result_link'),
                        source=quarter_data.get('source', 'Screener')
                    )
                    new_records.append(quarter_record)
                    logger.debug(f"✅ Created new quarterly record for {quarter_data['quarter']}")
                else:
                    logger.debug(f"⏭️ Skipping existing quarterly record for {quarter_data['quarter']}")
            
            if new_records:
                db.add_all(new_records)
                db.commit()
                logger.info(f"✅ Successfully saved {len(new_records)} quarterly results for {stock.nse_symbol}")
            else:
                logger.info(f"ℹ️ No new quarterly results to save for {stock.nse_symbol}")
            
            # Update sync tracker
            self._update_sync_tracker(db, stock, len(new_records))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving quarterly results for {stock.nse_symbol}: {e}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def _update_sync_tracker(self, db: SessionLocal, stock: Stock, records_count: int):
        """Update sync tracker for the stock"""
        try:
            sync_tracker = db.query(SyncTracker).filter(
                SyncTracker.stock_id == stock.id,
                SyncTracker.data_type == 'quarterly_results'
            ).first()
            
            if sync_tracker:
                sync_tracker.last_sync_time = datetime.now()
                sync_tracker.last_data_date = date.today()
                sync_tracker.records_count = records_count
                sync_tracker.sync_status = 'success'
                sync_tracker.error_message = None
            else:
                sync_tracker = SyncTracker(
                    stock_id=stock.id,
                    data_type='quarterly_results',
                    last_sync_time=datetime.now(),
                    last_data_date=date.today(),
                    records_count=records_count,
                    sync_status='success'
                )
                db.add(sync_tracker)
            
            db.commit()
            logger.debug(f"✅ Updated sync tracker for {stock.nse_symbol}")
            
        except Exception as e:
            logger.debug(f"Error updating sync tracker for {stock.nse_symbol}: {e}")
            db.rollback()


def main():
    """Main function to test the Screener quarterly syncer"""
    try:
        # Initialize syncer
        syncer = ScreenerQuarterlySyncer()
        
        # Get database session
        db = SessionLocal()
        
        # Test stocks
        test_stocks = ['HDFCBANK', 'ITC', 'DLF', 'RELIANCE']
        
        for symbol in test_stocks:
            try:
                # Get stock from database
                stock = db.query(Stock).filter(Stock.nse_symbol == symbol).first()
                
                if stock:
                    print(f"🔄 Testing Screener syncer with {stock.nse_symbol} (BSE: {stock.bse_symbol})")
                    
                    # Sync quarterly results
                    success = syncer.sync_stock_quarterly_results(stock)
                    
                    if success:
                        print(f"✅ {stock.nse_symbol} completed successfully")
                    else:
                        print(f"❌ {stock.nse_symbol} failed")
                else:
                    print(f"❌ Stock {symbol} not found in database")
                    
            except Exception as e:
                print(f"❌ Error processing {symbol}: {str(e)}")
                continue
        
        db.close()
        
    except Exception as e:
        print(f"❌ Main error: {str(e)}")
    finally:
        if 'syncer' in locals():
            syncer.cleanup()


if __name__ == "__main__":
    main()
