from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class StockBase(BaseModel):
    """Base stock schema."""
    name: str = Field(..., description="Company name")
    bse_symbol: Optional[str] = Field(None, description="BSE trading symbol")
    nse_symbol: Optional[str] = Field(None, description="NSE trading symbol")
    isin: Optional[str] = Field(None, description="ISIN code")


class StockCreate(StockBase):
    """Schema for creating a new stock."""
    face_value: Optional[float] = Field(None, description="Face value of the stock")
    industry: Optional[str] = Field(None, description="Industry classification")
    sector: Optional[str] = Field(None, description="Sector classification")
    subsector: Optional[str] = Field(None, description="Subsector classification")


class StockUpdate(BaseModel):
    """Schema for updating stock information."""
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    high_52_week: Optional[float] = None
    low_52_week: Optional[float] = None
    high_1_day: Optional[float] = None
    low_1_day: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    book_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    roce: Optional[float] = None
    roe: Optional[float] = None
    is_active: Optional[bool] = None


class StockResponse(StockBase):
    """Schema for stock response."""
    id: int
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    face_value: Optional[float] = None
    high_52_week: Optional[float] = None
    low_52_week: Optional[float] = None
    high_1_day: Optional[float] = None
    low_1_day: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    book_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    roce: Optional[float] = None
    roe: Optional[float] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    subsector: Optional[str] = None
    is_active: bool
    listing_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DailyPriceBase(BaseModel):
    """Base daily price schema."""
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: Optional[int] = None
    turnover: Optional[float] = None
    vwap: Optional[float] = None
    delivery_quantity: Optional[int] = None
    delivery_percentage: Optional[float] = None


class DailyPriceCreate(DailyPriceBase):
    """Schema for creating daily price data."""
    stock_id: int


class DailyPriceResponse(DailyPriceBase):
    """Schema for daily price response."""
    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuarterlyResultBase(BaseModel):
    """Base quarterly result schema."""
    quarter: str
    year: int
    quarter_number: int
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    ebitda: Optional[float] = None
    operating_profit: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    eps: Optional[float] = None
    expected_eps: Optional[float] = None
    is_consolidated: bool = False


class QuarterlyResultCreate(QuarterlyResultBase):
    """Schema for creating quarterly result."""
    stock_id: int


class QuarterlyResultResponse(QuarterlyResultBase):
    """Schema for quarterly result response."""
    id: int
    stock_id: int
    announcement_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FinancialStatementBase(BaseModel):
    """Base financial statement schema."""
    statement_type: str
    period: str
    year: int
    quarter: Optional[int] = None
    data: str  # JSON string
    is_consolidated: bool = False


class FinancialStatementCreate(FinancialStatementBase):
    """Schema for creating financial statement."""
    stock_id: int


class FinancialStatementResponse(FinancialStatementBase):
    """Schema for financial statement response."""
    id: int
    stock_id: int
    filing_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShareholdingPatternBase(BaseModel):
    """Base shareholding pattern schema."""
    quarter: str
    year: int
    quarter_number: int
    promoter_holding: Optional[float] = None
    fii_holding: Optional[float] = None
    dii_holding: Optional[float] = None
    public_holding: Optional[float] = None
    other_holding: Optional[float] = None
    total_shares: Optional[int] = None


class ShareholdingPatternCreate(ShareholdingPatternBase):
    """Schema for creating shareholding pattern."""
    stock_id: int


class ShareholdingPatternResponse(ShareholdingPatternBase):
    """Schema for shareholding pattern response."""
    id: int
    stock_id: int
    filing_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementBase(BaseModel):
    """Base announcement schema."""
    title: str
    content: Optional[str] = None
    announcement_type: str
    announcement_date: datetime
    is_important: bool = False


class AnnouncementCreate(AnnouncementBase):
    """Schema for creating announcement."""
    stock_id: int


class AnnouncementResponse(AnnouncementBase):
    """Schema for announcement response."""
    id: int
    stock_id: int
    filing_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NewsBase(BaseModel):
    """Base news schema."""
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    published_date: datetime


class NewsCreate(NewsBase):
    """Schema for creating news."""
    stock_id: int


class NewsResponse(NewsBase):
    """Schema for news response."""
    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CreditRatingBase(BaseModel):
    """Base credit rating schema."""
    rating_agency: str
    rating: str
    outlook: Optional[str] = None
    rating_date: datetime


class CreditRatingCreate(CreditRatingBase):
    """Schema for creating credit rating."""
    stock_id: int


class CreditRatingResponse(CreditRatingBase):
    """Schema for credit rating response."""
    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConcallBase(BaseModel):
    """Base concall schema."""
    quarter: str
    year: int
    call_date: datetime
    duration: Optional[int] = None
    transcript_url: Optional[str] = None
    recording_url: Optional[str] = None
    key_points: Optional[str] = None


class ConcallCreate(ConcallBase):
    """Schema for creating concall."""
    stock_id: int


class ConcallResponse(ConcallBase):
    """Schema for concall response."""
    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockDetailResponse(StockResponse):
    """Detailed stock response with related data."""
    daily_prices: List[DailyPriceResponse] = []
    quarterly_results: List[QuarterlyResultResponse] = []
    financial_statements: List[FinancialStatementResponse] = []
    shareholding_patterns: List[ShareholdingPatternResponse] = []
    announcements: List[AnnouncementResponse] = []
    news: List[NewsResponse] = []
    credit_ratings: List[CreditRatingResponse] = []
    concalls: List[ConcallResponse] = []


class StockListResponse(BaseModel):
    """Response for listing stocks."""
    stocks: List[StockResponse]
    total: int
    page: int
    size: int
    pages: int
