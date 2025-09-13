from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

# Global variable to track sync status
sync_status = {
    "is_running": False,
    "last_run": None,
    "last_success": None,
    "error": None
}

async def run_daily_sync():
    """Background task to run daily sync"""
    global sync_status
    
    try:
        sync_status["is_running"] = True
        sync_status["last_run"] = datetime.now().isoformat()
        sync_status["error"] = None
        
        # Import syncer only when needed
        from scripts.daily_ohlcv_syncer import DailyOHLCVSyncer
        
        # Run the daily syncer
        syncer = DailyOHLCVSyncer()
        result = syncer.sync_all_stocks()
        
        sync_status["last_success"] = datetime.now().isoformat()
        sync_status["is_running"] = False
        
        return result
        
    except Exception as e:
        sync_status["error"] = str(e)
        sync_status["is_running"] = False
        logging.error(f"Daily sync error: {e}")
        raise e

@router.post("/trigger-daily-sync")
async def trigger_daily_sync(background_tasks: BackgroundTasks):
    """Manually trigger daily sync"""
    if sync_status["is_running"]:
        return JSONResponse(
            status_code=400,
            content={"message": "Sync is already running", "status": sync_status}
        )
    
    # Add background task
    background_tasks.add_task(run_daily_sync)
    
    return JSONResponse(
        status_code=200,
        content={"message": "Daily sync started", "status": sync_status}
    )

@router.get("/sync-status")
async def get_sync_status():
    """Get current sync status"""
    return JSONResponse(content={"status": sync_status})

@router.post("/test-sync")
async def test_sync():
    """Test sync with a single stock"""
    try:
        # Import syncer only when needed
        from scripts.daily_ohlcv_syncer import DailyOHLCVSyncer
        
        syncer = DailyOHLCVSyncer()
        # Test with first stock
        stocks = syncer.get_all_stocks()
        if stocks:
            result = syncer.sync_stock_ohlcv(stocks[0])
            return JSONResponse(
                status_code=200,
                content={"message": f"Test sync successful for {stocks[0].name}", "result": result}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"message": "No stocks found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Test sync failed: {str(e)}"}
        )
