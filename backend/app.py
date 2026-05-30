import os, logging, threading, time, requests, json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")
app = Flask(__name__)
CORS(app)

STARTED = datetime.utcnow().isoformat() + "Z"
CACHE_FILE = "/tmp/jobs.json"

BASE_JOBS = [
    {"id":1,"title":"Crew Member","company":"McDonald's","city":"Dresden","district":"Dresden Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True},
    {"id":2,"title":"Crew Member","company":"McDonald's","city":"Leipzig","district":"Leipzig Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True},
    {"id":3,"title":"Crew Member","company":"McDonald's","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":False},
    {"id":4,"title":"Küchenhelfer/in","company":"Burger King","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Evenings","category":"🍔 Food","description":"Kitchen assistance at Burger King Dresden.","url":"https://www.burgerking.de/jobs","via":"burgerking.de","is_new":True},
    {"id":5,"title":"Barista","company":"Starbucks","city":"Dresden","district":"Dresden Mitte","type":"Werkstudent","timing":"Flexible","category":"🍔 Food","description":"Coffee preparation and customer service.","url":"https://starbucks.com/careers","via":"starbucks.com","is_new":True},
    {"id":6,"title":"Kassierer/in","company":"REWE","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Dresden.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False},
    {"id":7,"title":"Kassierer/in","company":"REWE","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Leipzig.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False},
    {"id":8,"title":"Regalmitarbeiter/in","company":"Lidl","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Dresden.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":False},
    {"id":9,"title":"Regalmitarbeiter/in","company":"Lidl","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Chemnitz.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":True},
    {"id":10,"title":"Kassenmitarbeiter/in","company":"Aldi","city":"Freiberg","district":"Freiberg","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout at Aldi Freiberg.","url":"https://www.aldi-sued.de/karriere","via":"aldi.de","is_new":True},
    {"id":11,"title":"Aushilfe","company":"Edeka","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Dresden.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":True},
    {"id":12,"title":"Aushilfe","company":"Edeka","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Leipzig.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":False},
    {"id":13,"title":"Verkäufer/in","company":"H&M","city":"Dresden","district":"Dresden Centrum","type":"Minijob","timing":"Weekends","category":"🛒 Retail","description":"Sales and customer service at H&M Dresden.","url":"https://career.hm.com","via":"hm.com","is_new":False},
    {"id":14,"title":"Verkäufer/in","company":"DM Drogerie","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at DM Dresden.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False},
    {"id":15,"title":"Verkäufer/in","company":"DM Drogerie","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at DM Leipzig.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False},
    {"id":16,"title":"Verkäufer/in","company":"Rossmann","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at Rossmann Chemnitz.","url":"https://www.rossmann.de/karriere","via":"rossmann.de","is_new":True},
    {"id":17,"title":"Warehouse Assistant","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Teilzeit","timing":"Weekends","category":"📦 Warehouse","description":"Picking and packing at Amazon Leipzig fulfillment center.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True},
    {"id":18,"title":"Paketzusteller/in","company":"DHL","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Dresden area.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":True},
    {"id":19,"title":"Paketzusteller/in","company":"DHL","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Leipzig area.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":False},
    {"id":20,"title":"Aushilfe Lager","company":"Hermes","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Evenings","category":"📦 Warehouse","description":"Parcel sorting at Hermes Leipzig depot.","url":"https://karriere.hermesworld.com","via":"hermesworld.com","is_new":True},
    {"id":21,"title":"Lagerhelfer/in","company":"DPD","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Parcel sorting at DPD depot Dresden.","url":"https://jobs.dpd.de","via":"dpd.de","is_new":True},
    {"id":22,"title":"Delivery Rider","company":"Lieferando","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery by bike or scooter in Dresden.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":True},
    {"id":23,"title":"Delivery Rider","company":"Lieferando","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery in Leipzig. Flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":False},
    {"id":24,"title":"Rezeptionist/in","company":"Ibis Hotel","city":"Dresden","district":"Dresden","type":"Teilzeit","timing":"Mornings/Evenings","category":"🏨 Hotel","description":"Front desk and guest services at Ibis Hotel Dresden.","url":"https://careers.accor.com","via":"ibis.com","is_new":False},
    {"id":25,"title":"Haushaltshelfer/in","company":"Motel One","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Mornings","category":"🏨 Hotel","description":"Room cleaning at Motel One Leipzig.","url":"https://www.motel-one.com/de/jobs","via":"motel-one.com","is_new":True},
    {"id":26,"title":"Kinomitarbeiter/in","company":"CinemaxX","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🎬 Entertainment","description":"Ticket sales at CinemaxX Dresden.","url":"https://cinemaxx.de","via":"cinemaxx.de","is_new":False},
    {"id":27,"title":"Fitnesstrainer/in","company":"McFit","city":"Leipzig","district":"Leipzig","type":"Werkstudent","timing":"Flexible","category":"🎬 Entertainment","description":"Coaching and customer support at McFit Leipzig.","url":"https://mcfit.com","via":"mcfit.com","is_new":False},
    {"id":28,"title":"Markthelfer/in","company":"OBI Baumarkt","city":"Görlitz","district":"Görlitz","type":"Minijob","timing":"Flexible","category":"🔧 Hardware","description":"Customer service at OBI Görlitz.","url":"https://www.obi.de/unternehmen/karriere","via":"obi.de","is_new":True},
    {"id":29,"title":"Tankwart/in","company":"Aral","city":"Zwickau","district":"Zwickau","type":"Minijob","timing":"Weekends","category":"🏢 Other","description":"Customer service at Aral petrol station Zwickau.","url":"https://www.aral.de/karriere","via":"aral.de","is_new":False},
    {"id":30,"title":"Paketsortierung","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Early morning parcel sorting at Amazon Leipzig.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True},
]

SAXONY_CITIES = {
    "dresden":"Dresden","leipzig":"Leipzig","chemnitz":"Chemnitz",
    "zwickau":"Zwickau","freiberg":"Freiberg","görlitz":"Görlitz",
    "goerlitz":"Görlitz","plauen":"Plauen","bautzen":"Bautzen",
    "pirna":"Pirna","meissen":"Meißen","meißen":"Meißen","riesa":"Riesa",
}
SAXONY_REGION = list(SAXONY_CITIES.keys()) + ["sachsen","saxony"]

TYPE_KW = {
    "Minijob":     ["minijob","mini job","520 euro","geringfügig"],
    "Werkstudent": ["werkstudent","working student","hiwi"],
    "Nebenjob":    ["nebenjob","nebentätigkeit"],
    "Teilzeit":    ["teilzeit","part-time","part time"],
}
CAT_KW = {
    "🍔 Food":         ["food","küche","restaurant","barista","mcdonald","burger","kfc","subway","bäcker","café","cafe","gastronomie","catering"],
    "🛒 Retail":       ["kasse","supermarkt","retail","verkauf","lidl","rewe","aldi","edeka","zara","h&m","penny","netto","kaufland"],
    "📦 Warehouse":    ["lager","warehouse","amazon","dhl","dpd","hermes","gls","paket","logistik","fulfillment","kommission"],
    "🏨 Hotel":        ["hotel","rezeption","housekeeping","unterkunft","hostel"],
    "💊 Healthcare":   ["pflege","apotheke","dm ","rossmann","health","drogerie","krankenhaus","zahnarzt","praxis"],
    "🚗 Delivery":     ["delivery","lieferung","fahrer","kurier","lieferando","uber eats","flink"],
    "🎬 Entertainment":["kino","cinema","sport","fitness","mcfit","fitx","theater","veranstaltung"],
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


# ── File-based job store (shared across gunicorn workers) ──────────────────────

def _save(jobs, updated):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"jobs": jobs, "updated": updated}, f)
        log.info(f"Saved {len(jobs)} jobs to {CACHE_FILE}")
    except Exception as e:
        log.error(f"Save failed: {e}")

def _load():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                data = json.load(f)
            log.info(f"Loaded {len(data['jobs'])} jobs from cache")
            return data["jobs"], data["updated"]
    except Exception as e:
        log.warning(f"Load failed: {e}")
    return list(BASE_JOBS), STARTED

def _get_jobs():
    jobs, _ = _load()
    return jobs

def _get_updated():
    _, updated = _load()
    return updated


# ── Adzuna fetch ───────────────────────────────────────────────────────────────

_fetching = False

def _fetch_adzuna():
    global _fetching
    _fetching = True
    app_id  = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        _fetching = False
        return

    searches = [
        ("minijob","Dresden"),("minijob","Leipzig"),
        ("minijob","Chemnitz"),("werkstudent","Dresden"),
        ("werkstudent","Leipzig"),("aushilfe","Sachsen"),
        ("nebenjob","Sachsen"),("teilzeit","Sachsen"),
    ]

    new_jobs = []
    for what, where in searches:
        try:
            r = requests.get(
                "https://api.adzuna.com/v1/api/jobs/de/search/1",
                params={"app_id":app_id,"app_key":app_key,
                        "results_per_page":20,"what":what,"where":where,"part_time":1},
                timeout=10,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            log.info(f"Adzuna {what}/{where}: {len(results)} results")
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
                title = item.get("title","").strip()
                desc  = item.get("description","")
                new_jobs.append({
                    "title":    title,
                    "company":  item.get("company",{}).get("display_name","Unknown"),
                    "city":     city, "district": city,
                    "type":     _guess_type(title+" "+desc),
                    "timing":   "Flexible",
                    "category": _guess_cat(title+" "+desc),
                    "description": desc[:250],
                    "url":      item.get("redirect_url","#"),
                    "via":      "adzuna.de",
                    "is_new":   True,
                    "source":   "adzuna",
                })
        except Exception as e:
            log.warning(f"Adzuna {what}/{where}: {e}")

    log.info(f"Adzuna total before dedup: {len(new_jobs)}")

    # Dedup: combine base + adzuna, remove duplicates by title+company+city
    all_jobs = list(BASE_JOBS) + new_jobs
    seen = set()
    deduped = []
    for j in all_jobs:
        key = (j["title"].lower()[:40], j["company"].lower(), j["city"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(j)

    for i, j in enumerate(deduped, 1):
        j["id"] = i

    _save(deduped, datetime.utcnow().isoformat() + "Z")
    log.info(f"Saved {len(deduped)} unique jobs ({len(deduped)-len(BASE_JOBS)} from Adzuna)")
    _fetching = False


def _background():
    time.sleep(5)
    while True:
        try:
            _fetch_adzuna()
        except Exception as e:
            log.error(f"Background error: {e}")
        time.sleep(4 * 3600)


# Save base jobs to file immediately so all workers share same store
_save(BASE_JOBS, STARTED)
threading.Thread(target=_background, daemon=True).start()
log.info(f"Started. Base jobs saved to file. Adzuna fetching in 5s...")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status":"ok","jobs":len(_get_jobs())})

@app.route("/api/status", methods=["GET"])
def api_status():
    jobs = _get_jobs()
    return jsonify({
        "status":"ok","job_count":len(jobs),
        "last_updated":_get_updated(),
        "refreshing":_fetching,
        "next_refresh":"every 4 hours",
    })

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    jobs = _get_jobs()
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
                    "jobs":jobs[offset:offset+limit],"last_updated":_get_updated()})

@app.route("/api/cities", methods=["GET"])
def get_cities():
    return jsonify(sorted({j["city"] for j in _get_jobs()}))

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(sorted({j["category"] for j in _get_jobs()}))

@app.route("/api/force-refresh", methods=["GET"])
def force_refresh():
    threading.Thread(target=_fetch_adzuna, daemon=True).start()
    return jsonify({"message":"Adzuna fetch started – check /api/status in 60 seconds"})

@app.route("/api/debug/fetch", methods=["GET"])
def debug_fetch():
    app_id  = os.getenv("ADZUNA_APP_ID","")
    app_key = os.getenv("ADZUNA_APP_KEY","")
    r = requests.get(
        "https://api.adzuna.com/v1/api/jobs/de/search/1",
        params={"app_id":app_id,"app_key":app_key,
                "results_per_page":3,"what":"minijob","where":"Dresden"},
        timeout=10,
    )
    results = r.json().get("results",[])
    return jsonify([{
        "title": item.get("title",""),
        "areas": item.get("location",{}).get("area",[]),
        "city_extracted": _extract_city(item.get("location",{}).get("area",[])),
        "saxony_match": any(s in " ".join(item.get("location",{}).get("area",[])).lower() for s in SAXONY_REGION),
    } for item in results])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
