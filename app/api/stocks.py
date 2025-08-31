from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.stock import Stock, DailyPrice, QuarterlyResult
from app.schemas.stock import StockResponse, StockDetailResponse

router = APIRouter()

@router.get("/stocks", response_model=List[StockResponse])
async def list_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sector: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all stocks with pagination and filtering"""
    try:
        query = db.query(Stock).filter(Stock.is_active == True)
        
        if sector:
            query = query.filter(Stock.sector == sector)
        if industry:
            query = query.filter(Stock.industry == industry)
        
        stocks = query.offset(skip).limit(limit).all()
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stocks/featured")
async def get_featured_stocks(db: Session = Depends(get_db)):
    """Get the 3 featured stocks (RELIANCE, TCS, INFY) with comprehensive data"""
    try:
        # Get the 3 specific stocks
        featured_symbols = ['RELIANCE', 'TCS', 'INFY']
        stocks = []
        
        for symbol in featured_symbols:
            stock = db.query(Stock).filter(
                (Stock.bse_symbol == symbol) | (Stock.nse_symbol == symbol)
            ).first()
            
            if stock:
                # Get latest quarterly result
                latest_quarterly = db.query(QuarterlyResult).filter(
                    QuarterlyResult.stock_id == stock.id
                ).order_by(
                    QuarterlyResult.year.desc(),
                    QuarterlyResult.quarter_number.desc()
                ).first()
                
                # Get latest daily price
                latest_price = db.query(DailyPrice).filter(
                    DailyPrice.stock_id == stock.id
                ).order_by(DailyPrice.date.desc()).first()
                
                stock_data = {
                    "id": stock.id,
                    "name": stock.name,
                    "nse_symbol": stock.nse_symbol,
                    "bse_symbol": stock.bse_symbol,
                    "current_price": stock.current_price,
                    "market_cap": stock.market_cap,
                    "face_value": stock.face_value,
                    "high_52_week": stock.high_52_week,
                    "low_52_week": stock.low_52_week,
                    "pe_ratio": stock.pe_ratio,
                    "pb_ratio": stock.pb_ratio,
                    "book_value": stock.book_value,
                    "dividend_yield": stock.dividend_yield,
                    "roce": stock.roce,
                    "roe": stock.roe,
                    "industry": stock.industry,
                    "sector": stock.sector,
                    "latest_quarterly": latest_quarterly,
                    "latest_price": latest_price
                }
                stocks.append(stock_data)
        
        return stocks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stocks/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific stock"""
    try:
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        return stock
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stocks/{symbol}/quarterly-results")
async def get_quarterly_results(
    symbol: str, 
    quarters: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get quarterly results for a stock"""
    try:
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Only return Screener.in data (better quality, more comprehensive)
        results = db.query(QuarterlyResult).filter(
            QuarterlyResult.stock_id == stock.id,
            QuarterlyResult.source == 'Screener'
        ).order_by(
            QuarterlyResult.year.desc(),
            QuarterlyResult.quarter_number.desc()
        ).limit(quarters).all()
        
        # Format results for better UI display
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "quarter": result.quarter,
                "year": result.year,
                "quarter_number": result.quarter_number,
                "revenue": result.revenue,
                "net_profit": result.net_profit,
                "ebitda": result.ebitda,
                "operating_profit": result.operating_profit,
                "other_income": result.other_income,
                "total_income": result.total_income,
                "expenditure": result.expenditure,
                "opm_percent": result.opm_percent,
                "npm_percent": result.npm_percent,
                "operating_margin": result.operating_margin,
                "net_margin": result.net_margin,
                "eps": result.eps,
                "ceps": result.ceps,
                "pbdt": result.pbdt,
                "pbt": result.pbt,
                "depreciation": result.depreciation,
                "interest": result.interest,
                "tax": result.tax,
                "tax_percent": result.tax_percent,
                "equity": result.equity,
                "announcement_date": result.announcement_date,
                "filing_date": result.filing_date,
                "source": result.source,
                "is_consolidated": result.is_consolidated
            })
        
        return formatted_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stocks/{symbol}/daily-prices")
async def get_daily_prices(
    symbol: str,
    days: int = Query(365, ge=1, le=1095),
    db: Session = Depends(get_db)
):
    """Get daily price data for a stock"""
    try:
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Calculate start date
        start_date = datetime.now() - timedelta(days=days)
        
        # Get daily prices
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.id,
            DailyPrice.date >= start_date
        ).order_by(DailyPrice.date.asc()).all()
        
        # Format data for charting
        chart_data = []
        for price in prices:
            chart_data.append({
                "date": price.date.strftime("%Y-%m-%d"),
                "open": float(price.open_price) if price.open_price else None,
                "high": float(price.high_price) if price.high_price else None,
                "low": float(price.low_price) if price.low_price else None,
                "close": float(price.close_price) if price.close_price else None,
                "volume": int(price.volume) if price.volume else None
            })
        
        return {
            "symbol": symbol,
            "stock_name": stock.name,
            "data": chart_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    """Get list of all sectors"""
    try:
        sectors = db.query(Stock.sector).filter(
            Stock.sector.isnot(None),
            Stock.is_active == True
        ).distinct().all()
        
        return [sector[0] for sector in sectors if sector[0]]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
