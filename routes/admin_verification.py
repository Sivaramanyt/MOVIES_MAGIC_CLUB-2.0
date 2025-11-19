# routes/admin_verification.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db import get_db
from config import (
    VERIFICATION_DEFAULT_ENABLED,
    VERIFICATION_DEFAULT_FREE_LIMIT,
    VERIFICATION_DEFAULT_VALID_MINUTES,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def _get_settings():
    db = get_db()
    doc = None
    if db is not None:
        doc = await db["settings"].find_one({"_id": "verification"})

    if not doc:
        return {
            "enabled": VERIFICATION_DEFAULT_ENABLED,
            "free_limit": VERIFICATION_DEFAULT_FREE_LIMIT,
            "valid_minutes": VERIFICATION_DEFAULT_VALID_MINUTES,
        }

    return {
        "enabled": bool(doc.get("enabled", VERIFICATION_DEFAULT_ENABLED)),
        "free_limit": int(doc.get("free_limit", VERIFICATION_DEFAULT_FREE_LIMIT)),
        "valid_minutes": int(
            doc.get("valid_minutes", VERIFICATION_DEFAULT_VALID_MINUTES)
        ),
    }


@router.get("/admin/verification", response_class=HTMLResponse)
async def verification_dashboard(request: Request):
    settings = await _get_settings()
    return templates.TemplateResponse(
        "admin_verification.html",
        {
            "request": request,
            "settings": settings,
            "active_tab": "verification",
        },
    )


@router.post("/admin/verification", response_class=HTMLResponse)
async def verification_save(
    request: Request,
    enabled: str = Form("off"),
    free_limit: int = Form(...),
    valid_minutes: int = Form(...),
):
    db = get_db()
    if db is not None:
        await db["settings"].update_one(
            {"_id": "verification"},
            {
                "$set": {
                    "enabled": enabled == "on",
                    "free_limit": int(free_limit),
                    "valid_minutes": int(valid_minutes),
                }
            },
            upsert=True,
        )

    # simple redirect back to page
    return RedirectResponse(url="/admin/verification", status_code=303)
