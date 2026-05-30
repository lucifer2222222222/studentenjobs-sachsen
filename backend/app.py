"""
Studentenjobs Sachsen - Flask Backend (Simplified)
Serves hardcoded chain jobs instantly + fetches from Adzuna in background.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("app")

app = Flask(__name__)
CORS(app)

REFRESH_INTERVAL_HOURS = 4

# ── Hardcoded jobs (instant, no network needed) ────────────────────────────────
HARDCODED_JOBS = [
    {"title":"Crew Member","company":"McDonald's","city":"Dresden","district":"Dresden Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Join our team at McDonald's Dresden. Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True,"source":"chains"},
    {"title":"Crew Member","company":"McDonald's","city":"Leipzig","district":"Leipzig Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Join our team at McDonald's Leipzig. Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True,"source":"chains"},
    {"title":"Crew Member","company":"McDonald's","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Join our team at McDonald's Chemnitz.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":False,"source":"chains"},
    {"title":"Kassierer/in","company":"REWE","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Dresden.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False,"source":"chains"},
    {"title":"Kassierer/in","company":"REWE","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Leipzig.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False,"source":"chains"},
    {"title":"Regalmitarbeiter/in","company":"Lidl","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Dresden. Early morning shifts available.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":False,"source":"chains"},
    {"title":"Regalmitarbeiter/in","company":"Lidl","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Chemnitz.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":True,"source":"chains"},
    {"title":"Regalmitarbeiter/in","company":"Aldi","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Stock and checkout work at Aldi Leipzig.","url":"https://www.aldi-sued.de/karriere","via":"aldi.de","is_new":False,"source":"chains"},
    {"title":"Kassenmitarbeiter/in","company":"Aldi","city":"Freiberg","district":"Freiberg","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at Aldi Freiberg.","url":"https://www.aldi-sued.de/karriere","via":"aldi.de","is_new":True,"source":"chains"},
    {"title":"Warehouse Assistant","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Teilzeit","timing":"Weekends","category":"📦 Warehouse","description":"Picking, packing and sorting at Amazon Leipzig fulfillment center. Weekend shifts available.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True,"source":"chains"},
    {"title":"Paketzusteller/in","company":"DHL","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Dresden area. Driving licence required.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":True,"source":"chains"},
    {"title":"Paketzusteller/in","company":"DHL","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Leipzig area.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":False,"source":"chains"},
    {"title":"Aushilfe Lager","company":"Hermes","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Evenings","category":"📦 Warehouse","description":"Parcel sorting at Hermes Leipzig depot. Evening shifts.","url":"https://karriere.hermesworld.com","via":"hermesworld.com","is_new":True,"source":"chains"},
    {"title":"Barista","company":"Starbucks","city":"Dresden","district":"Dresden Mitte","type":"Werkstudent","timing":"Flexible","category":"🍔 Food","description":"Coffee preparation and customer service at Starbucks Dresden.","url":"https://starbucks.com/careers","via":"starbucks.com","is_new":True,"source":"chains"},
    {"title":"Küchenhelfer/in","company":"Burger King","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Evenings","category":"🍔 Food","description":"Kitchen assistance at Burger King Chemnitz.","url":"https://www.burgerking.de/jobs","via":"burgerking.de","is_new":True,"source":"chains"},
    {"title":"Delivery Rider","company":"Lieferando","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery by bike or scooter in Dresden. Very flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":True,"source":"chains"},
    {"title":"Delivery Rider","company":"Lieferando","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery by bike or scooter in Leipzig.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":False,"source":"chains"},
    {"title":"Verkäufer/in","company":"DM Drogerie","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service and shelf management at DM Leipzig.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False,"source":"chains"},
    {"title":"Verkäufer/in","company":"DM Drogerie","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at DM Dresden.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False,"source":"chains"},
    {"title":"Verkäufer/in","company":"Rossmann","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at Rossmann Chemnitz.","url":"https://www.rossmann.de/karriere","via":"rossmann.de","is_new":True,"source":"chains"},
    {"title":"Rezeptionist/in","company":"Ibis Hotel","city":"Dresden","district":"Dresden","type":"Teilzeit","timing":"Mornings/Evenings","category":"🏨 Hotel","description":"Front desk and guest services at Ibis Hotel Dresden.","url":"https://careers.accor.com","via":"ibis.com","is_new":False,"source":"chains"},
    {"title":"Haushaltshelfer/in","company":"Motel One","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Mornings","category":"🏨 Hotel","description":"Room cleaning and housekeeping at Motel One Leipzig.","url":"https://www.motel-one.com/de/jobs","via":"motel-one.com","is_new":True,"source":"chains"},
    {"title":"Kinomitarbeiter/in","company":"CinemaxX","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🎬 Entertainment","description":"Ticket sales and cinema operations at CinemaxX Dresden.","url":"https://cinemaxx.de","via":"cinemaxx.de","is_new":False,"source":"chains"},
    {"title":"Fitnesstrainer/in","company":"McFit","city":"Leipzig","district":"Leipzig","type":"Werkstudent","timing":"Flexible","category":"🎬 Entertainment","description":"Coaching and customer support at McFit Leipzig.","url":"https://mcfit.com","via":"mcfit.com","is_new":False,"source":"chains"},
    {"title":"Verkäufer/in","company":"H&M","city":"Dresden","district":"Dresden Centrum","type":"Minijob","timing":"Weekends","category":"🛒 Retail","description":"Sales and customer service at H&M Dresden.","url":"https://career.hm.com","via":"hm.com","is_new":False,"source":"chains"},
    {"title":"Markthelfer/in","company":"OBI Baumarkt","city":"Görlitz","district":"Görlitz","type":"Minijob","timing":"Flexible","category":"🔧 Hardware","description":"Customer service and shelf stocking at OBI Görlitz.","url":"https://www.obi.de/unternehmen/karriere","via":"obi.de","is_new":True,"source":"chains"},
    {"title":"Tankwart/in","company":"Aral","city":"Zwickau","district":"Zwickau","type":"Minijob","timing":"Weekends","category":"🏢 Other","description":"Customer service at Aral petrol station Zwickau.","url":"https://www.aral.de/karriere","via":"aral.de","is_new":False,"source":"chains"},
    {"title":"Aushilfe","company":"Edeka","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Dresden.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":True,"source":"chains"},
    {"title":"Aushilfe","company":"Edeka","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Leipzig.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":False,"source":"chains"},
    {"title":"Lagerhelfer/in","company":"DPD","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Parcel sorting at DPD depot Dresden.","url":"https://jobs.dpd.de","via":"dpd.de","is_new":True,"source":"chains"},
]

# ── State ──────────────────────────────────────────────────────────────────────
_jobs = []
_last_updated = None
_is_refreshing = False
_started = False

JOBS_FILE = "/tmp/jobs_cache.json"


def save_cache():
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump({
                "jobs": _jobs,
                "last_updated": _last_updated.isoformat() if _last_updated else None,
            }, f)
    except Exception as e:
        log.error(f"Cache save failed: {e}")


def load_cache():
    global _jobs, _last_updated
    try:
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE) as f:
                data = json.load(f)
            _jobs = data.get("jobs", [])
            ts = data.get("last_updated")
            _last_updated = datetime.fromisoformat(ts) if ts else None
            log.info(f"Loaded {len(_jobs)} jobs from cache")
            return True
    except Exception as e:
        log.warning(f"Cache load failed: {e}")
    return False


def fetch_adzuna(app_id, app_key):
    """Fetch from Adzuna with a hard 5s timeout per request."""
    import requests
    jobs = []
    searches = [
        ("minijob", "Dresden"), ("minijob", "Leipzig"),
        ("werkstudent", "Sachsen"), ("aushilfe", "Sachsen"),
    ]
    saxony = ["dresden","leipzig","chemnitz","zwickau","freiberg","görlitz","sachsen"]
    for what, where in searches:
        try:
            r = requests.get(
                "https://api.adzuna.com/v1/api/jobs/de/search/1",
                params={"app_id": app_id, "app_key": app_key,
                        "results_per_page": 15, "what": what,
                        "where": where, "part_time": 1},
                timeout=5,
            )
            r.raise_for_status()
            for item in r.json().get("results", []):
                areas = item.get("location", {}).get("area", [])
                city = next((a for a in reversed(areas)
                             if a.lower() not in ("germany","deutschland","saxony","sachsen","europe")), "Saxony")
                if not any(s in city.lower() for s in saxony):
                    continue
                jobs.append({
                    "title": item.get("title","").strip(),
                    "company": item.get("company",{}).get("display_name","Unknown"),
                    "city": city, "district": city,
                    "type": "Minijob" if "minijob" in what else "Werkstudent",
                    "timing": "Flexible",
                    "category": "🏢 Other",
                    "description": item.get("description","")[:200],
                    "url": item.get("redirect_url","#"),
                    "via": "adzuna.de", "is_new": True,
                    "source": "adzuna", "posted_at": "",
                })
        except Exception as e:
            log.warning(f"Adzuna {what}/{where}: {e}")
    return jobs


def refresh_jobs():
    global _jobs, _last_updated, _is_refreshing
    if _is_refreshing:
        return
    _is_refreshing = True
    log.info("Refreshing jobs...")

    # Always start with hardcoded jobs so we always have something
    all_jobs = list(HARDCODED_JOBS)
    log.info(f"  Hardcoded: {len(all_jobs)} jobs")

    # Try Adzuna with strict timeout
    app_id  = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if app_id and app_key:
        try:
            adzuna_jobs = fetch_adzuna(app_id, app_key)
            all_jobs.extend(adzuna_jobs)
            log.info(f"  Adzuna: {len(adzuna_jobs)} jobs")
        except Exception as e:
            log.error(f"  Adzuna failed: {e}")

    # Deduplicate by title+company+city
    seen = set()
    deduped = []
    for j in all_jobs:
        key = (j.get("title","").lower()[:40], j.get("company","").lower(), j.get("city","").lower())
        if key not in seen:
            seen.add(key)
            deduped.append(j)

    # Assign IDs
    for i, j in enumerate(deduped, 1):
        j["id"] = i

    _jobs = deduped
    _last_updated = datetime.utcnow()
    _is_refreshing = False

    save_cache()
    log.info(f"Refresh done: {len(_jobs)} unique jobs")


def background_scheduler():
    while True:
        try:
            refresh_jobs()
        except Exception as e:
            log.error(f"Scheduler error: {e}")
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)


def startup():
    global _started
    if _started:
        return
    _started = True
    # Load from cache first so API responds immediately
    if not load_cache() or not _jobs:
        # No cache — run refresh immediately in background
        threading.Thread(target=refresh_jobs, daemon=True).start()
    else:
        # Have cached jobs — schedule next refresh in background
        threading.Thread(target=background_scheduler, daemon=True).start()
        return
    # Start recurring scheduler after first refresh
    def _after_first():
        while _is_refreshing:
            time.sleep(1)
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)
        background_scheduler()
    threading.Thread(target=_after_first, daemon=True).start()


startup()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "jobs": len(_jobs)})


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    city     = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    q        = request.args.get("q", "").strip().lower()
    limit    = min(int(request.args.get("limit", 100)), 200)
    offset   = int(request.args.get("offset", 0))

    jobs = _jobs

    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j.get("city","").lower() == city.lower()]

    if category and category.lower() != "all jobs":
        cat = category.split(" ", 1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat in j.get("category","").lower()]

    if q:
        jobs = [j for j in jobs if
                q in j.get("title","").lower() or
                q in j.get("company","").lower() or
                q in j.get("description","").lower()]

    return jsonify({
        "total": len(jobs), "offset": offset, "limit": limit,
        "jobs": jobs[offset: offset + limit],
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
    })


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "status": "ok",
        "job_count": len(_jobs),
        "last_updated": _last_updated.isoformat() + "Z" if _last_updated else None,
        "refreshing": _is_refreshing,
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
