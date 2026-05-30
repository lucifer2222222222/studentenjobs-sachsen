"""
Studentenjobs Sachsen - Flask Backend
Aggregates part-time jobs from multiple sources for students in Saxony, Germany.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

from scrapers.adzuna import fetch_adzuna_jobs
from scrapers.jsearch import fetch_jsearch_jobs
from scrapers.chains import fetch_chain_jobs
from scrapers.jobboards import fetch_jobboard_jobs
from deduplicator import deduplicate_jobs

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("app")

# ── Flask setup ─────────────────────────────────────────────────────────────── 
app = Flask(__name__)
CORS(app)  # Allow requests from GitHub Pages frontend

# ── In-memory job store ────────────────────────────────────────────────────────
_jobs: list[dict] = []
_last_updated: datetime | None = None
_is_refreshing = False
REFRESH_INTERVAL_HOURS = 4   # How often to re-scrape all sources

SAXONY_CITIES = ["Dresden", "Leipzig", "Chemnitz", "Zwickau", "Freiberg", "Görlitz",
                 "Plauen", "Bautzen", "Erfurt", "Halle", "Jena"]

# ── Job refresh logic ──────────────────────────────────────────────────────────

def refresh_jobs():
    """Scrape all sources, deduplicate, and update the in-memory store."""
    global _jobs, _last_updated, _is_refreshing
    if _is_refreshing:
        log.info("Refresh already in progress – skipping.")
        return
    _is_refreshing = True
    log.info("🔄 Starting full job refresh...")

    all_jobs = []
    sources = [
        ("Adzuna API",      fetch_adzuna_jobs),
        ("JSearch API",     fetch_jsearch_jobs),
        ("Chain portals",   fetch_chain_jobs),
        ("Job boards",      fetch_jobboard_jobs),
    ]
    for name, fn in sources:
        try:
            jobs = fn()
            log.info(f"  ✅ {name}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  ❌ {name} failed: {e}")

    deduped = deduplicate_jobs(all_jobs)
    log.info(f"✨ Refresh complete: {len(all_jobs)} raw → {len(deduped)} unique jobs")

    _jobs = deduped
    _last_updated = datetime.utcnow()
    _is_refreshing = False


def background_scheduler():
    """Run refresh_jobs() every REFRESH_INTERVAL_HOURS in a background thread."""
    while True:
        refresh_jobs()
        log.info(f"💤 Next refresh in {REFRESH_INTERVAL_HOURS}h")
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)


# ── API routes ─────────────────────────────────────────────────────────────────

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """
    GET /api/jobs
    Query params:
      city     – filter by city (optional)
      category – filter by job category (optional)
      q        – free-text search (optional)
      lang     – language code, not used server-side yet (optional)
      limit    – max results (default 100)
      offset   – pagination offset (default 0)
    """
    city     = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    q        = request.args.get("q", "").strip().lower()
    limit    = min(int(request.args.get("limit", 100)), 200)
    offset   = int(request.args.get("offset", 0))

    jobs = _jobs

    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j.get("city", "").lower() == city.lower()]

    if category and category.lower() != "all jobs":
        # Strip emoji prefix if present
        cat_clean = category.split(" ", 1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat_clean in j.get("category", "").lower()]

    if q:
        jobs = [j for j in jobs
                if q in j.get("title", "").lower()
                or q in j.get("company", "").lower()
                or q in j.get("description", "").lower()]

    total = len(jobs)
    page  = jobs[offset: offset + limit]

    return jsonify({
        "total":        total,
        "offset":       offset,
        "limit":        limit,
        "jobs":         page,
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
    })


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """GET /api/jobs/<id> – fetch a single job by its ID."""
    job = next((j for j in _jobs if str(j.get("id")) == str(job_id)), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/status", methods=["GET"])
def status():
    """Health-check & stats endpoint."""
    return jsonify({
        "status":       "ok",
        "job_count":    len(_jobs),
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
        "refreshing":   _is_refreshing,
        "next_refresh": (
            (_last_updated + timedelta(hours=REFRESH_INTERVAL_HOURS)).isoformat() + "Z"
            if _last_updated else "pending"
        ),
    })


@app.route("/api/refresh", methods=["POST"])
def manual_refresh():
    """POST /api/refresh – trigger a manual refresh (admin use)."""
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != os.getenv("ADMIN_SECRET", "change-me"):
        return jsonify({"error": "Unauthorized"}), 401
    thread = threading.Thread(target=refresh_jobs, daemon=True)
    thread.start()
    return jsonify({"message": "Refresh started"}), 202


@app.route("/api/cities", methods=["GET"])
def get_cities():
    """Return list of cities that currently have jobs."""
    cities = sorted({j["city"] for j in _jobs if j.get("city")})
    return jsonify(cities)


@app.route("/api/categories", methods=["GET"])
def get_categories():
    """Return list of categories that currently have jobs."""
    cats = sorted({j["category"] for j in _jobs if j.get("category")})
    return jsonify(cats)


# ── Startup ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=background_scheduler, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)

# This runs when started by gunicorn (Render uses gunicorn, not __main__)
else:
    t = threading.Thread(target=background_scheduler, daemon=True)
    t.start()
    log.info("🚀 Studentenjobs Sachsen backend starting on :5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
