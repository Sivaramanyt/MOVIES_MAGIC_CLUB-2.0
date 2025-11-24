# routes/movies.py

from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from verification_utils import (
    should_require_verification,
    increment_free_used,
    get_user_verification_state,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def _movie_to_ctx(doc: dict) -> dict:
    """Normalize movie document into a template-friendly dict."""
    return {
        "id": str(doc.get("_id")),
        "title": doc.get("title", "Untitled"),
        "year": doc.get("year"),
        "language": doc.get("language"),
        "quality": doc.get("quality", "HD"),
        "category": doc.get("category"),
        "poster_path": doc.get("poster_path"),
        "watch_url": doc.get("watch_url"),
        "download_url": doc.get("download_url"),
        "languages": doc.get("languages", []),
        "description": doc.get("description", ""),
    }


# ---------- MOVIES DETAIL PAGE ----------

@router.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: str):
    """
    Renders movie_detail.html for a single movie (poster, title, description, buttons).
    """
    db = get_db()
    movie_doc: Optional[dict] = None
    if db is not None:
        try:
            oid = ObjectId(movie_id)
            movie_doc = await db["movies"].find_one({"_id": oid})
        except Exception:
            movie_doc = None

    if not movie_doc:
        return templates.TemplateResponse(
            "movie_detail.html",
            {
                "request": request,
                "movie": None,
                "active_tab": "movies",
            },
        )

    movie_ctx = _movie_to_ctx(movie_doc)
    return templates.TemplateResponse(
        "movie_detail.html",
        {
            "request": request,
            "movie": movie_ctx,
            "active_tab": "movies",
        },
    )


# ---------- BROWSE ALL MOVIES ----------

@router.get("/movies/browse", response_class=HTMLResponse)
async def browse_all_movies(request: Request):
    """
    Show all movies in a grid (no pagination).
    """
    db = get_db()
    movies: List[dict] = []
    if db is not None:
        cursor = db["movies"].find({"seasons": {"$exists": False}}).sort("_id", -1)
        async for doc in cursor:
            movies.append(_movie_to_ctx(doc))

    return templates.TemplateResponse(
        "browse.html",
        {
            "request": request,
            "page_title": "All Movies",
            "page_subtitle": "Browse our complete collection",
            "movies": movies,
            "active_tab": "movies",
        },
    )


# ---------- WATCH / DOWNLOAD GATES ----------

@router.get("/movie/{movie_id}/watch")
async def movie_watch(request: Request, movie_id: str):
    """
    Gate for Watch Now button - with verification
    """
    print(f"\n🎬 WATCH BUTTON CLICKED - Movie ID: {movie_id}")
    
    # Check verification
    needs_verify = await should_require_verification(request)
    
    if needs_verify:
        print(f"🚨 REDIRECTING TO VERIFICATION PAGE")
        return RedirectResponse(
            url=f"/verify/start?next=/movie/{movie_id}/watch",
            status_code=303,
        )
    
    # Increment free used
    await increment_free_used(request)
    print(f"✅ User allowed to watch")
    
    # Get movie
    db = get_db()
    movie_doc: Optional[dict] = None
    if db is not None:
        try:
            oid = ObjectId(movie_id)
            movie_doc = await db["movies"].find_one({"_id": oid})
        except Exception:
            movie_doc = None
    
    if not movie_doc or not movie_doc.get("watch_url"):
        return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)
    
    # ✅ SIMPLE: Direct redirect to watch_url (NO changes, NO conversion)
    watch_url = movie_doc["watch_url"]
    print(f"🎬 Redirecting to: {watch_url}")
    return RedirectResponse(url=watch_url, status_code=302)


@router.get("/movie/{movie_id}/download")
async def movie_download(request: Request, movie_id: str):
    """
    Gate for Download button - with verification
    """
    print(f"\n📥 DOWNLOAD BUTTON CLICKED - Movie ID: {movie_id}")
    
    # Check verification
    needs_verify = await should_require_verification(request)
    
    if needs_verify:
        print(f"🚨 REDIRECTING TO VERIFICATION PAGE")
        return RedirectResponse(
            url=f"/verify/start?next=/movie/{movie_id}/download",
            status_code=303,
        )
    
    # Increment free used
    await increment_free_used(request)
    print(f"✅ User allowed to download")
    
    # Get movie
    db = get_db()
    movie_doc: Optional[dict] = None
    if db is not None:
        try:
            oid = ObjectId(movie_id)
            movie_doc = await db["movies"].find_one({"_id": oid})
        except Exception:
            movie_doc = None

    if not movie_doc or not movie_doc.get("download_url"):
        return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)

    print(f"✅ ALLOWING DOWNLOAD")
    return RedirectResponse(url=movie_doc["download_url"], status_code=302)
    
