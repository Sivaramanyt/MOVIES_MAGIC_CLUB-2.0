# routes/admin_verification.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from .admin_auth import is_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/verification", response_class=HTMLResponse)
async def admin_verification_settings(request: Request):
    """
    Show verification settings page with defaults if no settings exist
    """
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    
    db = get_db()
    
    # ⭐ FIX: Always provide settings, use defaults if needed
    if db is None:
        # Database not connected - use default settings
        settings = {
            "enabled": False,
            "free_limit": 3,
            "message": "Database not connected. Using default settings."
        }
    else:
        # Try to get settings from database
        settings_doc = await db["settings"].find_one({"_id": "verification"})
        
        if settings_doc is None:
            # No settings exist yet - create default
            settings = {
                "_id": "verification",
                "enabled": False,
                "free_limit": 3,
                "message": "Settings created with defaults."
            }
            # Save defaults to database
            await db["settings"].insert_one(settings)
        else:
            # Use existing settings
            settings = settings_doc
    
    # ⭐ FIX: Always pass settings to template
    return templates.TemplateResponse(
        "admin_verification.html",
        {
            "request": request,
            "settings": settings,  # Always defined now!
        },
    )


@router.post("/admin/verification", response_class=HTMLResponse)
async def admin_update_verification(
    request: Request,
    enabled: bool = Form(False),
    free_limit: int = Form(3),
):
    """
    Update verification settings
    """
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    
    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/verification?message=Database+not+connected",
            status_code=303,
        )
    
    # ⭐ FIX: Use upsert=True to create if doesn't exist
    await db["settings"].update_one(
        {"_id": "verification"},
        {
            "$set": {
                "enabled": enabled,
                "free_limit": max(1, min(10, free_limit)),  # Keep between 1-10
            }
        },
        upsert=True,  # Creates document if it doesn't exist
    )
    
    return RedirectResponse(
        "/admin/verification?message=Settings+saved+successfully+%E2%9C%85",
        status_code=303,
    )
    
