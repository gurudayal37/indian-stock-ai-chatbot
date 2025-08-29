from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

from app.api.stocks import router as stocks_router
from app.api.charts import router as charts_router

app = FastAPI(title="Stock Analysis Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(stocks_router, prefix="/api")
app.include_router(charts_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with stock list"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stock/{symbol}", response_class=HTMLResponse)
async def stock_detail(request: Request, symbol: str):
    """Individual stock detail page"""
    return templates.TemplateResponse("stock_detail.html", {"request": request, "symbol": symbol})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
