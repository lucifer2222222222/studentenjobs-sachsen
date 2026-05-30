import os, json, logging, threading, time, requests
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")
app = Flask(__name__)
CORS(app)

STARTED = datetime.utcnow().isoformat() + "Z"

BASE_JOBS = [
    {"id":1,"title":"Crew Member","company":"McDonald's","city":"Dresden","district":"Dresden Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed. Apply directly on our website.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True},
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
    {"id":18,"title":"Paketzusteller/in","company":"DHL","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Dresden area. Driving licence required.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":True},
    {"id":19,"title":"Paketzusteller/in","company":"DHL","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Leipzig area.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":False},
    {"id":20,"title":"Aushilfe Lager","company":"Hermes","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Evenings","category":"📦 Warehouse","description":"Parcel sorting at Hermes Leipzig depot.","url":"https://karriere.hermesworld.com","via":"hermesworld.com","is_new":True},
    {"id":21,"title":"Lagerhelfer/in","company":"DPD","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Parcel sorting at DPD depot Dresden.","url":"https://jobs.dpd.de","via":"dpd.de","is_new":True},
    {"id":22,"title":"Delivery Rider","company":"Lieferando","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery by bike or scooter in Dresden. Very flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":True},
    {"id":23,"title":"Delivery Rider","company":"Lieferando","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery in Leipzig. Flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":False},
    {"id":24,"title":"Rezeptionist/in","company":"Ibis Hotel","city":"Dresden","district":"Dresden","type":"Teilzeit","timing":"Mornings/Evenings","category":"🏨 Hotel","description":"Front desk and guest services at Ibis Hotel Dresden.","url":"https://careers.accor.com","via":"ibis.com","is_new":False},
    {"id":25,"title":"Haushaltshelfer/in","company":"Motel One","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Mornings","category":"🏨 Hotel","description":"Room cleaning at Motel One Leipzig.","url":"https://www.motel-one.com/de/jobs","via":"motel-one.com","is_new":True},
    {"id":26,"title":"Kinomitarbeiter/in","company":"CinemaxX","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🎬 Entertainment","description":"Ticket sales and cinema operations at CinemaxX Dresden.","url":"https://cinemaxx.de","via":"cinemaxx.de","is_new":False},
    {"id":27,"title":"Fitnesstrainer/in","company":"McFit","city":"Leipzig","district":"Leipzig","type":"Werkstudent","timing":"Flexible","category":"🎬 Entertainment","description":"Coaching and customer support at McFit Leipzig.","url":"https://mcfit.com","via":"mcfit.com","is_new":False},
    {"id":28,"title":"Markthelfer/in","company":"OBI Baumarkt","city":"Görlitz","district":"Görlitz","type":"Minijob","timing":"Flexible","category":"🔧 Hardware","description":"Customer service and shelf stocking at OBI Görlitz.","url":"https://www.obi.de/unternehmen/karriere","via":"obi.de","is_new":True},
    {"id":29,"title":"Tankwart/in","company":"Aral","city":"Zwickau","district":"Zwickau","type":"Minijob","timing":"Weekends","category":"🏢 Other","description":"Customer service at Aral petrol station Zwickau.","url":"https://www.aral.de/karriere","via":"aral.de","is_new":False},
    {"id":30,"title":"Paketsortierung","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Early morning parcel sorting at Amazon Leipzig.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True},
]

# Live job store — starts with hardcoded, Adzuna added in background
_jobs = list(BASE_JOBS)
_last_updated = STARTED
_fetching_adzuna = False

SAXONY = ["dresden","leipzig","chemnitz","zwickau","freiberg","görlitz","sachsen"]
TYPE_KW = {
    "Minijob":     ["minijob","mini job","520"],
    "Werkstudent": ["werkstudent","hiwi"],
    "Nebenjob":    ["nebenjob"],
    "Teilzeit":    ["teilzeit","part-time"],
}
CAT_KW = {
    "🍔 Food":       ["food","küche","restaurant","barista","mcdonald","burger","kfc","subway"],
    "🛒 Retail":     ["kasse","supermarkt","retail","verkauf","lidl","rewe","aldi","edeka","zara","h&m"],
    "📦 Warehouse":  ["lager","warehouse","amazon","dhl","dpd","hermes","paket","logistik"],
    "🏨 Hotel":      ["hotel","rezeption","housekeeping"],
    "💊 Healthcare": ["pflege","apotheke","dm ","rossmann","health","drogerie"],
    "🚗 Delivery":   ["delivery","lieferung","fahrer","kurier","lieferando"],
    "🎬 Entertainment":["kino","cinema","sport","fitness","mcfit"],
    "📞 Call Center":["call center","support","kundenservice","helpdesk"],
    "🔧 Hardware":   ["baumarkt","obi","hornbach","handwerk"],
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

def _fetch_adzuna():
    global _jobs, _last_updated, _fetching_adzuna
    _fetching_adzuna = True
    app_id  = os.getenv("ADZUNA_APP_ID","")
    app_key = os.getenv("ADZUNA_APP_KEY","")
    if not app_id or not app_key:
        log.info("No Adzuna keys – skipping")
        _fetching_adzuna = False
        return

    searches = [
        ("minijob","Dresden"), ("minijob","Leipzig"),
        ("werkstudent","Sachsen"), ("aushilfe","Sachsen"),
        ("nebenjob","Dresden"), ("minijob","Chemnitz"),
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
            for item in r.json().get("results",[]):
                areas = item.get("location",{}).get("area",[])
                city = next((a for a in reversed(areas)
                             if a.lower() not in ("germany","deutschland","saxony","sachsen","europe")), None)
                if not city or not any(s in city.lower() for s in SAXONY):
                    continue
                title = item.get("title","").strip()
                desc  = item.get("description","")
                new_jobs.append({
                    "title":   title,
                    "company": item.get("company",{}).get("display_name","Unknown"),
                    "city":    city, "district": city,
                    "type":    _guess_type(title+" "+desc),
                    "timing":  "Flexible",
                    "category":_guess_cat(title+" "+desc),
                    "description": desc[:250],
                    "url":     item.get("redirect_url","#"),
                    "via":     "adzuna.de", "is_new": True,
                    "source":  "adzuna", "posted_at": "",
                })
        except Exception as e:
            log.warning(f"Adzuna {what}/{where}: {e}")

    if new_jobs:
        # Merge with base jobs, deduplicate by title+company+city
        seen = {(j["title"].lower()[:35], j["company"].lower(), j["city"].lower())
                for j in BASE_JOBS}
        added = []
        for j in new_jobs:
            key = (j["title"].lower()[:35], j["company"].lower(), j["city"].lower())
            if key not in seen:
                seen.add(key)
                added.append(j)

        merged = list(BASE_JOBS) + added
        for i, j in enumerate(merged, 1):
            j["id"] = i
        _jobs = merged
        _last_updated = datetime.utcnow().isoformat() + "Z"
        log.info(f"Adzuna added {len(added)} new jobs → total {len(_jobs)}")
    else:
        log.info("Adzuna returned 0 new jobs")

    _fetching_adzuna = False

def _background():
    """Wait 5s after startup then fetch Adzuna, repeat every 4h."""
    time.sleep(5)
    while True:
        try:
            _fetch_adzuna()
        except Exception as e:
            log.error(f"Background fetch error: {e}")
        time.sleep(4 * 3600)

threading.Thread(target=_background, daemon=True).start()
log.info(f"Started with {len(_jobs)} hardcoded jobs, fetching Adzuna in background...")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status":"ok","jobs":len(_jobs)})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "status":"ok", "job_count":len(_jobs),
        "last_updated":_last_updated, "refreshing":_fetching_adzuna,
        "next_refresh":"every 4 hours",
    })

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    city     = request.args.get("city","").strip()
    category = request.args.get("category","").strip()
    q        = request.args.get("q","").strip().lower()
    limit    = min(int(request.args.get("limit",100)),200)
    offset   = int(request.args.get("offset",0))
    jobs = _jobs
    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j["city"].lower()==city.lower()]
    if category and category.lower() != "all jobs":
        cat = category.split(" ",1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat in j["category"].lower()]
    if q:
        jobs = [j for j in jobs if q in j["title"].lower() or q in j["company"].lower() or q in j.get("description","").lower()]
    return jsonify({"total":len(jobs),"offset":offset,"limit":limit,
                    "jobs":jobs[offset:offset+limit],"last_updated":_last_updated})

@app.route("/api/cities", methods=["GET"])
def get_cities():
    return jsonify(sorted({j["city"] for j in _jobs}))

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(sorted({j["category"] for j in _jobs}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
