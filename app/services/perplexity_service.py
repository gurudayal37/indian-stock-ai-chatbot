import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.stock import Stock, DailyPrice, QuarterlyResult, FinancialStatement
from app.schemas.chat import ChatRequest, ChatResponse, StockAnalysisResponse

logger = logging.getLogger(__name__)


class PerplexityService:
    """Service for Perplexity-powered stock market analysis and chat."""
    
    def __init__(self):
        """Initialize the Perplexity service."""
        if not settings.perplexity_api_key:
            logger.warning("Perplexity API key not found. LLM features will be limited.")
        
        self.api_key = settings.perplexity_api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
    
    def _get_stock_context(self, db: Session, stock_symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stock context for LLM analysis."""
        try:
            # Find stock by symbol (try both BSE and NSE)
            stock = db.query(Stock).filter(
                (Stock.bse_symbol == stock_symbol) | 
                (Stock.nse_symbol == stock_symbol)
            ).first()
            
            if not stock:
                return None
            
            # Get latest daily price
            latest_price = db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock.id
            ).order_by(DailyPrice.date.desc()).first()
            
            # Get latest quarterly results
            latest_quarterly = db.query(QuarterlyResult).filter(
                QuarterlyResult.stock_id == stock.id
            ).order_by(DailyPrice.date.desc()).first()
            
            # Get latest financial statement
            latest_financial = db.query(FinancialStatement).filter(
                FinancialStatement.stock_id == stock.id
            ).order_by(FinancialStatement.year.desc()).first()
            
            context = {
                "stock_info": {
                    "name": stock.name,
                    "bse_symbol": stock.bse_symbol,
                    "nse_symbol": stock.nse_symbol,
                    "industry": stock.industry,
                    "sector": stock.sector,
                    "subsector": stock.subsector,
                    "current_price": stock.current_price,
                    "market_cap": stock.market_cap,
                    "face_value": stock.face_value
                },
                "technical_data": {
                    "high_52_week": stock.high_52_week,
                    "low_52_week": stock.low_52_week,
                    "pe_ratio": stock.pe_ratio,
                    "pb_ratio": stock.pb_ratio,
                    "book_value": stock.book_value,
                    "dividend_yield": stock.dividend_yield,
                    "roce": stock.roce,
                    "roe": stock.roe
                }
            }
            
            if latest_price:
                context["price_data"] = {
                    "date": latest_price.date.isoformat(),
                    "open": latest_price.open_price,
                    "high": latest_price.high_price,
                    "low": latest_price.low_price,
                    "close": latest_price.close_price,
                    "volume": latest_price.volume,
                    "turnover": latest_price.turnover
                }
            
            if latest_quarterly:
                context["financial_data"] = {
                    "quarter": latest_quarterly.quarter,
                    "year": latest_quarterly.year,
                    "revenue": latest_quarterly.revenue,
                    "net_profit": latest_quarterly.net_profit,
                    "ebitda": latest_quarterly.ebitda,
                    "operating_profit": latest_quarterly.operating_profit,
                    "eps": latest_quarterly.eps,
                    "is_consolidated": latest_quarterly.is_consolidated
                }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting stock context: {e}")
            return None
    
    def _create_system_prompt(self, stock_context: Optional[Dict] = None) -> str:
        """Create system prompt for the LLM."""
        base_prompt = """You are an expert financial analyst specializing in Indian stock markets. 
        You have access to comprehensive stock market data and can provide detailed analysis, 
        insights, and recommendations.
        
        Your capabilities include:
        - Technical analysis of stock prices and trends
        - Fundamental analysis using financial ratios and statements
        - Sector and industry analysis
        - Risk assessment and investment recommendations
        - News sentiment analysis and market insights
        
        Always provide accurate, well-reasoned responses based on the data available.
        If you don't have enough information to answer a question confidently, say so.
        Include relevant metrics and data points in your responses when available."""
        
        if stock_context:
            base_prompt += f"\n\nCurrent stock context:\n{json.dumps(stock_context, indent=2)}"
        
        return base_prompt
    
    def _call_perplexity_api(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Call Perplexity API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}")
            raise
    
    def chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        """Process a chat request and return AI response."""
        try:
            # Get stock context if symbol is provided
            stock_context = None
            if request.stock_symbol:
                stock_context = self._get_stock_context(db, request.stock_symbol)
            
            # Create system prompt
            system_prompt = self._create_system_prompt(stock_context)
            
            # Prepare user message
            user_message = request.message
            if stock_context and request.include_context:
                user_message += f"\n\nPlease analyze the stock {request.stock_symbol} using the available data."
            
            if not self.api_key:
                return ChatResponse(
                    message="LLM service is not configured. Please set up Perplexity API key.",
                    stock_context=stock_context,
                    sources=[],
                    confidence_score=0.0
                )
            
            # Call Perplexity API
            response = self._call_perplexity_api([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ], request.max_tokens or settings.llm_max_tokens)
            
            # Determine confidence score based on response quality
            confidence_score = self._calculate_confidence_score(response, stock_context)
            
            # Identify sources used
            sources = self._identify_sources(stock_context)
            
            return ChatResponse(
                message=response,
                stock_context=stock_context,
                sources=sources,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error in chat service: {e}")
            return ChatResponse(
                message=f"Sorry, I encountered an error while processing your request: {str(e)}",
                stock_context=None,
                sources=[],
                confidence_score=0.0
            )
    
    def analyze_stock(self, db: Session, stock_symbol: str, analysis_type: str = "comprehensive") -> StockAnalysisResponse:
        """Perform comprehensive stock analysis."""
        try:
            # Get stock context
            stock_context = self._get_stock_context(db, stock_symbol)
            if not stock_context:
                return StockAnalysisResponse(
                    stock_symbol=stock_symbol,
                    analysis_type=analysis_type,
                    summary="Stock not found in database",
                    confidence_score=0.0
                )
            
            # Create analysis prompt
            analysis_prompt = f"""
            Please provide a comprehensive {analysis_type} analysis for {stock_symbol} ({stock_context['stock_info']['name']}).
            
            Include:
            1. Technical analysis (price trends, support/resistance levels)
            2. Fundamental analysis (financial ratios, growth prospects)
            3. Risk assessment
            4. Investment recommendations
            5. Key metrics summary
            
            Use the available data to provide specific insights and actionable recommendations.
            """
            
            # Get AI analysis
            analysis = self._call_perplexity_api([
                {"role": "system", "content": self._create_system_prompt(stock_context)},
                {"role": "user", "content": analysis_prompt}
            ], 1500)
            
            # Extract key metrics
            key_metrics = {
                "current_price": stock_context["stock_info"]["current_price"],
                "market_cap": stock_context["stock_info"]["market_cap"],
                "pe_ratio": stock_context["technical_data"]["pe_ratio"],
                "pb_ratio": stock_context["technical_data"]["pb_ratio"],
                "roe": stock_context["technical_data"]["roe"],
                "roce": stock_context["technical_data"]["roce"]
            }
            
            # Generate recommendations based on analysis
            recommendations = self._generate_recommendations(stock_context, analysis)
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(stock_context, analysis)
            
            return StockAnalysisResponse(
                stock_symbol=stock_symbol,
                analysis_type=analysis_type,
                summary=analysis,
                key_metrics=key_metrics,
                recommendations=recommendations,
                risk_factors=risk_factors,
                confidence_score=0.85
            )
            
        except Exception as e:
            logger.error(f"Error in stock analysis: {e}")
            return StockAnalysisResponse(
                stock_symbol=stock_symbol,
                analysis_type=analysis_type,
                summary=f"Analysis failed: {str(e)}",
                confidence_score=0.0
            )
    
    def _calculate_confidence_score(self, response: str, stock_context: Optional[Dict]) -> float:
        """Calculate confidence score for the response."""
        base_score = 0.7
        
        # Increase score if response is detailed
        if len(response) > 200:
            base_score += 0.1
        
        # Increase score if stock context is available
        if stock_context:
            base_score += 0.1
        
        # Increase score if response contains specific metrics
        if any(metric in response.lower() for metric in ["pe ratio", "market cap", "roe", "roce"]):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _identify_sources(self, stock_context: Optional[Dict]) -> List[str]:
        """Identify data sources used in the response."""
        sources = []
        
        if stock_context:
            if "stock_info" in stock_context:
                sources.append("Stock Database")
            if "price_data" in stock_context:
                sources.append("Market Data")
            if "financial_data" in stock_context:
                sources.append("Financial Statements")
        
        return sources
    
    def _generate_recommendations(self, stock_context: Dict, analysis: str) -> List[str]:
        """Generate investment recommendations based on analysis."""
        recommendations = []
        
        # Basic recommendations based on metrics
        if stock_context["technical_data"]["pe_ratio"]:
            pe_ratio = stock_context["technical_data"]["pe_ratio"]
            if pe_ratio < 15:
                recommendations.append("Low PE ratio suggests potential undervaluation")
            elif pe_ratio > 25:
                recommendations.append("High PE ratio indicates premium valuation")
        
        if stock_context["technical_data"]["roe"]:
            roe = stock_context["technical_data"]["roe"]
            if roe > 15:
                recommendations.append("Strong ROE indicates efficient capital utilization")
            elif roe < 10:
                recommendations.append("Low ROE suggests room for operational improvement")
        
        # Add analysis-based recommendations
        if "bullish" in analysis.lower():
            recommendations.append("Technical indicators suggest bullish momentum")
        if "bearish" in analysis.lower():
            recommendations.append("Technical indicators suggest bearish pressure")
        
        return recommendations
    
    def _identify_risk_factors(self, stock_context: Dict, analysis: str) -> List[str]:
        """Identify potential risk factors."""
        risk_factors = []
        
        # Market cap based risks
        if stock_context["stock_info"]["market_cap"] < 10000:  # Less than 1000 Cr
            risk_factors.append("Small cap stock - higher volatility expected")
        
        # PE ratio risks
        if stock_context["technical_data"]["pe_ratio"] > 50:
            risk_factors.append("High PE ratio - potential overvaluation risk")
        
        # Sector specific risks
        if stock_context["stock_info"]["sector"] == "Energy":
            risk_factors.append("Energy sector - sensitive to oil price fluctuations")
        elif stock_context["stock_info"]["sector"] == "Banking":
            risk_factors.append("Banking sector - sensitive to interest rate changes")
        
        return risk_factors
