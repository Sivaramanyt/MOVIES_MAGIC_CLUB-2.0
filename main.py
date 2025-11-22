import os
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from pyrogram import Client
from pyrogram.errors import BadRequest

from motor.motor_asyncio import AsyncIOMotorClient

from db import connect_to_mongo, close_mongo_connection

from routes.movies import router as movies_router
from routes.web import router as web_router
from routes.series_web import router as series_router
from routes.admin_auth import router as admin_auth_router
from routes.admin_movies import router as admin_movies_router
from routes.admin_series import router as admin_series_router
from routes.admin_series_seasons import router as admin_series_seasons_router
from routes.verify import router as verify_router
from routes.admin_episodes import router as admin_episodes_router
from routes.admin_verification import router as admin_verification_router

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    CHANNEL_ID,
    MONGO_URI,
    MONGO_DB,
)

# ---------------------------------------------------------------------
# FastAPI app setup
# ---------------------------------------------------------------------

app = FastAPI(title="Movies Magic Club 2.0")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session middleware (for admin panel, etc.)
SESSION_SECRET = os.getenv("SESSION_SECRET", "super-secret-session-key")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# ---------------------------------------------------------------------
# Telegram bot client (Pyrogram)
# ---------------------------------------------------------------------

bot = Client(
    "movie_webapp_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,  # no session file on disk, good for Koyeb
)

# ---------------------------------------------------------------------
# Startup & shutdown events
# ---------------------------------------------------------------------


@app.on_event("startup")
async def on_startup():
    # Connect to MongoDB and save client on app.state
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    app.state.db_client = mongo_client
    app.state.db = mongo_client[MONGO_DB]
    await connect_to_mongo(app)

    # Start Telegram bot
    await bot.start()
    print("🚀 FastAPI app and bot startup complete!")


@app.on_event("shutdown")
async def on_shutdown():
    # Close Mongo connection
    await close_mongo_connection(app)

    # Stop Telegram bot
    await bot.stop()


# ---------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------

app.include_router(web_router)
app.include_router(movies_router)
app.include_router(series_router)
app.include_router(admin_auth_router)
app.include_router(admin_movies_router)
app.include_router(admin_series_router)
app.include_router(admin_series_seasons_router)
app.include_router(verify_router)
app.include_router(admin_episodes_router)
app.include_router(admin_verification_router)

# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------


@app.get("/status")
async def status():
    return {"status": "ok"}


# ---------------------------------------------------------------------
# Poster upload API (used by your web admin)
# ---------------------------------------------------------------------


@app.post("/api/poster/upload")
async def upload_poster(image: UploadFile = File(...)):
    """
    1. Save uploaded image to temp file.
    2. Send to Telegram channel as photo.
    3. Return file_id and direct file_url from Telegram.
    """
    try:
        # Step 1: Save to temp file
        suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await image.read())
            tmp_path = tmp.name

        print(f"[DEBUG] Uploading image to Telegram: {tmp_path}")

        # Step 2: Send photo to channel (CHANNEL_ID is already int)
        tg_msg = await bot.send_photo(
            CHANNEL_ID,
            tmp_path,
            caption="New movie poster uploaded",
        )

        # Get highest resolution photo file_id
        photo = tg_msg.photo
        if isinstance(photo, list):
            file_id = photo[-1].file_id
        else:
            file_id = photo.file_id

        # Step 3: Resolve file path and build URL
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        # Clean up local temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return JSONResponse(
            {
                "success": True,
                "file_id": file_id,
                "file_url": file_url,
            }
        )
    except BadRequest as e:
        # This is where PEER_ID_INVALID comes from
        print(f"[ERROR] Poster upload failed: {e.MESSAGE}")
        return JSONResponse(
            {"success": False, "error": e.MESSAGE},
            status_code=200,
        )
    except Exception as e:
        print(f"[ERROR] Poster upload unexpected error: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=200,
        )


# ---------------------------------------------------------------------
# Debug endpoint to inspect CHANNEL_ID from Telegram's perspective
# ---------------------------------------------------------------------


@app.get("/debug/channel")
async def debug_channel():
    """
    Helps debug PEER_ID_INVALID.

    - If ok == True: bot can see the channel (id/title/type shown).
    - If ok == False and message == 'PEER_ID_INVALID': bot doesn't know this channel
      (wrong bot token, bot not added as admin, or wrong CHANNEL_ID).
    """
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        return {
            "ok": True,
            "id": chat.id,
            "title": chat.title,
            "type": str(chat.type),
        }
    except BadRequest as e:
        return {
            "ok": False,
            "error_type": "BadRequest",
            "message": e.MESSAGE,
        }
    except Exception as e:
        return {
            "ok": False,
            "error_type": type(e).__name__,
            "message": str(e),
    }
          
