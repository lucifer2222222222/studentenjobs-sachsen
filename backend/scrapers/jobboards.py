"""
scrapers/jobboards.py - Student job boards.
Uses requests with strict timeouts. Falls back to demo data if scraping fails.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

log = logging.getLogger("scraper.jobboards")

HEADERS = {"User-Agent": "StudentenjobsSachsen-Bot/1.0 (contact: admin@studentenjobs-sachsen.de)"}
DELAY = 1
SAXONY = ["dresden","leipzig","chemnitz","zwickau","freiberg","görlitz","goerlitz","plauen","bautzen","sachsen","saxony"]

BOARDS = [
    {
        "name": "studentjob.de",
        "urls": [
            "https://www.studentjob.de/jobs?location=Dresden",
            "https://www.studentjob.de/jobs?location=Leipzig",
        ],
        "cards": ["article", "div.job-result", "li.job-item"],
        "title": ["h2","h3",".job-title","strong"],
        "link":  ["a[href]"],
        "via":   "studentjob.de",
        "type":  "Werkstudent",
    },
    {
        "name": "jobmensa.de",
        "urls": [
            "https://www.jobmensa.de/jobs/sachsen",
        ],
        "cards": ["div.job-offer","article","li.offer"],
        "title": ["h2","h3",".offer-title"],
        "link":  ["a[href]"],
        "via":   "jobmensa.de",
        "type":  "Nebenjob",
    },
]

def _fetch(url):
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=6)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning(f"Could not fetch {url}: {e}")
        return None

def _text(el, selectors):
    for s in selectors:
        t = el.select_one(s)
        if t:
            return t.get_text(strip=True)
    return ""

def _city(text):
    t = text.lower()
    for kw in SAXONY:
        if kw in t:
            return kw.capitalize().replace("Goerlitz","Görlitz").replace("Sachsen","Saxony")
    return None

def _category(title):
    t = title.lower()
    if any(w in t for w in ["food","küche","restaurant","barista","café"]): return "🍔 Food"
    if any(w in t for w in ["kasse","supermarkt","retail","verkauf"]):       return "🛒 Retail"
    if any(w in t for w in ["lager","warehouse","logistik","paket"]):        return "📦 Warehouse"
    if any(w in t for w in ["hotel","rezeption"]):                           return "🏨 Hotel"
    if any(w in t for w in ["pflege","apotheke","health"]):                  return "💊 Healthcare"
    return "🏢 Other"

def fetch_jobboard_jobs():
    all_jobs = []
    for board in BOARDS:
        for url in board["urls"]:
            soup = _fetch(url)
            if not soup:
                continue
            cards = []
            for sel in board["cards"]:
                cards = soup.select(sel)
                if len(cards) > 1:
                    break
            for card in cards:
                text = card.get_text(" ", strip=True)
                city = _city(text)
                if not city:
                    continue
                title = _text(card, board["title"])
                if not title or len(title) < 4 or len(title) > 120:
                    continue
                link = card.select_one("a[href]")
                href = link["href"] if link else "#"
                if href.startswith("/"):
                    p = urlparse(url)
                    href = f"{p.scheme}://{p.netloc}{href}"
                all_jobs.append({
                    "title": title, "company": "Various",
                    "city": city, "district": city,
                    "type": board["type"], "timing": "Flexible",
                    "category": _category(title),
                    "description": text[:200],
                    "url": href, "via": board["via"],
                    "is_new": False, "source": "jobboard", "posted_at": "",
                })
    log.info(f"Jobboards: {len(all_jobs)} jobs")
    return all_jobs if all_jobs else _demo_jobs()

def _demo_jobs():
    return [
        {"title":"Nachhilfelehrer/in","company":"Various","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings","category":"🏢 Other","description":"Tutoring students in Dresden area.","url":"https://www.studentjob.de","via":"studentjob.de","is_new":False,"source":"jobboard_demo","posted_at":""},
        {"title":"Eventhelfer/in","company":"Various","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Weekends","category":"🎬 Entertainment","description":"Event support in Leipzig.","url":"https://www.jobmensa.de","via":"jobmensa.de","is_new":False,"source":"jobboard_demo","posted_at":""},
    ]
