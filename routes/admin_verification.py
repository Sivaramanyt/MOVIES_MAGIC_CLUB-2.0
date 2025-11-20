# routes/admin_verification.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from config import (
    VERIFICATION_DEFAULT_ENABLED,
    VERIFICATION_DEFAULT_FREE_LIMIT,
    VERIFICATION_DEFAULT_VALID_MINUTES,
    SHORTLINK_API,  # Default fallback
    SHORTLINK_URL,  # Default fallback
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/verification", response_class=HTMLResponse)
async def admin_verification_settings(request: Request):
    """
    Admin page for verification + shortlink settings.
    """
    db = get_db()
    message = request.query_params.get("message", "")
    
    if db is None:
        return templates.TemplateResponse(
            "admin_verification.html",
            {
                "request": request,
                "message": "Database not connected",
                "enabled": VERIFICATION_DEFAULT_ENABLED,
                "free_limit": VERIFICATION_DEFAULT_FREE_LIMIT,
                "valid_minutes": VERIFICATION_DEFAULT_VALID_MINUTES,
                "shortlink_api": SHORTLINK_API or "",
                "shortlink_url": SHORTLINK_URL or "",
            },
        )
    
    # Read verification settings
    settings = await db["settings"].find_one({"_id": "verification"})
    
    if not settings:
        settings = {
            "enabled": VERIFICATION_DEFAULT_ENABLED,
            "free_limit": VERIFICATION_DEFAULT_FREE_LIMIT,
            "valid_minutes": VERIFICATION_DEFAULT_VALID_MINUTES,
            "shortlink_api": SHORTLINK_API or "",
            "shortlink_url": SHORTLINK_URL or "",
        }
    
    return templates.TemplateResponse(
        "admin_verification.html",
        {
            "request": request,
            "message": message,
            "enabled": settings.get("enabled", VERIFICATION_DEFAULT_ENABLED),
            "free_limit": settings.get("free_limit", VERIFICATION_DEFAULT_FREE_LIMIT),
            "valid_minutes": settings.get("valid_minutes", VERIFICATION_DEFAULT_VALID_MINUTES),
            "shortlink_api": settings.get("shortlink_api", SHORTLINK_API or ""),
            "shortlink_url": settings.get("shortlink_url", SHORTLINK_URL or ""),
        },
    )


@router.post("/admin/verification", response_class=HTMLResponse)
async def admin_verification_update(
    request: Request,
    enabled: str = Form("off"),
    free_limit: int = Form(3),
    valid_minutes: int = Form(1440),
    shortlink_api: str = Form(""),
    shortlink_url: str = Form(""),
):
    """
    Update verification + shortlink settings.
    """
    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/verification?message=Database+not+connected",
            status_code=303,
        )
    
    enabled_bool = (enabled == "on")
    
    # Save all settings including shortlink
    await db["settings"].update_one(
        {"_id": "verification"},
        {
            "$set": {
                "enabled": enabled_bool,
                "free_limit": free_limit,
                "valid_minutes": valid_minutes,
                "shortlink_api": shortlink_api.strip(),
                "shortlink_url": shortlink_url.strip(),
            }
        },
        upsert=True,
    )
    
    return RedirectResponse(
        "/admin/verification?message=Settings+updated+successfully",
        status_code=303,
    )
        
