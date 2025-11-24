# routes/notice.py - Notice API routes

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from db import get_db
from datetime import datetime

router = APIRouter()

@router.get("/api/notice")
async def get_active_notice(request: Request):
    """
    Get active notice for frontend display
    """
    db = get_db()
    if db is None:
        return JSONResponse({"active": False})
    
    try:
        # Get notice from database
        notice = await db["site_notice"].find_one({"active": True})
        
        if not notice:
            return JSONResponse({"active": False})
        
        return JSONResponse({
            "active": True,
            "message": notice.get("message", ""),
            "type": notice.get("type", "info"),  # info, warning, maintenance
            "icon": notice.get("icon", "📢"),
            "created_at": notice.get("created_at", "")
        })
        
    except Exception as e:
        print(f"❌ Error fetching notice: {e}")
        return JSONResponse({"active": False})
