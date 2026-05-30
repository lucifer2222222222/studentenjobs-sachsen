"""
deduplicator.py
Removes duplicate jobs across sources using fuzzy title + company + city matching.
"""

import hashlib
import re
from difflib import SequenceMatcher


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation/whitespace for comparison."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _job_fingerprint(job: dict) -> str:
    """Strict dedup key: exact match on normalised title + company + city."""
    key = _normalise(job.get("title", "")) + "|" + \
          _normalise(job.get("company", "")) + "|" + \
          _normalise(job.get("city", ""))
    return hashlib.md5(key.encode()).hexdigest()


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """
    1. Remove exact duplicates (same fingerprint).
    2. Remove near-duplicates (title+company similarity > 90%).
    3. Assign stable integer IDs.
    4. Sort: newest first, then by city.
    """
    # Step 1: exact dedup
    seen_fps: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        fp = _job_fingerprint(job)
        if fp not in seen_fps:
            seen_fps.add(fp)
            unique.append(job)

    # Step 2: fuzzy dedup (within same city)
    by_city: dict[str, list[dict]] = {}
    for job in unique:
        city = job.get("city", "unknown")
        by_city.setdefault(city, []).append(job)

    final: list[dict] = []
    for city_jobs in by_city.values():
        kept: list[dict] = []
        for job in city_jobs:
            title_norm  = _normalise(job.get("title", ""))
            company_norm = _normalise(job.get("company", ""))
            is_dup = False
            for k in kept:
                t_sim = _similarity(title_norm,   _normalise(k.get("title", "")))
                c_sim = _similarity(company_norm, _normalise(k.get("company", "")))
                if t_sim > 0.90 and c_sim > 0.85:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(job)
        final.extend(kept)

    # Step 3: sort newest first, then by city
    final.sort(key=lambda j: (not j.get("is_new", False), j.get("city", "")))

    # Step 4: assign stable IDs
    for idx, job in enumerate(final, start=1):
        job["id"] = idx

    return final
