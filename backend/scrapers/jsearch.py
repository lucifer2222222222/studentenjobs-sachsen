"""
scrapers/jsearch.py - JSearch via RapidAPI
"""
import os
import logging
import requests

log = logging.getLogger("scraper.jsearch")

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")
BASE_URL = "https://jsearch.p.rapidapi.com/search"
HEADERS = {
    "X-RapidAPI-Key":  JSEARCH_API_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
}

QUERIES = ["Minijob Dresden", "Werkstudent Leipzig", "Nebenjob Sachsen"]

SAXONY = ["dresden","leipzig","chemnitz","zwickau","freiberg","görlitz","sachsen","saxony"]

def _city(job):
    raw = (job.get("job_city") or "").lower()
    for c in SAXONY:
        if c in raw:
            return c.capitalize()
    text = (job.get("job_title","") + " " + (job.get("job_description") or "")).lower()
    for c in SAXONY:
        if c in text:
            return c.capitalize()
    return None   # not in Saxony — skip

def _category(title, desc):
    t = (title + " " + (desc or "")).lower()
    if any(w in t for w in ["food","küche","restaurant","barista","mcdonald","burger","kfc"]): return "🍔 Food"
    if any(w in t for w in ["kasse","supermarkt","retail","verkauf","lidl","rewe","aldi"]):    return "🛒 Retail"
    if any(w in t for w in ["lager","warehouse","amazon","dhl","dpd","paket"]):                return "📦 Warehouse"
    if any(w in t for w in ["hotel","rezeption","housekeeping"]):                              return "🏨 Hotel"
    if any(w in t for w in ["pflege","health","apotheke","krankenhaus"]):                      return "💊 Healthcare"
    if any(w in t for w in ["delivery","lieferung","fahrer","kurier"]):                        return "🚗 Delivery"
    if any(w in t for w in ["call center","support","kundenservice"]):                         return "📞 Call Center"
    return "🏢 Other"

def fetch_jsearch_jobs():
    if not JSEARCH_API_KEY:
        log.warning("JSEARCH_API_KEY missing – using demo data")
        return _demo_jobs()

    jobs = []
    for query in QUERIES:
        try:
            resp = requests.get(
                BASE_URL,
                headers=HEADERS,
                params={"query": query, "page": "1", "num_pages": "1", "country": "de"},
                timeout=8,
            )
            resp.raise_for_status()
            for r in resp.json().get("data", []):
                city = _city(r)
                if not city:
                    continue
                jobs.append({
                    "title":       r.get("job_title","").strip(),
                    "company":     r.get("employer_name","Unknown"),
                    "city":        city, "district": city,
                    "type":        "Werkstudent" if "werkstudent" in query.lower() else "Teilzeit",
                    "timing":      "Flexible",
                    "category":    _category(r.get("job_title",""), r.get("job_description","")),
                    "description": (r.get("job_description") or "")[:300],
                    "url":         r.get("job_apply_link") or r.get("job_google_link","#"),
                    "via":         r.get("job_publisher","jsearch"),
                    "is_new":      True, "source": "jsearch", "posted_at": "",
                })
        except Exception as e:
            log.error(f"JSearch '{query}' error: {e}")
    log.info(f"JSearch: {len(jobs)} jobs")
    return jobs if jobs else _demo_jobs()

def _demo_jobs():
    return [
        {"title":"Barista","company":"Starbucks","city":"Leipzig","district":"Leipzig","type":"Werkstudent","timing":"Mornings","category":"🍔 Food","description":"Demo – JSearch key not set","url":"https://starbucks.com/careers","via":"jsearch","is_new":True,"source":"jsearch_demo","posted_at":""},
    ]
