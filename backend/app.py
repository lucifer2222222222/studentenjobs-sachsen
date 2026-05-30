"""
Studentenjobs Sachsen - Flask Backend
Jobs are persisted to a JSON file so they survive worker restarts.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("app")

app = Flask(__name__)
CORS(app)

JOBS_FILE = "/tmp/jobs_cache.json"   # survives worker restarts, cleared on full redeploy
REFRESH_INTERVAL_HOURS = 4
_is_refreshing = False
_started = False


# ── Persistence ────────────────────────────────────────────────────────────────

def load_jobs_from_file():
    """Load jobs from JSON file. Returns (jobs, last_updated) or ([], None)."""
    try:
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, "r") as f:
                data = json.load(f)
            jobs = data.get("jobs", [])
            ts   = data.get("last_updated")
            last = datetime.fromisoformat(ts) if ts else None
            log.info(f"Loaded {len(jobs)} jobs from cache (updated {ts})")
            return jobs, last
    except Exception as e:
        log.warning(f"Could not load cache: {e}")
    return [], None


def save_jobs_to_file(jobs, last_updated):
    """Persist jobs to JSON file."""
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump({
                "jobs": jobs,
                "last_updated": last_updated.isoformat() if last_updated else None,
            }, f)
        log.info(f"Saved {len(jobs)} jobs to cache")
    except Exception as e:
        log.error(f"Could not save cache: {e}")


# Load from file at startup (survives gunicorn worker restarts)
_jobs, _last_updated = load_jobs_from_file()


# ── Scraping ───────────────────────────────────────────────────────────────────

def refresh_jobs():
    global _jobs, _last_updated, _is_refreshing
    if _is_refreshing:
        log.info("Already refreshing – skipping")
        return
    _is_refreshing = True
    log.info("Starting job refresh...")

    all_jobs = []
    for name, fn in [
        ("Chains",    fetch_chain_jobs),    # instant – hardcoded
        ("Adzuna",    fetch_adzuna_jobs),   # ~5s
        ("JSearch",   fetch_jsearch_jobs),  # ~5s
        ("Jobboards", fetch_jobboard_jobs), # ~10s
    ]:
        try:
            jobs = fn()
            log.info(f"  {name}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  {name} failed: {e}")

    if all_jobs:
        deduped = deduplicate_jobs(all_jobs)
        _jobs = deduped
        _last_updated = datetime.utcnow()
        save_jobs_to_file(_jobs, _last_updated)
        log.info(f"Refresh done: {len(_jobs)} unique jobs")
    else:
        log.warning("No jobs returned from any source!")

    _is_refreshing = False


def needs_refresh():
    """True if we've never fetched or it's been more than REFRESH_INTERVAL_HOURS."""
    if not _last_updated:
        return True
    age = datetime.utcnow() - _last_updated
    return age > timedelta(hours=REFRESH_INTERVAL_HOURS)


def background_scheduler():
    while True:
        if needs_refresh():
            refresh_jobs()
        time.sleep(300)   # check every 5 minutes


def start_background_thread():
    global _started
    if not _started:
        _started = True
        t = threading.Thread(target=background_scheduler, daemon=True)
        t.start()
        log.info("Background scheduler started")


# Start on import — works with gunicorn
start_background_thread()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "Studentenjobs Sachsen API",
        "status": "ok",
        "jobs": len(_jobs),
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
    })


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
        cat = category.split(" ", 1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat in j.get("category", "").lower()]

    if q:
        jobs = [j for j in jobs if
                q in j.get("title", "").lower() or
                q in j.get("company", "").lower() or
                q in j.get("description", "").lower()]

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
def api_status():
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
