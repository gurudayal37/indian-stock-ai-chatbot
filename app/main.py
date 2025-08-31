from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from sqlalchemy import text

from app.api.stocks import router as stocks_router
from app.api.charts import router as charts_router

app = FastAPI(title="Indian Stock AI Chatbot", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(stocks_router, prefix="/api")
app.include_router(charts_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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
