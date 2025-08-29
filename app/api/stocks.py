from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

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
        
        results = db.query(QuarterlyResult).filter(
            QuarterlyResult.stock_id == stock.id
        ).order_by(
            QuarterlyResult.year.desc(),
            QuarterlyResult.quarter_number.desc()
        ).limit(quarters).all()
        
        return results
        
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
