import logging
import threading
import time

import pandas as pd
import streamlit as st
from datetime import datetime

from auth import require_auth, logout
from db.models import init_db, get_user_profile, upsert_jobs, get_all_jobs

from scraper.agent import ScraperAgent
from scraper import keywords as kw_gen

logger = logging.getLogger(__name__)

init_db()
username = require_auth()
if username is None:
    st.stop()

with st.sidebar:
    st.write(f"Logged in as **{username}**")
    if st.button("Logout", key="logout_jobs"):
        logout()

st.title("🔎 Position Browser")

profile = get_user_profile(username)
if not profile or profile.get("research_fields", "[]") == "[]":
    st.warning("Please complete your profile first (Profile page) before scanning for positions.")
    st.stop()

# Show generated search keywords
search_terms = kw_gen.generate(profile)
with st.expander("Search keywords (auto-generated from your profile)"):
    for term in search_terms:
        st.write(f"• {term}")


# --- Background scan function (runs in a daemon thread) ---
def _run_scan_background(user_profile: dict, scan_state: dict, user_email: str):
    """Run scraper in background thread, writing progress to scan_state dict."""
    try:
        agent = ScraperAgent()

        def status_cb(site_name: str, count: int, error: str | None):
            if error:
                scan_state["progress"][site_name] = {"status": "❌", "count": 0, "error": error}
            else:
                scan_state["progress"][site_name] = {"status": "✅", "count": count, "error": None}

        jobs = agent.run_all(user_profile, status_callback=status_cb)
        # Save directly to DB from thread so results survive browser close
        if jobs:
            upsert_jobs(jobs)
        scan_state["result_count"] = len(jobs)

        # Send email notification if configured
        if user_email:
            try:
                from utils.email_notify import send_scan_complete
                send_scan_complete(user_email, len(jobs))
            except Exception as exc:
                logger.warning("Email notification failed: %s", exc)

    except Exception as e:
        scan_state["error"] = str(e)
        logger.error("Background scan failed: %s", e)
    finally:
        scan_state["running"] = False


# --- Initialize scan state ---
if "scan_state" not in st.session_state:
    st.session_state["scan_state"] = {
        "running": False,
        "progress": {},
        "result_count": None,
        "error": None,
        "results_saved": False,
    }

scan_state = st.session_state["scan_state"]

# --- Scan button (disabled while running) ---
if scan_state["running"]:
    st.button("🔍 Scan in progress…", disabled=True)
else:
    if st.button("🔍 Scan for Positions", type="primary"):
        scan_state.update({
            "running": True,
            "progress": {},
            "result_count": None,
            "error": None,
            "results_saved": False,
        })
        user_email = profile.get("email", "")
        thread = threading.Thread(
            target=_run_scan_background,
            args=(profile, scan_state, user_email),
            daemon=True,
        )
        thread.start()
        st.rerun()

# --- Show progress / results ---
if scan_state["progress"]:
    lines = []
    for name, info in scan_state["progress"].items():
        if info["error"]:
            lines.append(f"{info['status']} **{name}**: error — {info['error']}")
        else:
            lines.append(f"{info['status']} **{name}**: found {info['count']} positions")
    st.markdown("\n\n".join(lines))

if scan_state["running"]:
    st.info("⏳ Scanning academic boards… you can navigate to other pages and come back.")
    time.sleep(2)
    st.rerun()
elif scan_state["result_count"] is not None and not scan_state["results_saved"]:
    # Scan just finished — results already saved to DB by the thread
    st.session_state["last_scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if scan_state["result_count"] > 0:
        st.success(f"Scan complete! Found {scan_state['result_count']} unique positions.")
    else:
        st.warning("No positions found. Try broadening your profile interests.")
    if scan_state["error"]:
        st.error(f"Scan error: {scan_state['error']}")
    scan_state["results_saved"] = True
elif scan_state.get("error") and not scan_state.get("results_saved"):
    st.error(f"Scan failed: {scan_state['error']}")
    scan_state["results_saved"] = True

st.divider()

# --- Display jobs ---
last_scan = st.session_state.get("last_scan_time")
if last_scan:
    st.caption(f"Last scanned: {last_scan}")

jobs = get_all_jobs()
if not jobs:
    st.info("No positions found yet. Click **Scan for Positions** above to start searching.")
    st.stop()

df = pd.DataFrame(jobs)

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    sources = sorted(df["source"].unique().tolist())
    selected_sources = st.multiselect("Source", sources, default=sources)
with col2:
    countries = sorted(df["country"].dropna().unique().tolist())
    if countries:
        selected_countries = st.multiselect("Country", countries, default=countries)
    else:
        selected_countries = []
with col3:
    fields = sorted(df["research_field"].dropna().unique().tolist())
    fields = [f for f in fields if f]
    if fields:
        selected_fields = st.multiselect("Research Field", fields, default=fields)
    else:
        selected_fields = []

# Apply filters
mask = df["source"].isin(selected_sources)
if selected_countries:
    mask &= df["country"].isin(selected_countries)
if selected_fields:
    mask &= df["research_field"].isin(selected_fields)

filtered = df[mask]

st.subheader(f"Positions ({len(filtered)} of {len(df)})")

# Display columns
display_cols = ["title", "institution", "location", "country", "source", "deadline", "url"]
available_cols = [c for c in display_cols if c in filtered.columns]

st.dataframe(
    filtered[available_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "url": st.column_config.LinkColumn("Link", display_text="View"),
        "title": st.column_config.TextColumn("Title", width="large"),
    },
)

# Expandable details
st.subheader("Position Details")
for _, job in filtered.head(50).iterrows():
    title = job.get("title", "Untitled")
    inst = job.get("institution", "")
    label = f"{title} — {inst}" if inst else title
    with st.expander(label):
        cols = st.columns([2, 1])
        with cols[0]:
            desc = job.get("description", "")
            if desc:
                st.write(desc[:2000])
            else:
                st.write("*No description available*")
        with cols[1]:
            st.write(f"**Source:** {job.get('source', '')}")
            st.write(f"**Location:** {job.get('location', '')}")
            st.write(f"**Deadline:** {job.get('deadline', 'N/A')}")
            st.write(f"**Salary:** {job.get('salary_info', 'N/A')}")
            url = job.get("url", "")
            if url:
                st.link_button("Apply / View", url)
