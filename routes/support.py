# routes/support.py

from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from config import BOT_TOKEN
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Get bot username from token (first part before colon)
BOT_USERNAME = os.getenv("BOT_USERNAME", "YOUR_BOT_USERNAME")


@router.get("/support", response_class=HTMLResponse)
async def support_page(request: Request):
    """
    Support page (optional - can be modal only)
    """
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "bot_username": BOT_USERNAME,
        },
    )


@router.post("/support/message")
async def submit_support_message(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    telegram_username: str = Form(""),
    message: str = Form(...),
):
    """
    Save support message to database and optionally notify via Telegram
    """
    db = get_db()
    if db is None:
        return JSONResponse(
            {"success": False, "error": "Database not connected"},
            status_code=500,
        )
    
    # Save message to database
    support_doc = {
        "name": name.strip(),
        "email": email.strip() or None,
        "telegram_username": telegram_username.strip() or None,
        "message": message.strip(),
        "timestamp": datetime.utcnow(),
        "status": "pending",  # pending, replied, closed
        "ip_address": request.client.host,
    }
    
    result = await db["support_messages"].insert_one(support_doc)
    
    # Optional: Send notification to admin via Telegram
    # You can implement this later using Pyrogram to send message to your admin chat
    
    return JSONResponse({
        "success": True,
        "message": "Your message has been sent successfully! We'll get back to you soon.",
    })


@router.get("/support/messages", response_class=HTMLResponse)
async def admin_support_messages(request: Request):
    """
    Admin page to view all support messages
    """
    from routes.admin_auth import is_admin
    
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    
    db = get_db()
    messages_list = []
    
    if db is not None:
        cursor = db["support_messages"].find().sort("timestamp", -1)
        messages_list = await cursor.to_list(length=100)
        
        # Convert ObjectId to string for template
        for msg in messages_list:
            msg["id"] = str(msg["_id"])
    
    return templates.TemplateResponse(
        "admin_support_messages.html",
        {
            "request": request,
            "messages": messages_list,
        },
    )
