# routes/admin_series.py

import os
from datetime import datetime
from typing import List
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db import get_db
from .admin_auth import is_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ---------- SERIES ADMIN: LIST + SEARCH + ADD ----------


@router.get("/admin/series", response_class=HTMLResponse)
async def admin_series_dashboard(request: Request, message: str = ""):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    q = request.query_params.get("q", "").strip()
    db = get_db()
    if db is None:
        return templates.TemplateResponse(
            "admin_series.html",
            {
                "request": request,
                "message": "MongoDB not connected",
                "q": q,
                "series_list": [],
            },
        )

    col = db["series"]

    query = {}
    if q:
        query = {"title": {"$regex": q, "$options": "i"}}

    cursor = col.find(query).sort("_id", -1).limit(50)
    series_list = [
        {
            "id": str(doc.get("_id")),
            "title": doc.get("title", "Untitled series"),
            "language": doc.get("language"),
            "year": doc.get("year"),
            "seasons_count": len(doc.get("seasons", [])),
        }
        async for doc in cursor
    ]

    return templates.TemplateResponse(
        "admin_series.html",
        {
            "request": request,
            "message": message,
            "q": q,
            "series_list": series_list,
        },
    )


@router.post("/admin/series", response_class=HTMLResponse)
async def admin_create_series(
    request: Request,
    title: str = Form(...),
    year: str = Form(""),
    quality: str = Form("HD"),
    category: str = Form(""),
    description: str = Form(""),
    languages: List[str] = Form(default=[]),
    poster: UploadFile = File(None),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/series?message=MongoDB+not+connected",
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

    primary_language = languages[0] if languages else "Tamil"

    series_doc = {
        "title": title,
        "year": year_int,
        "language": primary_language,
        "quality": quality or "HD",
        "category": category,
        "description": description,
        "languages": languages,
        "poster_path": poster_path,
        "seasons": [],
        "created_at": datetime.utcnow(),
    }

    await db["series"].insert_one(series_doc)

    return RedirectResponse(
        "/admin/series?message=Series+saved+successfully+%E2%9C%85",
        status_code=303,
    )


# ---------- SERIES ADMIN: EDIT + DELETE ----------


@router.get("/admin/series/{series_id}/edit", response_class=HTMLResponse)
async def admin_edit_series_form(request: Request, series_id: str):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/series?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        series = None

    if not series:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    series_ctx = {
        "id": str(series.get("_id")),
        "title": series.get("title", ""),
        "year": series.get("year") or "",
        "language": series.get("language", "Tamil"),
        "quality": series.get("quality", "HD"),
        "category": series.get("category", ""),
        "description": series.get("description", ""),
        "languages": series.get("languages", []),
        "poster_path": series.get("poster_path"),
    }

    return templates.TemplateResponse(
        "admin_edit_series.html",
        {"request": request, "series": series_ctx},
    )


@router.post("/admin/series/{series_id}/edit", response_class=HTMLResponse)
async def admin_edit_series(
    request: Request,
    series_id: str,
    title: str = Form(...),
    year: str = Form(""),
    quality: str = Form("HD"),
    category: str = Form(""),
    description: str = Form(""),
    languages: List[str] = Form(default=[]),
    poster: UploadFile = File(None),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/series?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
    except Exception:
        return RedirectResponse(
            "/admin/series?message=Invalid+series+id",
            status_code=303,
        )

    primary_language = languages[0] if languages else "Tamil"

    update = {
        "title": title,
        "language": primary_language,
        "quality": quality or "HD",
        "category": category,
        "description": description,
        "languages": languages,
    }

    if year.strip():
        try:
            update["year"] = int(year)
        except ValueError:
            update["year"] = None
    else:
        update["year"] = None

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
        update["poster_path"] = poster_path

    await db["series"].update_one({"_id": oid}, {"$set": update})

    return RedirectResponse(
        "/admin/series?message=Series+updated+successfully",
        status_code=303,
    )


@router.post("/admin/series/{series_id}/delete")
async def admin_delete_series(request: Request, series_id: str):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/series?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        await db["series"].delete_one({"_id": oid})
        msg = "Series+deleted+successfully"
    except Exception:
        msg = "Failed+to+delete+series"

    return RedirectResponse(f"/admin/series?message={msg}", status_code=303)


# ---------- HELPER FUNCTIONS FOR SEASONS / EPISODES ----------


def _find_season_index(series: dict, season_number: int):
    seasons = series.get("seasons", [])
    for idx, s in enumerate(seasons):
        if int(s.get("number", 0)) == season_number:
            return idx
    return None


def _find_episode_index(season: dict, episode_number: int):
    episodes = season.get("episodes", [])
    for idx, e in enumerate(episodes):
        if int(e.get("number", 0)) == episode_number:
            return idx
    return None


# ---------- SEASONS ----------


@router.get("/admin/series/{series_id}/seasons", response_class=HTMLResponse)
async def admin_series_seasons(request: Request, series_id: str, message: str = ""):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            "/admin/series?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        series = None

    if not series:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    seasons = series.get("seasons", [])
    series_ctx = {
        "id": str(series.get("_id")),
        "title": series.get("title", ""),
        "language": series.get("language", "Tamil"),
        "poster_path": series.get("poster_path"),
    }

    return templates.TemplateResponse(
        "admin_series_seasons.html",
        {
            "request": request,
            "series": series_ctx,
            "seasons": seasons,
            "message": message,
        },
    )


@router.post("/admin/series/{series_id}/seasons/add", response_class=HTMLResponse)
async def admin_add_season(
    request: Request,
    series_id: str,
    number: int = Form(...),
    name: str = Form(""),
    year: str = Form(""),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    seasons = series.get("seasons", [])
    for s in seasons:
        if int(s.get("number", 0)) == number:
            return RedirectResponse(
                f"/admin/series/{series_id}/seasons?message=Season+{number}+already+exists",
                status_code=303,
            )

    year_int = None
    if year.strip():
        try:
            year_int = int(year)
        except ValueError:
            year_int = None

    new_season = {
        "number": int(number),
        "name": name or f"Season {number}",
        "year": year_int,
        "episodes": [],
    }

    await db["series"].update_one(
        {"_id": oid},
        {"$push": {"seasons": new_season}},
    )

    return RedirectResponse(
        f"/admin/series/{series_id}/seasons?message=Season+added",
        status_code=303,
    )


@router.post("/admin/series/{series_id}/seasons/{season_number}/delete", response_class=HTMLResponse)
async def admin_delete_season(request: Request, series_id: str, season_number: int):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
    except Exception:
        return RedirectResponse(
            "/admin/series?message=Invalid+series+id",
            status_code=303,
        )

    await db["series"].update_one(
        {"_id": oid},
        {"$pull": {"seasons": {"number": int(season_number)}}},
    )

    return RedirectResponse(
        f"/admin/series/{series_id}/seasons?message=Season+deleted",
        status_code=303,
    )


# ---------- EPISODES ----------


@router.get(
    "/admin/series/{series_id}/season/{season_number}/episodes",
    response_class=HTMLResponse,
)
async def admin_series_episodes(
    request: Request,
    series_id: str,
    season_number: int,
    message: str = "",
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        series = None

    if not series:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    seasons = series.get("seasons", [])
    season_idx = _find_season_index(series, season_number)
    if season_idx is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=Season+not+found",
            status_code=303,
        )

    season = seasons[season_idx]
    episodes = season.get("episodes", [])

    series_ctx = {
        "id": str(series.get("_id")),
        "title": series.get("title", ""),
        "language": series.get("language", "Tamil"),
        "poster_path": series.get("poster_path"),
    }

    return templates.TemplateResponse(
        "admin_series_episodes.html",
        {
            "request": request,
            "series": series_ctx,
            "season": season,
            "episodes": episodes,
            "message": message,
        },
    )


@router.post(
    "/admin/series/{series_id}/season/{season_number}/episodes/add",
    response_class=HTMLResponse,
)
async def admin_add_episode(
    request: Request,
    series_id: str,
    season_number: int,
    number: int = Form(...),
    title: str = Form(""),
    watch_url: str = Form(""),
    download_url: str = Form(""),
    description: str = Form(""),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/season/{season_number}/episodes?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    seasons = series.get("seasons", [])
    s_idx = _find_season_index(series, season_number)
    if s_idx is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=Season+not+found",
            status_code=303,
        )

    season = seasons[s_idx]
    episodes = season.get("episodes", [])

    for e in episodes:
        if int(e.get("number", 0)) == number:
            return RedirectResponse(
                f"/admin/series/{series_id}/season/{season_number}/episodes?message=Episode+{number}+already+exists",
                status_code=303,
            )

    new_episode = {
        "number": int(number),
        "title": title or f"Episode {number}",
        "watch_url": watch_url,
        "download_url": download_url,
        "description": description,
    }

    episodes.append(new_episode)
    season["episodes"] = episodes
    seasons[s_idx] = season

    await db["series"].update_one(
        {"_id": oid},
        {"$set": {"seasons": seasons}},
    )

    return RedirectResponse(
        f"/admin/series/{series_id}/season/{season_number}/episodes?message=Episode+added",
        status_code=303,
    )


@router.post(
    "/admin/series/{series_id}/season/{season_number}/episode/{episode_number}/delete",
    response_class=HTMLResponse,
)
async def admin_delete_episode(
    request: Request,
    series_id: str,
    season_number: int,
    episode_number: int,
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    db = get_db()
    if db is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/season/{season_number}/episodes?message=MongoDB+not+connected",
            status_code=303,
        )

    try:
        oid = ObjectId(series_id)
        series = await db["series"].find_one({"_id": oid})
    except Exception:
        return RedirectResponse(
            "/admin/series?message=Series+not+found",
            status_code=303,
        )

    seasons = series.get("seasons", [])
    s_idx = _find_season_index(series, season_number)
    if s_idx is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/seasons?message=Season+not+found",
            status_code=303,
        )

    season = seasons[s_idx]
    episodes = season.get("episodes", [])
    e_idx = _find_episode_index(season, episode_number)

    if e_idx is None:
        return RedirectResponse(
            f"/admin/series/{series_id}/season/{season_number}/episodes?message=Episode+not+found",
            status_code=303,
        )

    episodes.pop(e_idx)
    season["episodes"] = episodes
    seasons[s_idx] = season

    await db["series"].update_one(
        {"_id": oid},
        {"$set": {"seasons": seasons}},
    )

    return RedirectResponse(
        f"/admin/series/{series_id}/season/{season_number}/episodes?message=Episode+deleted",
        status_code=303,
                           )
    
