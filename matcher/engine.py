"""TF-IDF cosine similarity matching + urgency scoring."""

import json
import re
from datetime import datetime, date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _build_profile_text(profile: dict) -> str:
    """Concatenate profile fields into a single text document."""
    parts = []

    fields_raw = profile.get("research_fields", "[]")
    if isinstance(fields_raw, str):
        try:
            fields = json.loads(fields_raw)
        except (json.JSONDecodeError, TypeError):
            fields = [fields_raw]
    else:
        fields = list(fields_raw)
    parts.extend(fields)

    for key in ("interests", "skills", "cv_text"):
        val = profile.get(key, "")
        if val:
            parts.append(val)

    return " ".join(parts)


def _build_job_text(job: dict) -> str:
    """Concatenate job fields into a single text document."""
    parts = []
    for key in ("title", "description", "research_field", "institution"):
        val = job.get(key, "")
        if val:
            parts.append(val)
    return " ".join(parts)


def _parse_deadline(deadline_str: str) -> date | None:
    """Try to parse a deadline string into a date object."""
    if not deadline_str:
        return None

    # Try common date patterns
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%B %d, %Y",
                "%d %b %Y", "%b %d, %Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(deadline_str.strip(), fmt).date()
        except ValueError:
            continue

    # Try to extract a date from surrounding text
    match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", deadline_str, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3)}", "%d %B %Y").date()
        except ValueError:
            pass

    match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})", deadline_str, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(f"{match.group(2)} {match.group(1)} {match.group(3)}", "%d %B %Y").date()
        except ValueError:
            pass

    return None


def compute_urgency(deadline_str: str) -> tuple[float, int | None]:
    """Compute urgency score (0-100) and days until deadline.

    Returns (urgency_score, days_remaining).
    Higher urgency = closer to deadline.
    """
    deadline = _parse_deadline(deadline_str)
    if deadline is None:
        return 50.0, None  # Unknown deadline → medium urgency

    days = (deadline - date.today()).days
    if days < 0:
        return 0.0, days  # Already passed
    if days <= 7:
        return 100.0, days
    if days <= 14:
        return 90.0, days
    if days <= 30:
        return 70.0, days
    if days <= 60:
        return 50.0, days
    if days <= 90:
        return 30.0, days
    return 10.0, days


def rank_jobs(profile: dict, jobs: list[dict],
              match_weight: float = 0.7,
              urgency_weight: float = 0.3) -> list[dict]:
    """Rank jobs against a user profile using TF-IDF + urgency.

    Returns jobs sorted by combined rank_score descending, each annotated with:
      - match_pct (0-100)
      - urgency_score (0-100)
      - days_until_deadline (int or None)
      - rank_score (weighted combo)
      - matched_keywords (list of top overlapping terms)
    """
    if not jobs:
        return []

    profile_text = _build_profile_text(profile)
    if not profile_text.strip():
        # No profile text → can't compute similarity
        for j in jobs:
            j["match_pct"] = 0
            j["urgency_score"], j["days_until_deadline"] = compute_urgency(j.get("deadline", ""))
            j["rank_score"] = j["urgency_score"] * urgency_weight
            j["matched_keywords"] = []
        return sorted(jobs, key=lambda j: j["rank_score"], reverse=True)

    job_texts = [_build_job_text(j) for j in jobs]

    # Build TF-IDF vectors: first doc is the profile, rest are jobs
    corpus = [profile_text] + job_texts
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Cosine similarity of profile (row 0) vs each job (rows 1..N)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    feature_names = vectorizer.get_feature_names_out()
    profile_vec = tfidf_matrix[0].toarray().flatten()

    for i, job in enumerate(jobs):
        match_pct = round(float(similarities[i]) * 100, 1)
        urgency_score, days = compute_urgency(job.get("deadline", ""))
        rank_score = round(match_pct * match_weight + urgency_score * urgency_weight, 1)

        # Find top overlapping keywords
        job_vec = tfidf_matrix[i + 1].toarray().flatten()
        overlap = profile_vec * job_vec
        top_indices = overlap.argsort()[-5:][::-1]
        matched_kw = [feature_names[idx] for idx in top_indices if overlap[idx] > 0]

        job["match_pct"] = match_pct
        job["urgency_score"] = urgency_score
        job["days_until_deadline"] = days
        job["rank_score"] = rank_score
        job["matched_keywords"] = matched_kw

    return sorted(jobs, key=lambda j: j["rank_score"], reverse=True)
