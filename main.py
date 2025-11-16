import os
import asyncio

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from pyrogram import Client, filters, idle

# ---------- CONFIG ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ Please set API_ID, API_HASH, BOT_TOKEN as env variables")
# ----------------------------

app = FastAPI()


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
        "This is your new Movie WebApp bot skeleton.\n"
        "Right now only /start works.\n"
        "Next steps: add movie website, web app, shortlink verification, admin dashboard. 🚀"
    )
    await message.reply_text(text)
# ----------------------------


# ---------- FASTAPI ROUTES ----------
@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Bot + FastAPI is running ✅"


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "OK"
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
    # run bot in background task
    asyncio.create_task(run_bot())
    print("🚀 FastAPI app startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    print("🔻 FastAPI app shutting down")
# ---------------------------------------------


# For local testing (optional – Koyeb will use `uvicorn main:app`)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
