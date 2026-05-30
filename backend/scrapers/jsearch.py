"""
scrapers/jsearch.py
Fetches jobs from JSearch API on RapidAPI (aggregates LinkedIn, Indeed, Glassdoor).
Free tier: 10 requests/month (enough for testing), paid tiers start at $10/mo.
Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Set env var: JSEARCH_API_KEY
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

QUERIES = [
    "Minijob Sachsen",
    "Werkstudent Dresden",
    "Werkstudent Leipzig",
    "part time student job Chemnitz",
    "Nebenjob Sachsen",
]

EMPLOYMENT_TYPE_MAP = {
    "PART_TIME":  "Teilzeit",
    "INTERN":     "Werkstudent",
    "CONTRACTOR": "Nebenjob",
    "FULLTIME":   "Teilzeit",  # include but label honestly
}

CITY_KEYWORDS = {
    "Dresden":  ["dresden"],
    "Leipzig":  ["leipzig"],
    "Chemnitz": ["chemnitz"],
    "Zwickau":  ["zwickau"],
    "Freiberg": ["freiberg"],
    "Görlitz":  ["görlitz", "goerlitz"],
    "Plauen":   ["plauen"],
    "Bautzen":  ["bautzen"],
}

CATEGORY_KEYWORDS = {
    "🍔 Food":        ["food", "restaurant", "cafe", "küche", "kitchen", "barista", "cook", "mcdonald", "burger"],
    "🛒 Retail":      ["retail", "kasse", "cashier", "verkauf", "supermarkt", "market", "shop"],
    "📦 Warehouse":   ["lager", "warehouse", "logistik", "logistics", "packer", "amazon", "dhl", "dpd"],
    "🏨 Hotel":       ["hotel", "reception", "housekeeping", "hospitality"],
    "💊 Healthcare":  ["pflege", "care", "health", "medical", "apotheke", "pharmacy", "krankenhaus"],
    "🎬 Entertainment": ["kino", "cinema", "sport", "fitness", "event"],
    "📞 Call Center": ["call center", "customer service", "support", "helpdesk"],
    "🚗 Delivery":    ["delivery", "lieferung", "fahrer", "driver", "kurier"],
    "🔧 Hardware":    ["baumarkt", "hardware", "obi", "hornbach", "handwerk"],
}


def _guess_category(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "🏢 Other"


def _extract_city(job: dict) -> str:
    city_raw = (job.get("job_city") or job.get("job_state") or "").lower()
    for city, variants in CITY_KEYWORDS.items():
        if any(v in city_raw for v in variants):
            return city
    # fallback: look in job title / description
    text = (job.get("job_title", "") + " " + job.get("job_description", "")).lower()
    for city, variants in CITY_KEYWORDS.items():
        if any(v in text for v in variants):
            return city
    return "Saxony"


def fetch_jsearch_jobs() -> list[dict]:
    if not JSEARCH_API_KEY:
        log.warning("JSEARCH_API_KEY not set – skipping JSearch. Using demo data.")
        return _demo_jobs()

    jobs = []
    for query in QUERIES:
        try:
            params = {
                "query":               query,
                "page":                "1",
                "num_pages":           "2",
                "country":             "de",
                "employment_types":    "PART_TIME,CONTRACTOR",
            }
            resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=12)
            resp.raise_for_status()
            data = resp.json()

            for r in data.get("data", []):
                city = _extract_city(r)
                emp_type = r.get("job_employment_type", "PART_TIME")
                jobs.append({
                    "title":       r.get("job_title", "").strip(),
                    "company":     r.get("employer_name", "Unknown"),
                    "city":        city,
                    "district":    city,
                    "type":        EMPLOYMENT_TYPE_MAP.get(emp_type, "Teilzeit"),
                    "timing":      "Flexible",
                    "category":    _guess_category(r.get("job_title",""), r.get("job_description","")),
                    "description": (r.get("job_description") or "")[:500],
                    "url":         r.get("job_apply_link") or r.get("job_google_link", "#"),
                    "via":         r.get("job_publisher", "jsearch"),
                    "is_new":      True,
                    "source":      "jsearch",
                    "posted_at":   str(r.get("job_posted_at_datetime_utc", "")),
                })
        except Exception as e:
            log.error(f"JSearch query '{query}' failed: {e}")

    log.info(f"JSearch: fetched {len(jobs)} jobs")
    return jobs


def _demo_jobs() -> list[dict]:
    return [
        {
            "title": "Barista (Demo)", "company": "Starbucks", "city": "Leipzig",
            "district": "Leipzig", "type": "Teilzeit", "timing": "Mornings/Weekends",
            "category": "🍔 Food", "description": "Demo job – add your JSearch API key.",
            "url": "https://starbucks.com/careers", "via": "jsearch",
            "is_new": True, "source": "jsearch_demo", "posted_at": "",
        },
    ]
