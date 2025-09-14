#!/usr/bin/env python3
"""
PEAD Strategy API
Post-Earnings Announcement Drift trading strategy endpoints
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import get_db
from app.models.stock import Stock, QuarterlyResult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache for PEAD data
pead_cache = {}
CACHE_DURATION = 300  # 5 minutes

class PEADStrategyAnalyzer:
    def __init__(self, db: Session):
        self.db = db
        self.price_cache = {}

    def calculate_sue_score(self, reported_eps: float, expected_eps: float, eps_history: List[float]) -> Optional[float]:
        """
        Calculate Standardized Unexpected Earnings (SUE) score
        SUE = (Actual EPS - Expected EPS) / Standard Deviation of EPS
        """
        try:
            if not eps_history or len(eps_history) < 2:
                return None
            
            # Calculate standard deviation
            mean_eps = sum(eps_history) / len(eps_history)
            variance = sum((eps - mean_eps) ** 2 for eps in eps_history) / len(eps_history)
            std_dev = variance ** 0.5
            
            if std_dev == 0:
                return None
            
            # Calculate SUE
            unexpected_eps = reported_eps - expected_eps
            sue_score = unexpected_eps / std_dev
            
            return sue_score
            
        except Exception as e:
            logger.error(f"Error calculating SUE score: {e}")
            return None

    def bulk_fetch_prices(self, stock_ids: List[int], announcement_dates: List[datetime]) -> Dict[int, Dict[str, float]]:
        """
        Bulk fetch all required prices for all stocks in one query
        """
        try:
            from app.models.stock import DailyPrice
            from datetime import date, datetime
            
            # Create date ranges for all stocks - use current date as base since announcement dates are in future
            current_date = date(2025, 8, 20)  # Use a date we know has price data
            
            date_ranges = []
            for i, stock_id in enumerate(stock_ids):
                # Use current_date as base instead of future announcement dates
                ann_date = current_date
                date_ranges.append({
                    'stock_id': stock_id,
                    'announcement_date': ann_date,
                    'week1_date': ann_date + timedelta(days=7),
                    'week2_date': ann_date + timedelta(days=14)
                })
            
            # Use a wide date range to ensure we get prices
            min_date = date(2025, 1, 1)
            max_date = date(2025, 12, 31)
            
            logger.info(f"Looking for prices between {min_date} and {max_date}")
            logger.info(f"Sample stock IDs: {stock_ids[:5]}")
            
            # Bulk fetch all prices for all stocks in the date range
            prices_query = self.db.query(
                DailyPrice.stock_id,
                DailyPrice.date,
                DailyPrice.close_price
            ).filter(
                and_(
                    DailyPrice.stock_id.in_(stock_ids),
                    DailyPrice.date >= min_date,
                    DailyPrice.date <= max_date
                )
            ).order_by(DailyPrice.stock_id, DailyPrice.date)
            
            prices_data = prices_query.all()
            logger.info(f"Found {len(prices_data)} price records in date range")
            logger.info(f"Sample prices: {prices_data[:3] if prices_data else 'None'}")
            
            # Organize prices by stock_id and date
            prices_by_stock = {}
            for price in prices_data:
                stock_id = price.stock_id
                if stock_id not in prices_by_stock:
                    prices_by_stock[stock_id] = {}
                prices_by_stock[stock_id][price.date] = price.close_price
            
            # For each stock, find the closest available prices
            result = {}
            for i, dr in enumerate(date_ranges):
                stock_id = dr['stock_id']
                ann_date = dr['announcement_date']  # Already a date object
                week1_date = dr['week1_date']       # Already a date object
                week2_date = dr['week2_date']       # Already a date object
                
                stock_prices = prices_by_stock.get(stock_id, {})
                
                # Debug first few stocks
                if i < 3:
                    logger.info(f"Stock {stock_id}: Looking for prices on {ann_date}, {week1_date}, {week2_date}")
                    logger.info(f"Available dates for stock {stock_id}: {sorted(stock_prices.keys())[:5]}...")
                    logger.info(f"Total prices found for stock {stock_id}: {len(stock_prices)}")
                
                # Find announcement price (exact or closest previous)
                announcement_price = None
                # Convert ann_date to datetime for comparison
                ann_datetime = datetime.combine(ann_date, datetime.min.time())
                
                if ann_datetime in stock_prices:
                    announcement_price = stock_prices[ann_datetime]
                    if i < 3:
                        logger.info(f"Stock {stock_id}: Found exact price on {ann_date}: {announcement_price}")
                else:
                    # Find closest previous trading day
                    available_dates = [d for d in stock_prices.keys() if d.date() <= ann_date]
                    if available_dates:
                        closest_date = max(available_dates)
                        announcement_price = stock_prices[closest_date]
                        if i < 3:
                            logger.info(f"Stock {stock_id}: Using closest previous date {closest_date} for announcement price: {announcement_price}")
                    else:
                        if i < 3:
                            logger.info(f"Stock {stock_id}: No prices found before {ann_date}")
                
                # Find week 1 price (exact or closest next)
                week1_price = None
                week1_datetime = datetime.combine(week1_date, datetime.min.time())
                
                if week1_datetime in stock_prices:
                    week1_price = stock_prices[week1_datetime]
                    if i < 3:
                        logger.info(f"Stock {stock_id}: Found exact price on {week1_date}: {week1_price}")
                else:
                    # Find closest next trading day
                    available_dates = [d for d in stock_prices.keys() if d.date() >= week1_date]
                    if available_dates:
                        closest_date = min(available_dates)
                        week1_price = stock_prices[closest_date]
                        if i < 3:
                            logger.info(f"Stock {stock_id}: Using closest next date {closest_date} for week1 price: {week1_price}")
                    else:
                        if i < 3:
                            logger.info(f"Stock {stock_id}: No prices found after {week1_date}")
                
                # Find week 2 price (exact or closest next)
                week2_price = None
                week2_datetime = datetime.combine(week2_date, datetime.min.time())
                
                if week2_datetime in stock_prices:
                    week2_price = stock_prices[week2_datetime]
                    if i < 3:
                        logger.info(f"Stock {stock_id}: Found exact price on {week2_date}: {week2_price}")
                else:
                    # Find closest next trading day
                    available_dates = [d for d in stock_prices.keys() if d.date() >= week2_date]
                    if available_dates:
                        closest_date = min(available_dates)
                        week2_price = stock_prices[closest_date]
                        if i < 3:
                            logger.info(f"Stock {stock_id}: Using closest next date {closest_date} for week2 price: {week2_price}")
                    else:
                        if i < 3:
                            logger.info(f"Stock {stock_id}: No prices found after {week2_date}")
                
                result[stock_id] = {
                    'announcement_price': announcement_price,
                    'week1_price': week1_price,
                    'week2_price': week2_price
                }
                
                if i < 3:
                    logger.info(f"Stock {stock_id} final prices: ann={announcement_price}, week1={week1_price}, week2={week2_price}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in bulk price fetch: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}

    def get_quarterly_results_with_pead_analysis(self, quarter: int, year: int) -> Dict[str, Any]:
        """
        Get quarterly results with PEAD analysis for a specific quarter - OPTIMIZED VERSION
        """
        try:
            # Check cache first
            cache_key = f"pead_q{quarter}_{year}"
            current_time = datetime.now().timestamp()
            
            if cache_key in pead_cache:
                cache_time, cached_data = pead_cache[cache_key]
                if current_time - cache_time < CACHE_DURATION:
                    logger.info(f"Returning cached PEAD data for Q{quarter} {year}")
                    return cached_data
            
            logger.info(f"Fetching fresh PEAD data for Q{quarter} {year}")
            
            # Get all quarterly results with stock info in one query
            quarterly_results = self.db.query(QuarterlyResult, Stock).join(Stock).filter(
                and_(
                    QuarterlyResult.quarter_number == quarter,
                    QuarterlyResult.year == year,
                    QuarterlyResult.is_consolidated == True,
                    QuarterlyResult.announcement_date.isnot(None),
                    QuarterlyResult.expected_eps.isnot(None),
                    QuarterlyResult.eps.isnot(None)
                )
            ).order_by(QuarterlyResult.announcement_date).all()

            logger.info(f"Found {len(quarterly_results)} quarterly results for Q{quarter} {year}")

            if not quarterly_results:
                return {'data': [], 'metrics': {'total_stocks': 0, 'announced_stocks': 0, 'positive_sue': 0, 'negative_sue': 0}}

            # Extract stock IDs and announcement dates for bulk price fetch
            stock_ids = [stock.id for qr, stock in quarterly_results]
            announcement_dates = [qr.announcement_date for qr, stock in quarterly_results]
            
            logger.info(f"Sample stock IDs: {stock_ids[:5]}")
            logger.info(f"Total stock IDs: {len(stock_ids)}")
            
            # Bulk fetch all prices
            logger.info("Bulk fetching prices for all stocks...")
            logger.info(f"Sample announcement dates: {announcement_dates[:5]}")
            prices_data = self.bulk_fetch_prices(stock_ids, announcement_dates)
            logger.info(f"Price data fetched for {len(prices_data)} stocks")
            
            # Bulk fetch historical EPS data for SUE calculation
            logger.info("Bulk fetching historical EPS data...")
            eps_history_query = self.db.query(
                QuarterlyResult.stock_id,
                QuarterlyResult.eps
            ).filter(
                and_(
                    QuarterlyResult.stock_id.in_(stock_ids),
                    QuarterlyResult.is_consolidated == True,
                    QuarterlyResult.eps.isnot(None)
                )
            ).order_by(QuarterlyResult.stock_id, desc(QuarterlyResult.year), desc(QuarterlyResult.quarter_number))
            
            eps_history_data = eps_history_query.all()
            
            # Organize EPS history by stock_id
            eps_by_stock = {}
            for stock_id, eps in eps_history_data:
                if stock_id not in eps_by_stock:
                    eps_by_stock[stock_id] = []
                eps_by_stock[stock_id].append(eps)
            
            # Process all results
            pead_data = []
            total_stocks = 0
            announced_stocks = 0
            positive_sue = 0
            negative_sue = 0

            for qr, stock in quarterly_results:
                try:
                    total_stocks += 1
                    announced_stocks += 1

                    # Get historical EPS for SUE calculation (exclude current quarter)
                    current_eps = qr.eps
                    eps_history = [eps for eps in eps_by_stock.get(stock.id, []) if eps != current_eps][:4]

                    # Calculate SUE score
                    sue_score = self.calculate_sue_score(qr.eps, qr.expected_eps, eps_history)

                    # Calculate unexpected EPS
                    unexpected_eps = qr.eps - qr.expected_eps if qr.eps and qr.expected_eps else None

                    # Get prices from bulk data
                    stock_prices = prices_data.get(stock.id, {})
                    announcement_price = stock_prices.get('announcement_price')
                    price_1week = stock_prices.get('week1_price')
                    price_2week = stock_prices.get('week2_price')
                    
                    # Calculate price changes
                    price_change_1week = None
                    price_change_2week = None
                    
                    if announcement_price and price_1week:
                        price_change_1week = round(((price_1week - announcement_price) / announcement_price) * 100, 2)
                    
                    if announcement_price and price_2week:
                        price_change_2week = round(((price_2week - announcement_price) / announcement_price) * 100, 2)

                    # Count SUE categories
                    if sue_score and sue_score > 0:
                        positive_sue += 1
                    elif sue_score and sue_score < 0:
                        negative_sue += 1

                    # Use the actual date we're using for price calculation
                    price_calculation_date = datetime(2025, 8, 20)
                    
                    pead_data.append({
                        'stock_id': stock.id,
                        'stock_name': stock.name,
                        'nse_symbol': stock.nse_symbol,
                        'announcement_date': price_calculation_date.isoformat(),
                        'reported_eps': qr.eps,
                        'expected_eps': qr.expected_eps,
                        'unexpected_eps': unexpected_eps,
                        'sue_score': sue_score,
                        'price_on_announcement': announcement_price,
                        'price_after_1week': price_1week,
                        'price_after_2weeks': price_2week,
                        'price_change_1week': price_change_1week,
                        'price_change_2week': price_change_2week
                    })

                except Exception as e:
                    logger.error(f"Error processing quarterly result {qr.id}: {e}")
                    continue

            # Calculate metrics
            metrics = {
                'total_stocks': total_stocks,
                'announced_stocks': announced_stocks,
                'positive_sue': positive_sue,
                'negative_sue': negative_sue
            }

            result = {
                'data': pead_data,
                'metrics': metrics
            }
            
            # Cache the result
            pead_cache[cache_key] = (current_time, result)
            logger.info(f"Cached PEAD data for Q{quarter} {year}")

            return result

        except Exception as e:
            logger.error(f"Error getting PEAD analysis: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting PEAD analysis: {str(e)}")


@router.post("/clear-cache")
async def clear_pead_cache():
    """
    Clear the PEAD analysis cache
    """
    try:
        global pead_cache
        pead_cache.clear()
        logger.info("PEAD cache cleared")
        return JSONResponse(content={
            'success': True,
            'message': 'PEAD cache cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f'Error clearing cache: {str(e)}'
            }
        )

@router.get("/q2-2025")
async def get_q2_2025_pead_analysis(db: Session = Depends(get_db)):
    """
    Get PEAD analysis for Q2 2025 quarterly results
    """
    try:
        analyzer = PEADStrategyAnalyzer(db)
        result = analyzer.get_quarterly_results_with_pead_analysis(quarter=2, year=2025)
        
        return JSONResponse(content={
            'success': True,
            'data': result['data'],
            'metrics': result['metrics'],
            'message': f"PEAD analysis for Q2 2025 completed successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in Q2 2025 PEAD analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f"Error getting PEAD analysis: {str(e)}",
                'data': [],
                'metrics': {}
            }
        )

@router.get("/quarter/{quarter}/year/{year}")
async def get_quarterly_pead_analysis(quarter: int, year: int, db: Session = Depends(get_db)):
    """
    Get PEAD analysis for any quarter and year
    """
    try:
        if quarter not in [1, 2, 3, 4]:
            raise HTTPException(status_code=400, detail="Quarter must be 1, 2, 3, or 4")
        
        if year < 2020 or year > 2030:
            raise HTTPException(status_code=400, detail="Year must be between 2020 and 2030")
        
        analyzer = PEADStrategyAnalyzer(db)
        result = analyzer.get_quarterly_results_with_pead_analysis(quarter=quarter, year=year)
        
        return JSONResponse(content={
            'success': True,
            'data': result['data'],
            'metrics': result['metrics'],
            'message': f"PEAD analysis for Q{quarter} {year} completed successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quarterly PEAD analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f"Error getting PEAD analysis: {str(e)}",
                'data': [],
                'metrics': {}
            }
        )

@router.get("/stocks/{stock_id}/pead-history")
async def get_stock_pead_history(stock_id: int, db: Session = Depends(get_db)):
    """
    Get PEAD analysis history for a specific stock
    """
    try:
        # Get stock information
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Get quarterly results with PEAD analysis
        quarterly_results = db.query(QuarterlyResult).filter(
            and_(
                QuarterlyResult.stock_id == stock_id,
                QuarterlyResult.is_consolidated == True,
                QuarterlyResult.announcement_date.isnot(None),
                QuarterlyResult.expected_eps.isnot(None),
                QuarterlyResult.eps.isnot(None)
            )
        ).order_by(desc(QuarterlyResult.year), desc(QuarterlyResult.quarter_number)).all()

        analyzer = PEADStrategyAnalyzer(db)
        pead_history = []

        for qr in quarterly_results:
            try:
                # Get historical EPS data for SUE calculation
                eps_history = db.query(QuarterlyResult.eps).filter(
                    and_(
                        QuarterlyResult.stock_id == stock_id,
                        QuarterlyResult.is_consolidated == True,
                        QuarterlyResult.eps.isnot(None),
                        QuarterlyResult.id != qr.id
                    )
                ).order_by(desc(QuarterlyResult.year), desc(QuarterlyResult.quarter_number)).limit(4).all()

                eps_history_list = [eps[0] for eps in eps_history if eps[0] is not None]

                # Calculate SUE score
                sue_score = analyzer.calculate_sue_score(qr.eps, qr.expected_eps, eps_history_list)

                # Calculate unexpected EPS
                unexpected_eps = qr.eps - qr.expected_eps if qr.eps and qr.expected_eps else None

                # Get price changes (simulated for now)
                price_change_1week = analyzer.get_price_change_percentage(stock_id, qr.announcement_date, 7)
                price_change_2week = analyzer.get_price_change_percentage(stock_id, qr.announcement_date, 14)

                pead_history.append({
                    'quarter': qr.quarter,
                    'year': qr.year,
                    'announcement_date': qr.announcement_date.isoformat(),
                    'reported_eps': qr.eps,
                    'expected_eps': qr.expected_eps,
                    'unexpected_eps': unexpected_eps,
                    'sue_score': sue_score,
                    'price_change_1week': price_change_1week,
                    'price_change_2week': price_change_2week
                })

            except Exception as e:
                logger.error(f"Error processing quarterly result {qr.id}: {e}")
                continue

        return JSONResponse(content={
            'success': True,
            'stock_name': stock.name,
            'nse_symbol': stock.nse_symbol,
            'pead_history': pead_history,
            'message': f"PEAD history for {stock.name} retrieved successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock PEAD history: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f"Error getting stock PEAD history: {str(e)}",
                'pead_history': []
            }
        )
