from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db, create_tables
from app.models.stock import Stock, DailyPrice, QuarterlyResult, FinancialStatement
from app.schemas.stock import (
    StockResponse, StockCreate, StockUpdate, StockDetailResponse, StockListResponse,
    DailyPriceResponse, QuarterlyResultResponse, FinancialStatementResponse
)
from app.schemas.chat import (
    ChatRequest, ChatResponse, StockAnalysisRequest, StockAnalysisResponse,
    MarketInsightRequest, MarketInsightResponse, ComparisonRequest, ComparisonResponse
)
from app.services.perplexity_service import PerplexityService
from app.services.data_collector import data_collector

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Indian Stock Market Database & Perplexity AI Chatbot",
    description="A comprehensive database system for Indian stock market data with a Perplexity AI-powered chatbot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Initialize services
llm_service = PerplexityService()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Indian Stock Market Database & LLM Chatbot...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    
    # Setup data collection scheduling
    try:
        data_collector.schedule_data_collection()
        logger.info("Data collection scheduling setup completed")
    except Exception as e:
        logger.error(f"Error setting up data collection: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Indian Stock Market Database & LLM Chatbot",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# Stock Management Endpoints
@app.get("/api/stocks", response_model=StockListResponse)
async def list_stocks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    db: Session = Depends(get_db)
):
    """List all stocks with pagination and filtering."""
    try:
        query = db.query(Stock).filter(Stock.is_active == True)
        
        # Apply filters
        if sector:
            query = query.filter(Stock.sector == sector)
        if industry:
            query = query.filter(Stock.industry == industry)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        stocks = query.offset(skip).limit(limit).all()
        
        # Calculate pagination info
        pages = (total + limit - 1) // limit
        page = (skip // limit) + 1
        
        return StockListResponse(
            stocks=stocks,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing stocks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stocks/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific stock."""
    try:
        # Find stock by symbol (try both BSE and NSE)
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | 
            (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        return stock
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/stocks", response_model=StockResponse)
async def create_stock(
    stock: StockCreate,
    db: Session = Depends(get_db)
):
    """Create a new stock entry."""
    try:
        # Check if stock already exists
        existing_stock = db.query(Stock).filter(
            (Stock.bse_symbol == stock.bse_symbol) |
            (Stock.nse_symbol == stock.nse_symbol) |
            (Stock.isin == stock.isin)
        ).first()
        
        if existing_stock:
            raise HTTPException(status_code=400, detail="Stock already exists")
        
        # Create new stock
        db_stock = Stock(**stock.dict())
        db.add(db_stock)
        db.commit()
        db.refresh(db_stock)
        
        return db_stock
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating stock: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/stocks/{symbol}", response_model=StockResponse)
async def update_stock(
    symbol: str,
    stock_update: StockUpdate,
    db: Session = Depends(get_db)
):
    """Update stock information."""
    try:
        # Find stock by symbol
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | 
            (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Update stock fields
        update_data = stock_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stock, field, value)
        
        stock.updated_at = datetime.now()
        db.commit()
        db.refresh(stock)
        
        return stock
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stock: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# Financial Data Endpoints
@app.get("/api/stocks/{symbol}/daily-prices", response_model=List[DailyPriceResponse])
async def get_daily_prices(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of price data"),
    db: Session = Depends(get_db)
):
    """Get daily price data for a stock."""
    try:
        # Find stock by symbol
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | 
            (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Get daily prices
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.id
        ).order_by(DailyPrice.date.desc()).limit(days).all()
        
        return prices
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily prices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stocks/{symbol}/quarterly-results", response_model=List[QuarterlyResultResponse])
async def get_quarterly_results(
    symbol: str,
    quarters: int = Query(8, ge=1, le=20, description="Number of quarters to return"),
    db: Session = Depends(get_db)
):
    """Get quarterly results for a stock."""
    try:
        # Find stock by symbol
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | 
            (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Get quarterly results
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
        logger.error(f"Error getting quarterly results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stocks/{symbol}/financial-statements", response_model=List[FinancialStatementResponse])
async def get_financial_statements(
    symbol: str,
    statement_type: Optional[str] = Query(None, description="Filter by statement type"),
    db: Session = Depends(get_db)
):
    """Get financial statements for a stock."""
    try:
        # Find stock by symbol
        stock = db.query(Stock).filter(
            (Stock.bse_symbol == symbol) | 
            (Stock.nse_symbol == symbol)
        ).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Build query
        query = db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock.id
        )
        
        if statement_type:
            query = query.filter(FinancialStatement.statement_type == statement_type)
        
        # Get financial statements
        statements = query.order_by(
            FinancialStatement.year.desc(),
            FinancialStatement.quarter.desc() if FinancialStatement.quarter else FinancialStatement.year.desc()
        ).all()
        
        return statements
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial statements: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# LLM Chatbot Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_llm(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Chat with the LLM about stocks."""
    try:
        response = llm_service.chat(db, request)
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/analyze-stock", response_model=StockAnalysisResponse)
async def analyze_stock(
    request: StockAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Get comprehensive stock analysis from LLM."""
    try:
        response = llm_service.analyze_stock(
            db, 
            request.stock_symbol, 
            request.analysis_type
        )
        return response
        
    except Exception as e:
        logger.error(f"Error in stock analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Data Collection Endpoints
@app.post("/api/collect-data")
async def trigger_data_collection(
    db: Session = Depends(get_db)
):
    """Trigger manual data collection."""
    try:
        results = data_collector.collect_all_data(db)
        return {
            "message": "Data collection completed",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in data collection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    """Get list of all sectors."""
    try:
        sectors = db.query(Stock.sector).filter(
            Stock.sector.isnot(None),
            Stock.is_active == True
        ).distinct().all()
        
        return [sector[0] for sector in sectors if sector[0]]
        
    except Exception as e:
        logger.error(f"Error getting sectors: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/industries")
async def get_industries(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    db: Session = Depends(get_db)
):
    """Get list of industries, optionally filtered by sector."""
    try:
        query = db.query(Stock.industry).filter(
            Stock.industry.isnot(None),
            Stock.is_active == True
        )
        
        if sector:
            query = query.filter(Stock.sector == sector)
        
        industries = query.distinct().all()
        return [industry[0] for industry in industries if industry[0]]
        
    except Exception as e:
        logger.error(f"Error getting industries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
