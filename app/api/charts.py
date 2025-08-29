from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.stock import Stock, DailyPrice

router = APIRouter()

@router.get("/stocks/{symbol}/ohlcv")
async def get_ohlcv_data(
    symbol: str,
    days: int = Query(365, ge=1, le=1095),  # Max 3 years
    db: Session = Depends(get_db)
):
    """Get OHLCV data for charting"""
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
