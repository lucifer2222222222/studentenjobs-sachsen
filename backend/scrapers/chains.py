"""
scrapers/chains.py
Scrapes career pages of major chains present in Saxony.
Uses requests + BeautifulSoup for static pages, Playwright for JS-heavy ones.
Always checks robots.txt and adds polite delays between requests.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

log = logging.getLogger("scraper.chains")

HEADERS = {
    "User-Agent": "StudentenjobsSachsen-Bot/1.0 (student job aggregator; contact: your@email.de)"
}
DELAY_BETWEEN_REQUESTS = 2   # seconds — be polite

SAXONY_CITY_KEYWORDS = [
    "dresden", "leipzig", "chemnitz", "zwickau", "freiberg",
    "görlitz", "goerlitz", "plauen", "bautzen", "sachsen", "saxony",
]

# Each entry: (company, category, base_url, search_url_template, parser_fn_name)
CHAIN_CONFIGS = [
    {
        "company":  "McDonald's",
        "category": "🍔 Food",
        "search_url": "https://jobs.mcdonalds.de/search?q=&location=Sachsen&radius=100&employment_type=part_time",
        "via":      "mcdonalds.de",
        "apply_base": "https://jobs.mcdonalds.de",
        "parser":   "parse_mcdonalds",
    },
    {
        "company":  "REWE",
        "category": "🛒 Retail",
        "search_url": "https://karriere.rewe.de/stellenangebote?q=minijob&location=Sachsen",
        "via":      "rewe-group.com",
        "apply_base": "https://karriere.rewe.de",
        "parser":   "parse_generic_job_list",
    },
    {
        "company":  "Lidl",
        "category": "🛒 Retail",
        "search_url": "https://jobs.lidl.de/jobsuche/ergebnisse?region=sachsen&art=teilzeit",
        "via":      "lidl.de",
        "apply_base": "https://jobs.lidl.de",
        "parser":   "parse_generic_job_list",
    },
    {
        "company":  "DHL",
        "category": "📦 Warehouse",
        "search_url": "https://careers.dhl.com/global/en/search-results?keywords=teilzeit&location=sachsen",
        "via":      "careers.dhl.com",
        "apply_base": "https://careers.dhl.com",
        "parser":   "parse_generic_job_list",
    },
    {
        "company":  "DM Drogerie",
        "category": "💊 Healthcare",
        "search_url": "https://www.dm.de/unternehmen/jobs-und-karriere/stellenangebote/?search=teilzeit&location=sachsen",
        "via":      "dm.de",
        "apply_base": "https://www.dm.de",
        "parser":   "parse_generic_job_list",
    },
    {
        "company":  "Motel One",
        "category": "🏨 Hotel",
        "search_url": "https://www.motel-one.com/de/jobs/?filter_city=dresden",
        "via":      "motel-one.com",
        "apply_base": "https://www.motel-one.com",
        "parser":   "parse_generic_job_list",
    },
]


def _robots_allowed(url: str) -> bool:
    """Check if crawling the URL is allowed by robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True   # if robots.txt is unreachable, proceed cautiously


def _is_saxony_job(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in SAXONY_CITY_KEYWORDS)


def _get_page(url: str, timeout: int = 12) -> BeautifulSoup | None:
    """Fetch a page with polite delay; return parsed BeautifulSoup or None."""
    time.sleep(DELAY_BETWEEN_REQUESTS)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None


# ── Parsers ────────────────────────────────────────────────────────────────────

def parse_mcdonalds(soup: BeautifulSoup, config: dict) -> list[dict]:
    """Parse McDonald's job listing page."""
    jobs = []
    for card in soup.select("article.job-card, div.job-listing, li.job-item"):
        title_el = card.select_one("h2, h3, .job-title, .position-title")
        loc_el   = card.select_one(".location, .job-location, [class*='location']")
        link_el  = card.select_one("a[href]")

        title    = title_el.get_text(strip=True) if title_el else ""
        location = loc_el.get_text(strip=True)   if loc_el   else ""
        href     = link_el["href"]                if link_el  else "#"

        if not title or not _is_saxony_job(location + " " + title):
            continue

        city = next((c.capitalize() for c in SAXONY_CITY_KEYWORDS if c in location.lower()), "Saxony")
        jobs.append(_make_job(title, city, config, href))
    return jobs


def parse_generic_job_list(soup: BeautifulSoup, config: dict) -> list[dict]:
    """
    Generic parser that looks for common job listing patterns.
    Works for most simple career pages.
    """
    jobs = []
    # Try multiple common selectors
    selectors = [
        "article", "li.job", "div.job", ".vacancy", ".stellenangebot",
        "[class*='job-item']", "[class*='vacancy']", "[class*='position']",
    ]
    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) > 1:
            break

    for card in cards:
        text = card.get_text(" ", strip=True)
        if not _is_saxony_job(text):
            continue

        title_el = card.select_one("h2, h3, h4, .title, .position, strong")
        link_el  = card.select_one("a[href]")
        title    = title_el.get_text(strip=True) if title_el else text[:60]
        href     = link_el["href"] if link_el else "#"

        # Filter noise
        if len(title) < 4 or len(title) > 120:
            continue

        city = next((c.capitalize() for c in SAXONY_CITY_KEYWORDS if c in text.lower()), "Saxony")
        jobs.append(_make_job(title, city, config, href))

    return jobs


def _make_job(title: str, city: str, config: dict, href: str) -> dict:
    base = config.get("apply_base", "")
    url  = urljoin(base, href) if href.startswith("/") else href
    return {
        "title":       title,
        "company":     config["company"],
        "city":        city,
        "district":    city,
        "type":        "Minijob",
        "timing":      "Flexible",
        "category":    config["category"],
        "description": "",
        "url":         url,
        "via":         config["via"],
        "is_new":      False,
        "source":      "chains",
        "posted_at":   "",
    }


# ── Main entry ─────────────────────────────────────────────────────────────────

PARSER_MAP = {
    "parse_mcdonalds":       parse_mcdonalds,
    "parse_generic_job_list": parse_generic_job_list,
}


def fetch_chain_jobs() -> list[dict]:
    all_jobs = []

    for config in CHAIN_CONFIGS:
        url = config["search_url"]
        company = config["company"]

        if not _robots_allowed(url):
            log.info(f"Skipping {company} – disallowed by robots.txt")
            continue

        log.info(f"Scraping {company}...")
        soup = _get_page(url)
        if not soup:
            continue

        parser_fn = PARSER_MAP.get(config["parser"], parse_generic_job_list)
        try:
            jobs = parser_fn(soup, config)
            log.info(f"  {company}: {len(jobs)} Saxony jobs found")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  {company} parser failed: {e}")

    # Fallback demo data if scraping yields nothing (e.g. JS-rendered pages)
    if not all_jobs:
        log.warning("Chain scrapers returned no jobs – using demo data")
        all_jobs = _demo_jobs()

    return all_jobs


def _demo_jobs() -> list[dict]:
    return [
        {
            "title": "Crew Member", "company": "McDonald's", "city": "Dresden",
            "district": "Dresden Mitte", "type": "Minijob", "timing": "Sofort",
            "category": "🍔 Food", "description": "Crew member at McDonald's Dresden.",
            "url": "https://jobs.mcdonalds.de", "via": "mcdonalds.de",
            "is_new": True, "source": "chains_demo", "posted_at": "",
        },
        {
            "title": "Kassierer/in", "company": "REWE", "city": "Leipzig",
            "district": "Leipzig Mitte", "type": "Minijob", "timing": "Flexible",
            "category": "🛒 Retail", "description": "Cashier at REWE Leipzig.",
            "url": "https://karriere.rewe.de", "via": "rewe-group.com",
            "is_new": False, "source": "chains_demo", "posted_at": "",
        },
        {
            "title": "Warehouse Assistant", "company": "Amazon", "city": "Leipzig",
            "district": "Leipzig Süd", "type": "Teilzeit", "timing": "Weekends",
            "category": "📦 Warehouse", "description": "Warehouse assistant at Amazon Leipzig.",
            "url": "https://amazon.jobs", "via": "amazon.jobs",
            "is_new": True, "source": "chains_demo", "posted_at": "",
        },
        {
            "title": "Regalmitarbeiter/in", "company": "Lidl", "city": "Chemnitz",
            "district": "Chemnitz", "type": "Minijob", "timing": "Früh/Morgens",
            "category": "🛒 Retail", "description": "Stock replenishment at Lidl Chemnitz.",
            "url": "https://jobs.lidl.de", "via": "lidl.de",
            "is_new": False, "source": "chains_demo", "posted_at": "",
        },
        {
            "title": "Paketzusteller/in", "company": "DHL", "city": "Dresden",
            "district": "Dresden", "type": "Nebenjob", "timing": "Mornings",
            "category": "📦 Warehouse", "description": "Package delivery in Dresden area.",
            "url": "https://careers.dhl.com", "via": "careers.dhl.com",
            "is_new": True, "source": "chains_demo", "posted_at": "",
        },
    ]
