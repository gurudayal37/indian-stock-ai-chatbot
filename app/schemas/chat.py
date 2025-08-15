from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Schema for chat messages."""
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str = Field(..., description="User's question about stocks")
    stock_symbol: Optional[str] = Field(None, description="Specific stock symbol to focus on")
    include_context: bool = Field(default=True, description="Include stock context in response")
    max_tokens: Optional[int] = Field(1000, description="Maximum tokens in response")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    message: str = Field(..., description="AI assistant's response")
    stock_context: Optional[dict] = Field(None, description="Relevant stock information")
    sources: List[str] = Field(default=[], description="Data sources used")
    confidence_score: float = Field(..., description="Confidence in the response (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Schema for chat session."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    messages: List[ChatMessage] = Field(default=[], description="Chat history")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="Whether session is active")


class StockAnalysisRequest(BaseModel):
    """Schema for stock analysis request."""
    stock_symbol: str = Field(..., description="Stock symbol to analyze")
    analysis_type: str = Field(..., description="Type of analysis (technical, fundamental, news, etc.)")
    time_period: Optional[str] = Field("1Y", description="Time period for analysis")
    include_comparison: bool = Field(default=False, description="Include peer comparison")


class StockAnalysisResponse(BaseModel):
    """Schema for stock analysis response."""
    stock_symbol: str
    analysis_type: str
    summary: str = Field(..., description="Analysis summary")
    key_metrics: dict = Field(default={}, description="Key financial metrics")
    technical_indicators: Optional[dict] = Field(None, description="Technical analysis")
    fundamental_analysis: Optional[dict] = Field(None, description="Fundamental analysis")
    news_sentiment: Optional[dict] = Field(None, description="News sentiment analysis")
    recommendations: List[str] = Field(default=[], description="Investment recommendations")
    risk_factors: List[str] = Field(default=[], description="Risk factors to consider")
    confidence_score: float = Field(..., description="Confidence in analysis (0-1)")


class MarketInsightRequest(BaseModel):
    """Schema for market insight request."""
    sector: Optional[str] = Field(None, description="Sector to analyze")
    industry: Optional[str] = Field(None, description="Industry to analyze")
    insight_type: str = Field(..., description="Type of insight (trends, performance, etc.)")
    time_period: str = Field("1Y", description="Time period for analysis")


class MarketInsightResponse(BaseModel):
    """Schema for market insight response."""
    sector: Optional[str] = None
    industry: Optional[str] = None
    insight_type: str
    summary: str = Field(..., description="Market insight summary")
    top_performers: List[dict] = Field(default=[], description="Top performing stocks")
    market_trends: dict = Field(default={}, description="Market trends analysis")
    sector_performance: Optional[dict] = Field(None, description="Sector performance metrics")
    investment_opportunities: List[str] = Field(default=[], description="Investment opportunities")
    risks_and_challenges: List[str] = Field(default=[], description="Market risks and challenges")
    confidence_score: float = Field(..., description="Confidence in insight (0-1)")


class ComparisonRequest(BaseModel):
    """Schema for stock comparison request."""
    stock_symbols: List[str] = Field(..., description="List of stock symbols to compare")
    comparison_metrics: List[str] = Field(default=["pe_ratio", "market_cap", "roe"], 
                                        description="Metrics to compare")
    time_period: str = Field("1Y", description="Time period for comparison")


class ComparisonResponse(BaseModel):
    """Schema for stock comparison response."""
    stock_symbols: List[str]
    comparison_metrics: List[str]
    comparison_table: dict = Field(..., description="Comparison data table")
    analysis: str = Field(..., description="Comparative analysis")
    recommendations: List[str] = Field(default=[], description="Comparison-based recommendations")
    risk_assessment: dict = Field(default={}, description="Risk assessment for each stock")
    confidence_score: float = Field(..., description="Confidence in comparison (0-1)")


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""
    session_id: str
    messages: List[ChatMessage]
    total_messages: int
    session_duration: Optional[float] = Field(None, description="Session duration in minutes")
    created_at: datetime
    updated_at: datetime
