"""Generate targeted search keywords from a user profile."""

import json
import re


# Map position type labels to search prefixes
_POSITION_PREFIXES = {
    "Postdoc": ["postdoc", "postdoctoral"],
    "PhD": ["PhD", "doctoral"],
    "Research Scientist": ["research scientist"],
    "Research Assistant": ["research assistant"],
    "Internship": ["internship", "research intern"],
    "Lecturer": ["lecturer"],
    "Assistant Professor": ["assistant professor"],
    "Associate Professor": ["associate professor"],
    "Professor": ["professor"],
    "Fellowship": ["fellowship", "research fellow"],
    "Other": ["researcher"],
}


# Map fellowship program labels to search query strings
_FELLOWSHIP_QUERIES = {
    "MSCA Marie Curie Postdoctoral Fellowship": "MSCA Marie Curie postdoctoral fellowship",
    "EMBO Postdoctoral Fellowship": "EMBO postdoctoral fellowship",
    "HFSP Postdoctoral Fellowship": "HFSP Human Frontier Science postdoctoral",
    "Alexander von Humboldt Fellowship": "Alexander von Humboldt fellowship postdoc",
    "Newton International Fellowship (Royal Society)": "Newton International Fellowship Royal Society",
    "Swiss NSF Postdoc.Mobility": "Swiss National Science Foundation postdoc mobility",
    "JSPS Postdoctoral Fellowship (Japan)": "JSPS postdoctoral fellowship Japan",
    "Fulbright Postdoctoral Fellowship": "Fulbright postdoctoral fellowship",
    "DFG Walter Benjamin Programme": "DFG Walter Benjamin postdoc",
    "ARC DECRA (Australia)": "ARC DECRA Discovery Early Career",
    "ERC Starting Grant": "ERC Starting Grant",
    "Branco Weiss Fellowship": "Branco Weiss fellowship Society in Science",
    "Life Sciences Research Foundation (LSRF)": "LSRF Life Sciences Research Foundation fellowship",
    "Helen Hay Whitney Fellowship": "Helen Hay Whitney postdoctoral fellowship",
    "Damon Runyon Fellowship": "Damon Runyon postdoctoral fellowship",
    "Wellcome Trust Early Career Award": "Wellcome Trust early career postdoc",
    "HHMI Hanna Gray Fellowship": "HHMI Hanna Gray fellowship",
    "Other fellowship": "postdoctoral fellowship",
}


def _get_prefixes(profile: dict) -> list[str]:
    """Return search prefixes based on user-selected position types."""
    types_raw = profile.get("position_types", '["Postdoc"]')
    if isinstance(types_raw, str):
        try:
            types = json.loads(types_raw)
        except (json.JSONDecodeError, TypeError):
            types = ["Postdoc"]
    else:
        types = list(types_raw)

    if not types:
        types = ["Postdoc"]

    prefixes: list[str] = []
    for t in types:
        prefixes.extend(_POSITION_PREFIXES.get(t, [t.lower()]))
    return prefixes


def generate(profile: dict) -> list[str]:
    """Build a list of search query strings from the user's profile fields.

    Combines position_types, research_fields, interests, and skills into
    targeted search queries.  Returns at most 10 queries to keep scraping fast.
    """
    queries: list[str] = []
    prefixes = _get_prefixes(profile)

    # --- Research fields → "{prefix} {field}" ---
    fields_raw = profile.get("research_fields", "[]")
    if isinstance(fields_raw, str):
        try:
            fields = json.loads(fields_raw)
        except (json.JSONDecodeError, TypeError):
            fields = [f.strip() for f in fields_raw.split(",") if f.strip()]
    else:
        fields = list(fields_raw)

    for field in fields:
        # Use the first prefix for each field to avoid explosion
        queries.append(f"{prefixes[0]} {field}")

    # --- Interests → "{prefix} {interest phrase}" ---
    interests = profile.get("interests", "")
    if interests:
        # Split on commas, semicolons, or newlines
        phrases = re.split(r"[,;\n]+", interests)
        # Alternate prefixes across interest phrases
        for i, phrase in enumerate(phrases):
            phrase = phrase.strip()
            if phrase and len(phrase) > 3:
                prefix = prefixes[i % len(prefixes)]
                queries.append(f"{prefix} {phrase}")

    # --- Skills → "{skill} research position" (only top 2) ---
    skills = profile.get("skills", "")
    if skills:
        skill_list = re.split(r"[,;\n]+", skills)
        for skill in skill_list[:2]:
            skill = skill.strip()
            if skill and len(skill) > 2:
                queries.append(f"{skill} research position")

    # --- Fellowship programs → direct fellowship search queries ---
    fellowships_raw = profile.get("fellowship_programs", "[]")
    if isinstance(fellowships_raw, str):
        try:
            fellowships = json.loads(fellowships_raw)
        except (json.JSONDecodeError, TypeError):
            fellowships = []
    else:
        fellowships = list(fellowships_raw)

    for f in fellowships:
        query = _FELLOWSHIP_QUERIES.get(f, f)
        queries.append(query)

    # Deduplicate (case-insensitive) and cap at 12
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    return unique[:12]
