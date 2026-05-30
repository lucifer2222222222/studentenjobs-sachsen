"""
scrapers/jobboards.py
Scrapes dedicated student job boards:
  - studentjob.de
  - jobmensa.de
  - minijob-zentrale.de
  - meinestadt.de
These are public, student-focused boards explicitly designed to be listed.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

log = logging.getLogger("scraper.jobboards")

HEADERS = {
    "User-Agent": "StudentenjobsSachsen-Bot/1.0 (student job aggregator; contact: your@email.de)"
}
DELAY = 2  # seconds between requests

SAXONY_CITY_KEYWORDS = [
    "dresden", "leipzig", "chemnitz", "zwickau", "freiberg",
    "görlitz", "goerlitz", "plauen", "bautzen", "sachsen", "saxony",
]

CITY_NORMALISE = {
    "sachsen": "Saxony", "saxony": "Saxony",
    "dresden": "Dresden", "leipzig": "Leipzig",
    "chemnitz": "Chemnitz", "zwickau": "Zwickau",
    "freiberg": "Freiberg", "görlitz": "Görlitz",
    "goerlitz": "Görlitz", "plauen": "Plauen",
    "bautzen": "Bautzen",
}

JOBBOARD_CONFIGS = [
    {
        "name":   "studentjob.de",
        "urls": [
            "https://www.studentjob.de/jobs?location=Sachsen&distance=50",
            "https://www.studentjob.de/jobs?location=Dresden&distance=30",
            "https://www.studentjob.de/jobs?location=Leipzig&distance=30",
        ],
        "card_selectors":  ["article.job-listing", "div.jobResult", "li.job-item", "div[class*='job']"],
        "title_selectors": ["h2", "h3", ".job-title", ".title", "strong"],
        "city_selectors":  [".location", ".city", "[class*='location']"],
        "link_selectors":  ["a[href]"],
        "via":             "studentjob.de",
        "type":            "Werkstudent",
        "category":        "🏢 Other",
    },
    {
        "name":   "jobmensa.de",
        "urls": [
            "https://www.jobmensa.de/jobs/sachsen",
            "https://www.jobmensa.de/jobs/dresden",
            "https://www.jobmensa.de/jobs/leipzig",
        ],
        "card_selectors":  ["div.job-offer", "article", "li.offer", ".stellenangebot"],
        "title_selectors": ["h2", "h3", ".offer-title", ".title"],
        "city_selectors":  [".location", ".city", "span[class*='city']"],
        "link_selectors":  ["a[href]"],
        "via":             "jobmensa.de",
        "type":            "Nebenjob",
        "category":        "🏢 Other",
    },
    {
        "name":   "minijob-zentrale.de",
        "urls": [
            "https://www.minijob-zentrale.de/DE/00_home/01_arbeitnehmer/03_minijobboerse/01_Minijobboerse_suche/node.html?suche_bundesland=Sachsen",
        ],
        "card_selectors":  ["div.result-item", "tr.job-row", "li.minijob", "article"],
        "title_selectors": ["h2", "h3", "td.title", ".position", "strong"],
        "city_selectors":  [".location", "td.city", ".ort"],
        "link_selectors":  ["a[href]"],
        "via":             "minijob-zentrale.de",
        "type":            "Minijob",
        "category":        "🏢 Other",
    },
]


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True


def _fetch_html(url: str) -> BeautifulSoup | None:
    time.sleep(DELAY)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.warning(f"Could not fetch {url}: {e}")
        return None


def _extract_text(soup_el, selectors: list[str]) -> str:
    for sel in selectors:
        el = soup_el.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return ""


def _guess_city(text: str) -> str:
    text_lower = text.lower()
    for kw, city in CITY_NORMALISE.items():
        if kw in text_lower:
            return city
    return "Saxony"


def _guess_category(title: str) -> str:
    """Simple keyword-based category guesser."""
    t = title.lower()
    if any(w in t for w in ["food", "küche", "restaurant", "cafe", "barista", "mcdonald", "burger"]):
        return "🍔 Food"
    if any(w in t for w in ["kasse", "cashier", "supermarkt", "retail", "verkauf", "markt"]):
        return "🛒 Retail"
    if any(w in t for w in ["lager", "logistik", "warehouse", "amazon", "dhl", "paket"]):
        return "📦 Warehouse"
    if any(w in t for w in ["hotel", "rezeption", "housekeeping"]):
        return "🏨 Hotel"
    if any(w in t for w in ["pflege", "health", "arzt", "apotheke", "krankenhaus"]):
        return "💊 Healthcare"
    if any(w in t for w in ["delivery", "lieferung", "fahrer", "kurier"]):
        return "🚗 Delivery"
    if any(w in t for w in ["kino", "event", "sport", "fitness"]):
        return "🎬 Entertainment"
    if any(w in t for w in ["call center", "support", "kundenservice"]):
        return "📞 Call Center"
    return "🏢 Other"


def _scrape_board(config: dict) -> list[dict]:
    jobs = []
    for url in config["urls"]:
        if not _robots_allowed(url):
            log.info(f"  Skipping {url} (robots.txt)")
            continue

        soup = _fetch_html(url)
        if not soup:
            continue

        # Try each card selector until one yields results
        cards = []
        for sel in config["card_selectors"]:
            cards = soup.select(sel)
            if len(cards) > 1:
                break

        for card in cards:
            full_text = card.get_text(" ", strip=True)

            # Must mention Saxony/city
            if not any(kw in full_text.lower() for kw in SAXONY_CITY_KEYWORDS):
                continue

            title = _extract_text(card, config["title_selectors"])
            if not title or len(title) < 4 or len(title) > 150:
                continue

            city_text = _extract_text(card, config["city_selectors"]) or full_text
            city = _guess_city(city_text)

            link_el = card.select_one("a[href]")
            href = link_el["href"] if link_el else "#"
            if href.startswith("/"):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"

            jobs.append({
                "title":       title,
                "company":     "Various",   # jobboards don't always show company
                "city":        city,
                "district":    city,
                "type":        config["type"],
                "timing":      "Flexible",
                "category":    _guess_category(title),
                "description": full_text[:400],
                "url":         href,
                "via":         config["via"],
                "is_new":      False,
                "source":      "jobboard",
                "posted_at":   "",
            })

    return jobs


def fetch_jobboard_jobs() -> list[dict]:
    all_jobs = []
    for config in JOBBOARD_CONFIGS:
        log.info(f"Scraping {config['name']}...")
        try:
            jobs = _scrape_board(config)
            log.info(f"  {config['name']}: {len(jobs)} Saxony jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  {config['name']} failed: {e}")

    if not all_jobs:
        log.warning("Job boards returned no jobs – using demo data")
        all_jobs = _demo_jobs()

    return all_jobs


def _demo_jobs() -> list[dict]:
    return [
        {
            "title": "Nachhilfelehrer/in (Demo)", "company": "Various",
            "city": "Dresden", "district": "Dresden",
            "type": "Nebenjob", "timing": "Evenings",
            "category": "📚 Teaching",
            "description": "Demo from studentjob.de – scraper will populate with real jobs.",
            "url": "https://www.studentjob.de", "via": "studentjob.de",
            "is_new": False, "source": "jobboard_demo", "posted_at": "",
        },
        {
            "title": "Aushilfe Lager (Demo)", "company": "Various",
            "city": "Leipzig", "district": "Leipzig",
            "type": "Minijob", "timing": "Flexible",
            "category": "📦 Warehouse",
            "description": "Demo from jobmensa.de – scraper will populate with real jobs.",
            "url": "https://www.jobmensa.de", "via": "jobmensa.de",
            "is_new": False, "source": "jobboard_demo", "posted_at": "",
        },
    ]
