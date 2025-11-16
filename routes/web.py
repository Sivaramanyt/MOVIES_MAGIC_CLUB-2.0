# routes/web.py

import os
from datetime import datetime
from typing import List
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from db import get_db

router = APIRouter()

templates = Jinja2Templates(directory="templates")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def is_admin(request: Request) -> bool:
    return request.session.get("is_admin") is True


# ---------- PUBLIC PAGES ----------


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    db = get_db()

    latest_movies = []
    tamil_movies = []
    telugu_movies = []
    hindi_movies = []
    malayalam_movies = []
    kannada_movies = []

    if db is not None:
        movies_col = db["movies"]

        # Latest 5 (hero slider)
        cursor = movies_col.find().sort("_id", -1).limit(5)
        latest_movies = [
            {
                "id": str(doc.get("_id")),
                "title": doc.get("title", "Untitled"),
                "year": doc.get("year"),
                "language": doc.get("language"),
                "quality": doc.get("quality", "HD"),
                "category": doc.get("category"),
                "poster_path": doc.get("poster_path"),
            }
            async for doc in cursor
        ]

        async def fetch_by_language(lang: str, limit: int = 12):
            cur = (
                movies_col.find({"language": lang})
                .sort("_id", -1)
                .limit(limit)
            )
            return [
                {
                    "id": str(d.get("_id")),
                    "title": d.get("title", "Untitled"),
                    "year": d.get("year"),
                    "language": d.get("language"),
                    "quality": d.get("quality", "HD"),
                    "poster_path": d.get("poster_path"),
                }
                async for d in cur
            ]

        tamil_movies = await fetch_by_language("Tamil")
        telugu_movies = await fetch_by_language("Telugu")
        hindi_movies = await fetch_by_language("Hindi")
        malayalam_movies = await fetch_by_language("Malayalam")
        kannada_movies = await fetch_by_language("Kannada")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "latest_movies": latest_movies,
            "tamil_movies": tamil_movies,
            "telugu_movies": telugu_movies,
            "hindi_movies": hindi_movies,
            "malayalam_movies": malayalam_movies,
            "kannada_movies": kannada_movies,
        },
    )


@router.get("/search", response_class=HTMLResponse)
async def search_movies(request: Request, q: str = ""):
    db = get_db()
    movies = []

    if db is not None and q.strip():
        cursor = db["movies"].find(
            {"title": {"$regex": q, "$options": "i"}}
        ).limit(30)

        movies = [
            {
                "id": str(doc.get("_id")),
                "title": doc.get("title", ""),
                "year": doc.get("year"),
                "language": doc.get("language"),
                "quality": doc.get("quality"),
            }
            async for doc in cursor
        ]

    context = {
        "request": request,
        "query": q,
        "movies": movies,
    }
    return templates.TemplateResponse("search.html", context)


@router.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: str):
    db = get_db()
    movie = None

    if db is not None:
        try:
            oid = ObjectId(movie_id)
            movie = await db["movies"].find_one({"_id": oid})
        except Exception:
            movie = None

    if movie:
        languages = movie.get("languages") or []
        audio_text = ", ".join(languages) if languages else movie.get(
            "audio", "Tamil, Telugu, Hindi"
        )

        movie_ctx = {
            "id": str(movie.get("_id")),
            "title": movie.get("title", "Sample Movie Title"),
            "year": movie.get("year", 2024),
            "language": movie.get("language", "Tamil"),
            "quality": movie.get("quality", "HD"),
            "category": movie.get("category", "Action"),
            "is_multi_dubbed": len(languages) > 1,
            "duration": movie.get("duration", "2h 20m"),
            "description": movie.get("description", ""),
            "audio": audio_text,
            "subtitles": movie.get("subtitles", "English"),
            "size": movie.get("size", "2.1 GB"),
            "views": movie.get("views", "12.4K"),
            "poster_path": movie.get("poster_path"),
            "watch_url": movie.get("watch_url", ""),
            "download_url": movie.get("download_url", ""),
        }
    else:
        movie_ctx = {
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
            "poster_path": None,
            "watch_url": "",
            "download_url": "",
        }

    return templates.TemplateResponse(
        "movie_detail.html",
        {"request": request, "movie": movie_ctx},
    )


@router.get("/health", response_class=PlainTextResponse)
async def health():
    return "OK"


@router.get("/debug/movies-count", response_class=PlainTextResponse)
async def movies_count():
    db = get_db()
    if db is None:
        return "MongoDB not connected"
    count = await db["movies"].count_documents({})
    return f"Movies in DB: {count}"


# ---------- ADMIN LOGIN + DASHBOARD ----------


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": ""},
    )


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse("/admin/movies", status_code=303)

    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Invalid password"},
    )


@router.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/admin/movies", response_class=HTMLResponse)
async def admin_dashboard(request: Request, message: str = ""):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return templates.TemplateResponse(
            "admin_movies.html",
            {
                "request": request,
                "message": "MongoDB not connected",
                "total_movies": 0,
                "tamil_count": 0,
                "telugu_count": 0,
                "hindi_count": 0,
                "malayalam_count": 0,
                "kannada_count": 0,
                "movies": [],
            },
        )

    movies_col = db["movies"]

    total_movies = await movies_col.count_documents({})
    tamil_count = await movies_col.count_documents({"language": "Tamil"})
    telugu_count = await movies_col.count_documents({"language": "Telugu"})
    hindi_count = await movies_col.count_documents({"language": "Hindi"})
    malayalam_count = await movies_col.count_documents({"language": "Malayalam"})
    kannada_count = await movies_col.count_documents({"language": "Kannada"})

    cursor = movies_col.find().sort("_id", -1).limit(30)
    movies = [
        {
            "id": str(doc.get("_id")),
            "title": doc.get("title", "Untitled"),
            "year": doc.get("year"),
            "language": doc.get("language"),
            "quality": doc.get("quality", "HD"),
        }
        async for doc in cursor
    ]

    return templates.TemplateResponse(
        "admin_movies.html",
        {
            "request": request,
            "message": message,
            "total_movies": total_movies,
            "tamil_count": tamil_count,
            "telugu_count": telugu_count,
            "hindi_count": hindi_count,
            "malayalam_count": malayalam_count,
            "kannada_count": kannada_count,
            "movies": movies,
        },
    )


@router.post("/admin/movies", response_class=HTMLResponse)
async def admin_create_movie(
    request: Request,
    title: str = Form(...),
    year: str = Form(""),
    language: str = Form(...),
    quality: str = Form("HD"),
    category: str = Form(""),
    watch_url: str = Form(""),
    download_url: str = Form(""),
    languages: List[str] = Form(default=[]),
    description: str = Form(""),
    poster: UploadFile = File(None),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/movies?message=MongoDB+not+connected",
            status_code=303,
        )

    poster_path = None
    if poster and poster.filename:
        poster_dir = os.path.join("static", "posters")
        os.makedirs(poster_dir, exist_ok=True)

        ext = os.path.splitext(poster.filename)[1].lower()
        filename = f"{uuid4().hex}{ext}"
        filepath = os.path.join(poster_dir, filename)

        content = await poster.read()
        with open(filepath, "wb") as f:
            f.write(content)

        poster_path = f"posters/{filename}"

    year_int = None
    if year.strip():
        try:
            year_int = int(year)
        except ValueError:
            year_int = None

    movie_doc = {
        "title": title,
        "year": year_int,
        "language": language,
        "languages": languages,
        "quality": quality or "HD",
        "category": category,
        "watch_url": watch_url,
        "download_url": download_url,
        "poster_path": poster_path,
        "description": description,
        "created_at": datetime.utcnow(),
    }

    await db["movies"].insert_one(movie_doc)

    return RedirectResponse(
        "/admin/movies?message=Movie+saved+successfully+%E2%9C%85",
        status_code=303,
    )


@router.post("/admin/movies/{movie_id}/delete")
async def admin_delete_movie(request: Request, movie_id: str):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/movies?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(movie_id)
        await db["movies"].delete_one({"_id": oid})
        msg = "Movie+deleted+successfully"
    except Exception:
        msg = "Failed+to+delete+movie"

    return RedirectResponse(f"/admin/movies?message={msg}", status_code=303)
            
