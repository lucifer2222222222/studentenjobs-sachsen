"""
scrapers/adzuna.py - Fetch jobs from Adzuna API
"""
import os
import logging
import requests

log = logging.getLogger("scraper.adzuna")

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
BASE_URL = "https://api.adzuna.com/v1/api/jobs/de/search"

SEARCHES = [
    {"what": "minijob",     "where": "Dresden"},
    {"what": "minijob",     "where": "Leipzig"},
    {"what": "werkstudent", "where": "Sachsen"},
    {"what": "nebenjob",    "where": "Dresden"},
    {"what": "aushilfe",    "where": "Leipzig"},
]

CATEGORY_MAP = {
    "catering": "🍔 Food", "retail": "🛒 Retail",
    "logistics": "📦 Warehouse", "hospitality": "🏨 Hotel",
    "healthcare": "💊 Healthcare", "customer-services": "📞 Call Center",
    "trade-construction": "🔧 Hardware",
}

TYPE_KEYWORDS = {
    "Minijob":     ["minijob", "mini job", "520"],
    "Werkstudent": ["werkstudent", "hiwi"],
    "Nebenjob":    ["nebenjob", "nebentätigkeit"],
    "Teilzeit":    ["teilzeit", "part-time"],
}

SAXONY = ["dresden","leipzig","chemnitz","zwickau","freiberg","görlitz","plauen","bautzen","sachsen"]

def _guess_type(title, desc):
    text = (title + " " + desc).lower()
    for t, kws in TYPE_KEYWORDS.items():
        if any(k in text for k in kws):
            return t
    return "Teilzeit"

def _extract_city(loc):
    for area in reversed(loc.get("area", [])):
        if area.lower() not in ("germany","deutschland","saxony","sachsen","europe"):
            return area
    return loc.get("display_name", "Saxony")

def _is_saxony(text):
    t = text.lower()
    return any(c in t for c in SAXONY)

def fetch_adzuna_jobs():
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        log.warning("Adzuna keys missing – using demo data")
        return _demo_jobs()

    jobs = []
    for s in SEARCHES:
        try:
            resp = requests.get(
                f"{BASE_URL}/1",
                params={
                    "app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY,
                    "results_per_page": 20, "what": s["what"],
                    "where": s["where"], "part_time": 1,
                    "content-type": "application/json",
                },
                timeout=8,   # strict 8s timeout
            )
            resp.raise_for_status()
            for r in resp.json().get("results", []):
                city = _extract_city(r.get("location", {}))
                if not _is_saxony(city + " " + r.get("title","")):
                    continue
                jobs.append({
                    "title":       r.get("title","").strip(),
                    "company":     r.get("company",{}).get("display_name","Unknown"),
                    "city":        city, "district": city,
                    "type":        _guess_type(r.get("title",""), r.get("description","")),
                    "timing":      "Flexible",
                    "category":    CATEGORY_MAP.get(r.get("category",{}).get("tag",""), "🏢 Other"),
                    "description": r.get("description","")[:300],
                    "url":         r.get("redirect_url","#"),
                    "via":         "adzuna.de", "is_new": True,
                    "source":      "adzuna", "posted_at": r.get("created",""),
                })
        except Exception as e:
            log.error(f"Adzuna '{s}' error: {e}")
    log.info(f"Adzuna: {len(jobs)} jobs")
    return jobs if jobs else _demo_jobs()

def _demo_jobs():
    return [
        {"title":"Kassierer/in","company":"REWE","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Demo – Adzuna key not set","url":"https://karriere.rewe.de","via":"adzuna.de","is_new":True,"source":"adzuna_demo","posted_at":""},
        {"title":"Crew Member","company":"McDonald's","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Demo – Adzuna key not set","url":"https://jobs.mcdonalds.de","via":"adzuna.de","is_new":True,"source":"adzuna_demo","posted_at":""},
        {"title":"Lagerhelfer","company":"DHL","city":"Leipzig","district":"Leipzig","type":"Teilzeit","timing":"Mornings","category":"📦 Warehouse","description":"Demo – Adzuna key not set","url":"https://careers.dhl.com","via":"adzuna.de","is_new":False,"source":"adzuna_demo","posted_at":""},
    ]
