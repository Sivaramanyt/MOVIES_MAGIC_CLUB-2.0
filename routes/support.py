from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db import get_db
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# ----------- PAGE ROUTE (optional: support modal page, adjust as needed) -----------
@router.get("/support", response_class=HTMLResponse)
async def support_page(request: Request):
    return templates.TemplateResponse("support.html", {"request": request, "bot_token": BOT_TOKEN})

# ----------- CONTACT/SUPPORT MESSAGE -----------
@router.post("/support/message")
async def submit_support_message(
    request: Request,
    name: str = Form(...),
    email: str = Form(None),
    telegram_username: str = Form(None),
    message: str = Form(...)
):
    db = get_db()
    if db is None:
        return JSONResponse({"success": False, "error": "Database not connected"}, status_code=500)

    support_doc = {
        "name": name,
        "email": email,
        "telegram_username": telegram_username,
        "message": message,
        "timestamp": datetime.utcnow(),
        "ip": request.client.host
    }
    result = await db["support_messages"].insert_one(support_doc)

    # Optional: Notify via Telegram, email, etc.

    return JSONResponse({"success": True, "message": "Message sent", "id": str(result.inserted_id)})

# ----------- LIVE GROUP CHAT: SEND MESSAGE -----------
@router.post("/support/chat/send")
async def send_chat_message(request: Request):
    data = await request.json()
    name = data.get("name", "Anonymous")
    message = data.get("message", "").strip()

    if not message:
        return JSONResponse({"success": False, "error": "Message is empty"}, status_code=400)

    db = get_db()
    if db is None:
        return JSONResponse({"success": False, "error": "Database not connected"}, status_code=500)

    chat_doc = {
        "name": name,
        "message": message,
        "timestamp": datetime.utcnow(),
        "ip": request.client.host
    }
    result = await db["support_chat"].insert_one(chat_doc)
    return JSONResponse({"success": True, "message": "Message sent", "id": str(result.inserted_id)})

# ----------- LIVE GROUP CHAT: FETCH MESSAGES -----------
@router.get("/support/chat/fetch")
async def fetch_chat_messages(request: Request):
    db = get_db()
    if db is None:
        return JSONResponse({"success": False, "error": "Database not connected"}, status_code=500)

    cursor = db["support_chat"].find().sort("timestamp", -1).limit(50)
    messages = []
    async for doc in cursor:
        messages.append({
            "name": doc.get("name", "Anonymous"),
            "message": doc.get("message", ""),
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else ""
        })
    return JSONResponse({"success": True, "messages": messages[::-1]})

# ----------- ADMIN VIEW: SUPPORT MESSAGES -----------
@router.get("/admin/support/messages", response_class=HTMLResponse)
async def admin_support_messages(request: Request):
    db = get_db()
    messages = await db["support_messages"].find().sort("timestamp", -1).to_list(100)
    return templates.TemplateResponse("admin_support_messages.html", {"request": request, "messages": messages})
    
