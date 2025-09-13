from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from sqlalchemy import text

from app.api.stocks import router as stocks_router
from app.api.charts import router as charts_router
from app.api.sync import router as sync_router

app = FastAPI(title="Indian Stock AI Chatbot", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(stocks_router, prefix="/api")
app.include_router(charts_router, prefix="/api")
app.include_router(sync_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/stock/{symbol}", response_class=HTMLResponse)
async def stock_detail(request: Request, symbol: str):
    """Individual stock detail page"""
    return templates.TemplateResponse("stock_detail.html", {"request": request, "symbol": symbol})

@app.get("/all-stocks-list", response_class=HTMLResponse)
async def all_stocks_list(request: Request):
    """All stocks list page with table format"""
    return templates.TemplateResponse("all_stocks_list.html", {"request": request})

@app.get("/all-time-high-breakout-stocks", response_class=HTMLResponse)
async def all_time_high_breakout(request: Request):
    """All Time High Breakout strategy page"""
    return templates.TemplateResponse("all_time_high_breakout.html", {"request": request})

@app.get("/pead-strategy", response_class=HTMLResponse)
async def pead_strategy(request: Request):
    """PEAD strategy page"""
    return templates.TemplateResponse("pead_strategy.html", {"request": request})

@app.get("/momentum-stocks", response_class=HTMLResponse)
async def momentum_stocks(request: Request):
    """Momentum stocks strategy page"""
    return templates.TemplateResponse("momentum_stocks.html", {"request": request})

@app.get("/statistical-arbitrage", response_class=HTMLResponse)
async def statistical_arbitrage(request: Request):
    """Statistical arbitrage strategy page"""
    return templates.TemplateResponse("statistical_arbitrage.html", {"request": request})

@app.get("/news-based-trading", response_class=HTMLResponse)
async def news_based_trading(request: Request):
    """News based trading strategy page"""
    return templates.TemplateResponse("news_based_trading.html", {"request": request})

@app.get("/value-investing", response_class=HTMLResponse)
async def value_investing(request: Request):
    """Value investing strategy page"""
    return templates.TemplateResponse("value_investing.html", {"request": request})

@app.get("/growth-stocks", response_class=HTMLResponse)
async def growth_stocks(request: Request):
    """Growth stocks strategy page"""
    return templates.TemplateResponse("growth_stocks.html", {"request": request})

@app.get("/dividend-stocks", response_class=HTMLResponse)
async def dividend_stocks(request: Request):
    """Dividend stocks strategy page"""
    return templates.TemplateResponse("dividend_stocks.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel for managing sync operations"""
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/test-db")
async def test_database():
    """Test endpoint to check database connectivity and environment variables"""
    try:
        from app.core.database import engine
        from app.core.config import settings
        
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            db_test = "✅ Database connection successful"
        
        # Check environment variables
        env_vars = {
            "ACTIVE_DATABASE": os.getenv("ACTIVE_DATABASE", "NOT SET"),
            "DATABASE_URL": os.getenv("DATABASE_URL", "NOT SET")[:50] + "..." if os.getenv("DATABASE_URL") else "NOT SET",
            "PYTHONPATH": os.getenv("PYTHONPATH", "NOT SET")
        }
        
        return {
            "status": "success",
            "database": db_test,
            "environment_variables": env_vars,
            "settings_active_db": settings.active_database,
            "settings_db_url": str(settings.effective_database_url)[:50] + "..."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "environment_variables": {
                "ACTIVE_DATABASE": os.getenv("ACTIVE_DATABASE", "NOT SET"),
                "DATABASE_URL": os.getenv("DATABASE_URL", "NOT SET")[:50] + "..." if os.getenv("DATABASE_URL") else "NOT SET",
                "PYTHONPATH": os.getenv("PYTHONPATH", "NOT SET")
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
