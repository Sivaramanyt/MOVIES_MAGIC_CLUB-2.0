import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from pyrogram import Client, filters
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
from routes.support import router as support_router
from routes.legal import router as legal_router

from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID, MONGO_URI, MONGO_DB

SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-secret")

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(movies_router)
app.include_router(web_router)
app.include_router(series_router)
app.include_router(admin_auth_router)
app.include_router(admin_movies_router)
app.include_router(admin_series_router)
app.include_router(admin_series_seasons_router)
app.include_router(verify_router)
app.include_router(admin_episodes_router)
app.include_router(admin_verification_router)
app.include_router(support_router)
app.include_router(legal_router)

# === Pyrogram Bot: SINGLE CLIENT (used for both bot and upload) ===

bot = Client(
    "movie_webapp_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

# Mongo client for posters collection
mongo_client = AsyncIOMotorClient(MONGO_URI)
poster_db = mongo_client[MONGO_DB if MONGO_DB else "movies_magic_club"]


@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    text = (
        "👋 Hi!\n\n"
        "Movies Magic Club bot is online.\n"
        "Use the website / web app to browse movies & series. 🎬"
    )
    await message.reply_text(text)


@app.on_event("startup")
async def on_startup():
    # Use original DB helpers (no arguments)
    await connect_to_mongo()
    await bot.start()
    print("🚀 FastAPI app and bot startup complete!")


@app.on_event("shutdown")
async def on_shutdown():
    await close_mongo_connection()
    await bot.stop()
    mongo_client.close()
    print("🔻 FastAPI app and bot shutting down!")


@app.post("/api/poster/upload")
async def upload_poster(
    movie_title: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        # Save upload to temp file
        suffix = os.path.splitext(image.filename or "")[-1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmpfile:
            content = await image.read()
            tmpfile.write(content)
            tmp_path = tmpfile.name

        print(f"[DEBUG] Uploading image to Telegram: {tmp_path}")

        # Use CHANNEL_ID directly (already int from config)
        tg_msg = await bot.send_photo(
            CHANNEL_ID,
            tmp_path,
            caption=f"{movie_title}\n{description}",
        )

        # Get highest-resolution photo file_id
        photo = tg_msg.photo
        if isinstance(photo, list):
            file_id = photo[-1].file_id
        else:
            file_id = photo.file_id

        print(f"[DEBUG] Telegram file_id: {file_id}")

        # Get file path and build public URL
        file_info = await bot.get_file(file_id)
        image_url = (
            f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        )
        print(f"[DEBUG] Telegram image URL: {image_url}")

        # Save movie record in Mongo
        movie = {
            "title": movie_title,
            "description": description,
            "image_url": image_url,
            "file_id": file_id,
        }
        result = await poster_db.movies.insert_one(movie)
        print(f"[DEBUG] Movie inserted with ID: {result.inserted_id}")

        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return JSONResponse(
            {
                "success": True,
                "message": "Poster uploaded and saved!",
                "url": image_url,
            }
        )
    except BadRequest as e:
        # Catch PEER_ID_INVALID here
        print(f"[ERROR] Poster upload failed (BadRequest): {e.MESSAGE}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return JSONResponse(
            {"success": False, "error": e.MESSAGE},
            status_code=200,
        )
    except Exception as e:
        print(f"[ERROR] Poster upload failed: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=200,
        )


@app.get("/debug/channel")
async def debug_channel():
    """
    Debug endpoint for PEER_ID_INVALID.
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


@app.get("/")
async def root():
    return {"message": "Movies Magic Club API is running."}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
