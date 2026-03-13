from db.connection import get_connection

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    research_fields TEXT DEFAULT '[]',
    position_types TEXT DEFAULT '["Postdoc"]',
    fellowship_programs TEXT DEFAULT '[]',
    interests TEXT DEFAULT '',
    skills TEXT DEFAULT '',
    location_pref TEXT DEFAULT '[]',
    phd_completion TEXT DEFAULT '',
    degrees TEXT DEFAULT '{}',
    cv_text TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT DEFAULT '',
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    institution TEXT DEFAULT '',
    location TEXT DEFAULT '',
    country TEXT DEFAULT '',
    research_field TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    url TEXT DEFAULT '',
    salary_info TEXT DEFAULT '',
    duration TEXT DEFAULT '',
    contract_type TEXT DEFAULT '',
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, url)
);

CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    match_score REAL DEFAULT 0.0,
    matched_keywords TEXT DEFAULT '[]',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    UNIQUE(user_id, job_id)
);
"""


def init_db():
    """Create tables if they don't exist, and migrate schema if needed."""
    conn = get_connection()
    conn.executescript(_SCHEMA)
    # Migration: add position_types column if missing (for existing DBs)
    try:
        conn.execute("SELECT position_types FROM users LIMIT 1")
    except Exception:
        conn.execute("ALTER TABLE users ADD COLUMN position_types TEXT DEFAULT '[\"Postdoc\"]'")
    try:
        conn.execute("SELECT fellowship_programs FROM users LIMIT 1")
    except Exception:
        conn.execute("ALTER TABLE users ADD COLUMN fellowship_programs TEXT DEFAULT '[]'")
    try:
        conn.execute("SELECT degrees FROM users LIMIT 1")
    except Exception:
        conn.execute("ALTER TABLE users ADD COLUMN degrees TEXT DEFAULT '{}'")
    conn.commit()


# --- User helpers ---

def upsert_user_profile(username: str, *, name: str, email: str,
                         research_fields: str, position_types: str,
                         fellowship_programs: str, interests: str, skills: str,
                         location_pref: str, degrees: str,
                         cv_text: str):
    conn = get_connection()
    conn.execute(
        """UPDATE users SET name=?, email=?, research_fields=?, position_types=?,
           fellowship_programs=?, interests=?, skills=?, location_pref=?,
           degrees=?, cv_text=?
           WHERE username=?""",
        (name, email, research_fields, position_types, fellowship_programs,
         interests, skills, location_pref, degrees, cv_text, username),
    )
    conn.commit()


def get_user_profile(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if row is None:
        return None
    return dict(row)


def register_user(username: str, password_hash: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    conn.commit()


def get_user_credentials() -> dict:
    """Return {username: password_hash} for all users."""
    conn = get_connection()
    rows = conn.execute("SELECT username, password_hash FROM users").fetchall()
    return {r["username"]: r["password_hash"] for r in rows}


# --- Job helpers ---

def upsert_jobs(jobs: list[dict]):
    conn = get_connection()
    for j in jobs:
        conn.execute(
            """INSERT INTO jobs (source, external_id, title, description,
               institution, location, country, research_field, deadline,
               url, salary_info, duration, contract_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, url) DO UPDATE SET
               title=excluded.title, description=excluded.description,
               institution=excluded.institution, location=excluded.location,
               country=excluded.country, research_field=excluded.research_field,
               deadline=excluded.deadline, salary_info=excluded.salary_info,
               duration=excluded.duration, contract_type=excluded.contract_type,
               scraped_at=CURRENT_TIMESTAMP""",
            (j.get("source", ""), j.get("external_id", ""),
             j.get("title", ""), j.get("description", ""),
             j.get("institution", ""), j.get("location", ""),
             j.get("country", ""), j.get("research_field", ""),
             j.get("deadline", ""), j.get("url", ""),
             j.get("salary_info", ""), j.get("duration", ""),
             j.get("contract_type", "")),
        )
    conn.commit()


def get_all_jobs() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM jobs ORDER BY scraped_at DESC").fetchall()
    return [dict(r) for r in rows]


# --- Match helpers ---

def upsert_match(user_id: int, job_id: int, match_score: float,
                 matched_keywords: str = "[]"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO match_results (user_id, job_id, match_score, matched_keywords)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, job_id) DO UPDATE SET
           match_score=excluded.match_score,
           matched_keywords=excluded.matched_keywords,
           computed_at=CURRENT_TIMESTAMP""",
        (user_id, job_id, match_score, matched_keywords),
    )
    conn.commit()


def get_user_matches(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT m.*, j.title, j.description, j.institution, j.location,
           j.country, j.deadline, j.url, j.source, j.salary_info,
           j.duration, j.contract_type, j.research_field
           FROM match_results m JOIN jobs j ON m.job_id = j.id
           WHERE m.user_id = ?
           ORDER BY m.match_score DESC""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]
