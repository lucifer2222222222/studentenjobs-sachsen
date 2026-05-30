"""
scrapers/adzuna.py
Fetches part-time jobs from the Adzuna API (free, no credit card).
Sign up at: https://developer.adzuna.com/
Set env vars: ADZUNA_APP_ID, ADZUNA_APP_KEY
"""

import os
import logging
import requests
from datetime import datetime

log = logging.getLogger("scraper.adzuna")

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

BASE_URL = "https://api.adzuna.com/v1/api/jobs/de/search"

SAXONY_SEARCHES = [
    {"what": "minijob",     "where": "Sachsen"},
    {"what": "nebenjob",    "where": "Dresden"},
    {"what": "werkstudent", "where": "Leipzig"},
    {"what": "aushilfe",    "where": "Sachsen"},
    {"what": "teilzeit student", "where": "Chemnitz"},
]

CATEGORY_MAP = {
    "catering": "🍔 Food",
    "retail":   "🛒 Retail",
    "logistics": "📦 Warehouse",
    "hospitality": "🏨 Hotel",
    "healthcare": "💊 Healthcare",
    "it-jobs":  "💻 IT",
    "pr-advertising-marketing": "📢 Marketing",
    "customer-services": "📞 Call Center",
    "teaching": "📚 Teaching",
    "trade-construction": "🔧 Hardware",
}

TYPE_KEYWORDS = {
    "Minijob":     ["minijob", "mini job", "mini-job", "520"],
    "Werkstudent": ["werkstudent", "working student", "hiwi"],
    "Nebenjob":    ["nebenjob", "nebentätigkeit", "side job"],
    "Teilzeit":    ["teilzeit", "part-time", "part time"],
}


def _guess_job_type(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    for jtype, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return jtype
    return "Teilzeit"


def _extract_city(location_data: dict) -> str:
    """Pull the most specific city from Adzuna's location object."""
    areas = location_data.get("area", [])
    # areas list goes from broad → specific e.g. ["Germany", "Saxony", "Dresden"]
    for area in reversed(areas):
        if area not in ("Germany", "Deutschland", "Saxony", "Sachsen", "Europe"):
            return area
    return location_data.get("display_name", "Saxony")


def fetch_adzuna_jobs() -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        log.warning("Adzuna credentials not set – skipping. Set ADZUNA_APP_ID and ADZUNA_APP_KEY.")
        return _demo_jobs()

    jobs = []
    for search in SAXONY_SEARCHES:
        try:
            params = {
                "app_id":          ADZUNA_APP_ID,
                "app_key":         ADZUNA_APP_KEY,
                "results_per_page": 50,
                "what":            search["what"],
                "where":           search["where"],
                "content-type":    "application/json",
                "full_time":       0,
                "part_time":       1,
            }
            resp = requests.get(f"{BASE_URL}/1", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            for r in data.get("results", []):
                city = _extract_city(r.get("location", {}))
                category_slug = r.get("category", {}).get("tag", "")
                jobs.append({
                    "title":       r.get("title", "").strip(),
                    "company":     r.get("company", {}).get("display_name", "Unknown"),
                    "city":        city,
                    "district":    city,
                    "type":        _guess_job_type(r.get("title",""), r.get("description","")),
                    "timing":      "Flexible",
                    "category":    CATEGORY_MAP.get(category_slug, "🏢 Other"),
                    "description": r.get("description", "")[:500],
                    "url":         r.get("redirect_url", "#"),
                    "via":         "adzuna.de",
                    "is_new":      True,
                    "source":      "adzuna",
                    "posted_at":   r.get("created", ""),
                })
        except Exception as e:
            log.error(f"Adzuna search '{search}' failed: {e}")

    log.info(f"Adzuna: fetched {len(jobs)} jobs")
    return jobs


def _demo_jobs() -> list[dict]:
    """Return sample jobs when no API key is set (for local development)."""
    return [
        {
            "title": "Aushilfe Kasse (Demo)", "company": "REWE", "city": "Dresden",
            "district": "Dresden", "type": "Minijob", "timing": "Weekends",
            "category": "🛒 Retail", "description": "Demo job – add your Adzuna API key.",
            "url": "https://rewe.de/karriere", "via": "adzuna.de",
            "is_new": True, "source": "adzuna_demo", "posted_at": "",
        },
    ]
