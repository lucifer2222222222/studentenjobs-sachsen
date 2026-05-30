import os, logging, threading, time, requests, json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")
app = Flask(__name__)
CORS(app)

CACHE_FILE = "/tmp/jobs.json"

SAXONY_CITIES = {
    "dresden":"Dresden","leipzig":"Leipzig","chemnitz":"Chemnitz",
    "zwickau":"Zwickau","freiberg":"Freiberg","görlitz":"Görlitz",
    "goerlitz":"Görlitz","plauen":"Plauen","bautzen":"Bautzen",
    "pirna":"Pirna","meissen":"Meißen","meißen":"Meißen","riesa":"Riesa",
    "glauchau":"Glauchau","torgau":"Torgau",
}
SAXONY_REGION = list(SAXONY_CITIES.keys()) + ["sachsen","saxony"]

TYPE_KW = {
    "Minijob":     ["minijob","mini job","520 euro","geringfügig"],
    "Werkstudent": ["werkstudent","working student","hiwi"],
    "Nebenjob":    ["nebenjob","nebentätigkeit"],
    "Teilzeit":    ["teilzeit","part-time","part time"],
}
CAT_KW = {
    "🍔 Food":         ["food","küche","restaurant","barista","mcdonald","burger","kfc","subway","bäcker","café","cafe","gastronomie","catering","koch","kellner","starbucks"],
    "🛒 Retail":       ["kasse","supermarkt","retail","verkauf","lidl","rewe","aldi","edeka","zara","h&m","penny","netto","kaufland","verkäufer","rossmann","dm "],
    "📦 Warehouse":    ["lager","warehouse","amazon","dhl","dpd","hermes","gls","paket","logistik","fulfillment","kommission","sortier"],
    "🏨 Hotel":        ["hotel","rezeption","housekeeping","unterkunft","hostel","empfang"],
    "💊 Healthcare":   ["pflege","apotheke","drogerie","health","krankenhaus","zahnarzt","praxis","sanitär","arzt","medizin"],
    "🚗 Delivery":     ["delivery","lieferung","fahrer","kurier","lieferando","uber","flink","gorillas"],
    "🎬 Entertainment":["kino","cinema","sport","fitness","mcfit","fitx","theater","veranstaltung","event"],
    "📞 Call Center":  ["call center","callcenter","support","kundenservice","helpdesk","telefonist"],
    "🔧 Hardware":     ["baumarkt","obi","hornbach","handwerk","werkzeug","bauhelfer"],
}

def _guess_type(text):
    t = text.lower()
    for jt, kws in TYPE_KW.items():
        if any(k in t for k in kws):
            return jt
    return "Teilzeit"

def _guess_cat(text):
    t = text.lower()
    for cat, kws in CAT_KW.items():
        if any(k in t for k in kws):
            return cat
    return "🏢 Other"

def _extract_city(areas):
    for area in reversed(areas):
        a = area.lower().strip()
        if a in SAXONY_CITIES:
            return SAXONY_CITIES[a]
    for area in reversed(areas):
        a = area.lower().strip()
        for key, city in SAXONY_CITIES.items():
            if key in a:
                return city
    return None

def _save(jobs):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"jobs": jobs, "updated": datetime.utcnow().isoformat() + "Z"}, f)
        log.info(f"Saved {len(jobs)} jobs to cache")
    except Exception as e:
        log.error(f"Save failed: {e}")

def _load():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                data = json.load(f)
            return data.get("jobs", []), data.get("updated", "")
    except Exception as e:
        log.warning(f"Load failed: {e}")
    return [], ""

_fetching = False

# ── Search queries ─────────────────────────────────────────────────────────────
# General student job searches
GENERAL_SEARCHES = [
    ("minijob",          "Dresden"),
    ("minijob",          "Leipzig"),
    ("minijob",          "Chemnitz"),
    ("minijob",          "Zwickau"),
    ("minijob",          "Sachsen"),
    ("werkstudent",      "Dresden"),
    ("werkstudent",      "Leipzig"),
    ("werkstudent",      "Sachsen"),
    ("aushilfe",         "Sachsen"),
    ("nebenjob",         "Sachsen"),
    ("teilzeit student", "Sachsen"),
    ("minijob",          "Freiberg"),
]

# Company-specific searches — pulls real jobs from these chains
COMPANY_SEARCHES = [
    ("McDonald's",  "Sachsen"),
    ("McDonalds",   "Sachsen"),
    ("Lidl",        "Sachsen"),
    ("Aldi",        "Sachsen"),
    ("REWE",        "Sachsen"),
    ("Burger King", "Sachsen"),
    ("Starbucks",   "Sachsen"),
    ("Amazon",      "Leipzig"),
    ("DHL",         "Sachsen"),
    ("DPD",         "Sachsen"),
    ("Hermes",      "Sachsen"),
    ("Lieferando",  "Sachsen"),
    ("Rossmann",    "Sachsen"),
    ("dm ",         "Sachsen"),
    ("Edeka",       "Sachsen"),
    ("Penny",       "Sachsen"),
    ("Kaufland",    "Sachsen"),
    ("H&M",         "Sachsen"),
    ("Zara",        "Sachsen"),
    ("OBI",         "Sachsen"),
    ("Hornbach",    "Sachsen"),
    ("Ibis",        "Sachsen"),
    ("Motel One",   "Sachsen"),
    ("CinemaxX",    "Sachsen"),
    ("McFit",       "Sachsen"),
    ("Arvato",      "Sachsen"),
]

def _fetch_single(app_id, app_key, what, where):
    """Fetch one search query from Adzuna. Returns list of job dicts."""
    r = requests.get(
        "https://api.adzuna.com/v1/api/jobs/de/search/1",
        params={
            "app_id": app_id, "app_key": app_key,
            "results_per_page": 20, "what": what,
            "where": where, "part_time": 1,
            "content-type": "application/json",
        },
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    jobs = []
    for item in results:
        areas = item.get("location", {}).get("area", [])
        all_areas = " ".join(areas).lower()
        if not any(s in all_areas for s in SAXONY_REGION):
            continue
        city = _extract_city(areas)
        if not city:
            for area in reversed(areas):
                if area.lower() not in ("germany","deutschland","europe"):
                    city = area
                    break
        if not city:
            city = "Saxony"
        title   = item.get("title", "").strip()
        desc    = item.get("description", "")
        company = item.get("company", {}).get("display_name", "Unknown")
        jobs.append({
            "title":       title,
            "company":     company,
            "city":        city,
            "district":    city,
            "type":        _guess_type(title + " " + desc),
            "timing":      "Flexible",
            "category":    _guess_cat(title + " " + company + " " + desc),
            "description": desc[:300],
            "url":         item.get("redirect_url", "#"),
            "via":         "adzuna.de",
            "is_new":      True,
            "source":      "adzuna",
            "posted_at":   item.get("created", ""),
        })
    return jobs


def _fetch_adzuna():
    global _fetching
    _fetching = True
    app_id  = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        log.warning("No Adzuna keys")
        _fetching = False
        return

    all_jobs = []

    # Run general searches
    log.info("Running general searches...")
    for what, where in GENERAL_SEARCHES:
        try:
            jobs = _fetch_single(app_id, app_key, what, where)
            log.info(f"  General '{what}/{where}': {len(jobs)}")
            all_jobs.extend(jobs)
        except Exception as e:
            log.warning(f"  General '{what}/{where}': {e}")

    # Run company-specific searches
    log.info("Running company searches...")
    for what, where in COMPANY_SEARCHES:
        try:
            jobs = _fetch_single(app_id, app_key, what, where)
            log.info(f"  Company '{what}/{where}': {len(jobs)}")
            all_jobs.extend(jobs)
        except Exception as e:
            log.warning(f"  Company '{what}/{where}': {e}")

    log.info(f"Total before dedup: {len(all_jobs)}")

    # Deduplicate by title + company + city
    seen = set()
    deduped = []
    for j in all_jobs:
        key = (j["title"].lower()[:40], j["company"].lower(), j["city"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(j)

    # Sort newest first
    deduped.sort(key=lambda j: j.get("posted_at", ""), reverse=True)

    # Assign IDs
    for i, j in enumerate(deduped, 1):
        j["id"] = i

    _save(deduped)
    log.info(f"Done: {len(deduped)} unique jobs saved")
    _fetching = False


def _background():
    try:
        _fetch_adzuna()
    except Exception as e:
        log.error(f"Initial fetch error: {e}")
    while True:
        time.sleep(4 * 3600)
        try:
            _fetch_adzuna()
        except Exception as e:
            log.error(f"Scheduled fetch error: {e}")


threading.Thread(target=_background, daemon=True).start()
log.info("Background fetcher started...")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    jobs, updated = _load()
    return jsonify({"status":"ok","jobs":len(jobs),"updated":updated})

@app.route("/api/status", methods=["GET"])
def api_status():
    jobs, updated = _load()
    return jsonify({
        "status":"ok","job_count":len(jobs),
        "last_updated":updated,"refreshing":_fetching,
        "next_refresh":"every 4 hours",
    })

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    jobs, updated = _load()
    city     = request.args.get("city","").strip()
    category = request.args.get("category","").strip()
    q        = request.args.get("q","").strip().lower()
    limit    = min(int(request.args.get("limit",100)),200)
    offset   = int(request.args.get("offset",0))
    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j["city"].lower()==city.lower()]
    if category and category.lower() != "all jobs":
        cat = category.split(" ",1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat in j["category"].lower()]
    if q:
        jobs = [j for j in jobs if q in j["title"].lower()
                or q in j["company"].lower()
                or q in j.get("description","").lower()]
    return jsonify({"total":len(jobs),"offset":offset,"limit":limit,
                    "jobs":jobs[offset:offset+limit],"last_updated":updated})

@app.route("/api/cities", methods=["GET"])
def get_cities():
    jobs, _ = _load()
    return jsonify(sorted({j["city"] for j in jobs}))

@app.route("/api/categories", methods=["GET"])
def get_categories():
    jobs, _ = _load()
    return jsonify(sorted({j["category"] for j in jobs}))

@app.route("/api/force-refresh", methods=["GET"])
def force_refresh():
    threading.Thread(target=_fetch_adzuna, daemon=True).start()
    return jsonify({"message":"Fetch started – check /api/status in 90 seconds"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
