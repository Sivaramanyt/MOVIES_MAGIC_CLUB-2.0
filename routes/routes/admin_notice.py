# routes/admin_notice.py - Admin notice management

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/notice", response_class=HTMLResponse)
async def admin_notice_page(request: Request):
    """
    Admin page to manage site notice
    """
    # TODO: Add admin authentication check
    
    db = get_db()
    notice = None
    
    if db is not None:
        try:
            notice = await db["site_notice"].find_one({"active": True})
        except Exception as e:
            print(f"❌ Error fetching notice: {e}")
    
    return templates.TemplateResponse(
        "admin_notice.html",
        {
            "request": request,
            "notice": notice,
            "active_tab": "notice"
        }
    )


@router.post("/admin/notice/update")
async def update_notice(
    request: Request,
    message: str = Form(...),
    notice_type: str = Form("info"),
    icon: str = Form("📢"),
    active: bool = Form(False)
):
    """
    Update or create site notice
    """
    db = get_db()
    if db is None:
        return RedirectResponse(url="/admin/notice?error=db", status_code=303)
    
    try:
        # First, deactivate all notices
        await db["site_notice"].update_many(
            {},
            {"$set": {"active": False}}
        )
        
        # Create or update the notice
        notice_data = {
            "message": message,
            "type": notice_type,
            "icon": icon,
            "active": active,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if notice exists
        existing = await db["site_notice"].find_one({})
        
        if existing:
            # Update existing
            await db["site_notice"].update_one(
                {"_id": existing["_id"]},
                {"$set": notice_data}
            )
        else:
            # Create new
            notice_data["created_at"] = datetime.utcnow().isoformat()
            await db["site_notice"].insert_one(notice_data)
        
        return RedirectResponse(url="/admin/notice?success=1", status_code=303)
        
    except Exception as e:
        print(f"❌ Error updating notice: {e}")
        return RedirectResponse(url="/admin/notice?error=1", status_code=303)


@router.post("/admin/notice/disable")
async def disable_notice(request: Request):
    """
    Disable all notices
    """
    db = get_db()
    if db is None:
        return RedirectResponse(url="/admin/notice?error=db", status_code=303)
    
    try:
        await db["site_notice"].update_many(
            {},
            {"$set": {"active": False}}
        )
        return RedirectResponse(url="/admin/notice?success=disabled", status_code=303)
    except Exception as e:
        print(f"❌ Error disabling notice: {e}")
        return RedirectResponse(url="/admin/notice?error=1", status_code=303)
