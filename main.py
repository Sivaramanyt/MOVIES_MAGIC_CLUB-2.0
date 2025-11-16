import os
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from pyrogram import Client, filters, idle

from db import connect_to_mongo, close_mongo_connection, get_db
from routes.movies import router as movies_router
from config import API_ID, API_HASH, BOT_TOKEN  # from config.py


app = FastAPI()

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Include movies API router
app.include_router(movies_router)


# ---------- PYROGRAM BOT ----------
bot = Client(
    "movie_webapp_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    text = (
        "👋 Hi!\n\n"
        "This is your new Movies Magic Club bot skeleton.\n"
        "Right now only /start works.\n"
        "Next steps: add MongoDB movies, website UI, web app, verification, admin dashboard. 🚀"
    )
    await message.reply_text(text)

# ----------------------------


# ---------- FASTAPI ROUTES ----------

# Home page – dashboard
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # TODO: later pass real movie lists from MongoDB
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


# Movie detail page
@app.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: str):
    # TODO: later fetch from MongoDB using movie_id
    movie = {
        "id": movie_id,
        "title": "Sample Movie Title",
        "year": 2024,
        "language": "Tamil",
        "quality": "HD",
        "category": "Action",
        "is_multi_dubbed": True,
        "duration": "2h 20m",
        "description": "",
        "audio": "Tamil, Telugu, Hindi",
        "subtitles": "English",
        "size": "2.1 GB",
        "views": "12.4K",
    }
    return templates.TemplateResponse(
        "movie_detail.html",
        {"request": request, "movie": movie},
    )


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "OK"


@app.get("/debug/movies-count", response_class=PlainTextResponse)
async def movies_count():
    db = get_db()
    if not db:
        return "MongoDB not connected"
    count = await db["movies"].count_documents({})
    return f"Movies in DB: {count}"

# ------------------------------------


# ---------- START BOT IN BACKGROUND ----------
async def run_bot():
    await bot.start()
    print("✅ Pyrogram bot started")
    await idle()
    await bot.stop()
    print("🛑 Pyrogram bot stopped")


@app.on_event("startup")
async def on_startup():
    # Connect to MongoDB
    await connect_to_mongo()

    # Run bot in background
    asyncio.create_task(run_bot())
    print("🚀 FastAPI app startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    await close_mongo_connection()
    print("🔻 FastAPI app shutting down")
# ---------------------------------------------


# For local testing only; Koyeb uses `uvicorn main:app ...`
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
    
