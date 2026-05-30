"""
Studentenjobs Sachsen - Flask Backend
"""

import os
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("app")

app = Flask(__name__)
CORS(app)

_jobs = []
_last_updated = None
_is_refreshing = False
_started = False
REFRESH_INTERVAL_HOURS = 4


def refresh_jobs():
    global _jobs, _last_updated, _is_refreshing
    if _is_refreshing:
        return
    _is_refreshing = True
    log.info("Refreshing jobs...")
    all_jobs = []
    for name, fn in [
        ("Adzuna",    fetch_adzuna_jobs),
        ("JSearch",   fetch_jsearch_jobs),
        ("Chains",    fetch_chain_jobs),
        ("Jobboards", fetch_jobboard_jobs),
    ]:
        try:
            jobs = fn()
            log.info(f"  {name}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  {name} failed: {e}")
    _jobs = deduplicate_jobs(all_jobs)
    _last_updated = datetime.utcnow()
    _is_refreshing = False
    log.info(f"Done: {len(_jobs)} unique jobs")


def background_scheduler():
    while True:
        refresh_jobs()
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)


def start_background_thread():
    """Call once at startup regardless of whether gunicorn or dev server."""
    global _started
    if not _started:
        _started = True
        t = threading.Thread(target=background_scheduler, daemon=True)
        t.start()
        log.info("Background scheduler started")


# ── Start on import (works with gunicorn) ─────────────────────────────────────
start_background_thread()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"name": "Studentenjobs Sachsen API", "status": "ok", "jobs": len(_jobs)})


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    city     = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    q        = request.args.get("q", "").strip().lower()
    limit    = min(int(request.args.get("limit", 100)), 200)
    offset   = int(request.args.get("offset", 0))

    jobs = _jobs

    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j.get("city", "").lower() == city.lower()]

    if category and category.lower() != "all jobs":
        cat_clean = category.split(" ", 1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat_clean in j.get("category", "").lower()]

    if q:
        jobs = [j for j in jobs if q in j.get("title","").lower()
                or q in j.get("company","").lower()
                or q in j.get("description","").lower()]

    return jsonify({
        "total":        len(jobs),
        "offset":       offset,
        "limit":        limit,
        "jobs":         jobs[offset: offset + limit],
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
    })


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = next((j for j in _jobs if str(j.get("id")) == str(job_id)), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/status", methods=["GET"])
def status():
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
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != os.getenv("ADMIN_SECRET", "change-me"):
        return jsonify({"error": "Unauthorized"}), 401
    threading.Thread(target=refresh_jobs, daemon=True).start()
    return jsonify({"message": "Refresh started"}), 202


@app.route("/api/cities", methods=["GET"])
def get_cities():
    return jsonify(sorted({j["city"] for j in _jobs if j.get("city")}))


@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(sorted({j["category"] for j in _jobs if j.get("category")}))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
