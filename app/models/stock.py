from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime


class Stock(Base):
    """Stock model representing a company's basic information."""
    
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    isin = Column(String(20), unique=True, index=True)
    bse_symbol = Column(String(20), unique=True, index=True)
    nse_symbol = Column(String(20), unique=True, index=True)
    current_price = Column(Float)
    market_cap = Column(BigInteger)
    face_value = Column(Float, default=10.0)
    high_52_week = Column(Float)
    low_52_week = Column(Float)
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    book_value = Column(Float)
    dividend_yield = Column(Float)
    roce = Column(Float)
    roe = Column(Float)
    industry = Column(String(100))
    sector = Column(String(100))
    subsector = Column(String(100))
    subsector1 = Column(String(100))  # Added for detailed sector hierarchy
    subsector2 = Column(String(100))  # Added for detailed sector hierarchy
    subsector3 = Column(String(100))  # Added for detailed sector hierarchy
    long_business_summary = Column(Text)  # Long business description from Yahoo Finance
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)  # Last time data was synced from external sources
    
    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="stock", cascade="all, delete-orphan")
    quarterly_results = relationship("QuarterlyResult", back_populates="stock", cascade="all, delete-orphan")
    financial_statements = relationship("FinancialStatement", back_populates="stock", cascade="all, delete-orphan")
    shareholding_patterns = relationship("ShareholdingPattern", back_populates="stock", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="stock", cascade="all, delete-orphan")
    news = relationship("News", back_populates="stock", cascade="all, delete-orphan")
    credit_ratings = relationship("CreditRating", back_populates="stock", cascade="all, delete-orphan")
    concalls = relationship("Concall", back_populates="stock", cascade="all, delete-orphan")
    sync_trackers = relationship("SyncTracker", back_populates="stock", cascade="all, delete-orphan")


class DailyPrice(Base):
    """Daily OHLC price data for stocks."""
    __tablename__ = "daily_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer)
    turnover = Column(Float)
    
    # Additional metrics
    vwap = Column(Float)  # Volume Weighted Average Price
    delivery_quantity = Column(Integer)
    delivery_percentage = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="daily_prices")


class QuarterlyResult(Base):
    """Quarterly financial results (consolidated and standalone)."""
    __tablename__ = "quarterly_results"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    quarter = Column(String(10), nullable=False)  # e.g., "Q1 2024"
    year = Column(Integer, nullable=False)
    quarter_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    
    # Financial metrics (existing)
    revenue = Column(Float)
    net_profit = Column(Float)
    ebitda = Column(Float)
    operating_profit = Column(Float)
    
    # BSE-specific financial metrics (new)
    other_income = Column(Float)  # Other Income
    total_income = Column(Float)  # Total Income
    expenditure = Column(Float)   # Total Expenditure
    interest = Column(Float)      # Interest Expense
    pbdt = Column(Float)          # Profit Before Depreciation and Tax
    depreciation = Column(Float)  # Depreciation & Amortization
    pbt = Column(Float)           # Profit Before Tax
    tax = Column(Float)           # Tax Expense
    equity = Column(Float)        # Equity Share Capital
    ceps = Column(Float)          # Cash Earnings Per Share
    
    # Ratios (existing + new)
    operating_margin = Column(Float)
    net_margin = Column(Float)
    eps = Column(Float)  # Earnings Per Share
    opm_percent = Column(Float)  # Operating Profit Margin %
    npm_percent = Column(Float)  # Net Profit Margin %
    tax_percent = Column(Float)  # Tax as percentage of PBT
    
    # Type (consolidated or standalone)
    is_consolidated = Column(Boolean, default=False)
    
    # Metadata (existing + new)
    announcement_date = Column(DateTime)
    filing_date = Column(DateTime)  # Filing date
    quarterly_result_link = Column(Text)  # Link to BSE quarterly results
    source = Column(String(20), default='BSE')  # Data source: BSE, Yahoo Finance, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="quarterly_results")


class FinancialStatement(Base):
    """Financial statements (P&L, Balance Sheet, Cash Flow)."""
    __tablename__ = "financial_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    statement_type = Column(String(50), nullable=False)  # P&L, Balance Sheet, Cash Flow
    period = Column(String(20), nullable=False)  # Annual, Quarterly
    year = Column(Integer, nullable=False)
    quarter = Column(Integer)  # 1-4 for quarterly, null for annual
    
    # Statement data (stored as JSON for flexibility)
    data = Column(Text)  # JSON string containing statement data
    
    # Type (consolidated or standalone)
    is_consolidated = Column(Boolean, default=False)
    
    # Metadata
    filing_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="financial_statements")


class ShareholdingPattern(Base):
    """Shareholding pattern data."""
    __tablename__ = "shareholding_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    quarter = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    quarter_number = Column(Integer, nullable=False)
    
    # Shareholding data
    promoter_holding = Column(Float)
    fii_holding = Column(Float)  # Foreign Institutional Investors
    dii_holding = Column(Float)  # Domestic Institutional Investors
    public_holding = Column(Float)
    other_holding = Column(Float)
    
    # Total shares
    total_shares = Column(Integer)
    
    # Metadata
    filing_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="shareholding_patterns")


class Announcement(Base):
    """Company announcements and corporate actions."""
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    announcement_type = Column(String(100), index=True)  # Board Meeting, Dividend, etc.
    
    # Metadata
    announcement_date = Column(DateTime, nullable=False)
    filing_date = Column(DateTime)
    is_important = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="announcements")


class News(Base):
    """Stock-related news articles."""
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source = Column(String(100))
    url = Column(String(500))
    
    # Sentiment analysis
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(20))  # Positive, Negative, Neutral
    
    # Metadata
    published_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="news")


class CreditRating(Base):
    """Credit ratings for companies."""
    __tablename__ = "credit_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    rating_agency = Column(String(100), nullable=False)
    rating = Column(String(20), nullable=False)
    outlook = Column(String(20))  # Stable, Positive, Negative
    
    # Metadata
    rating_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="credit_ratings")


class Concall(Base):
    """Earnings call transcripts and recordings."""
    __tablename__ = "concalls"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    quarter = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    
    # Call details
    call_date = Column(DateTime, nullable=False)
    duration = Column(Integer)  # in minutes
    transcript_url = Column(String(500))
    recording_url = Column(String(500))
    
    # Key highlights
    key_points = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    stock = relationship("Stock", back_populates="concalls")


class SyncTracker(Base):
    __tablename__ = "sync_tracker"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    data_type = Column(String(50), nullable=False)  # 'ohlcv', 'news', 'financials', 'earnings', 'events'
    last_sync_time = Column(DateTime, default=datetime.utcnow)
    last_data_date = Column(DateTime)  # Last date of data we have
    records_count = Column(Integer, default=0)  # Number of records synced
    sync_status = Column(String(20), default='success')  # 'success', 'failed', 'partial'
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (UniqueConstraint('stock_id', 'data_type', name='uq_stock_data_type'),)
    
    # Relationship
    stock = relationship("Stock", back_populates="sync_trackers")
