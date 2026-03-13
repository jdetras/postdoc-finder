import pandas as pd
import streamlit as st
from datetime import datetime

from auth import require_auth, logout
from db.models import init_db, get_user_profile, upsert_jobs, get_all_jobs
from scraper.agent import ScraperAgent
from scraper import keywords as kw_gen

init_db()
username = require_auth()
if username is None:
    st.stop()

with st.sidebar:
    st.write(f"Logged in as **{username}**")
    if st.button("Logout", key="logout_jobs"):
        logout()

st.title("🔎 Job Browser")

profile = get_user_profile(username)
if not profile or profile.get("research_fields", "[]") == "[]":
    st.warning("Please complete your profile first (Profile page) before scanning for jobs.")
    st.stop()

# Show generated search keywords
search_terms = kw_gen.generate(profile)
with st.expander("Search keywords (auto-generated from your profile)"):
    for term in search_terms:
        st.write(f"• {term}")

# --- Scan button ---
if st.button("🔍 Scan for Jobs", type="primary"):
    status_container = st.container()
    progress_placeholder = st.empty()

    results_by_site: dict[str, dict] = {}

    def status_callback(site_name: str, count: int, error: str | None):
        if error:
            results_by_site[site_name] = {"status": "❌", "count": 0, "error": error}
        else:
            results_by_site[site_name] = {"status": "✅", "count": count, "error": None}

        # Update progress display
        lines = []
        for name, info in results_by_site.items():
            if info["error"]:
                lines.append(f"{info['status']} **{name}**: error — {info['error']}")
            else:
                lines.append(f"{info['status']} **{name}**: found {info['count']} jobs")
        progress_placeholder.markdown("\n\n".join(lines))

    with st.spinner("Scanning 8 job boards... this may take a few minutes."):
        agent = ScraperAgent()
        all_jobs = agent.run_all(profile, status_callback=status_callback)

    if all_jobs:
        upsert_jobs(all_jobs)
        st.session_state["last_scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state["scanned_jobs"] = all_jobs
        st.success(f"Scan complete! Found {len(all_jobs)} unique positions.")
    else:
        st.warning("No jobs found. Try broadening your profile interests.")

st.divider()

# --- Display jobs ---
last_scan = st.session_state.get("last_scan_time")
if last_scan:
    st.caption(f"Last scanned: {last_scan}")

jobs = get_all_jobs()
if not jobs:
    st.info("No jobs in database yet. Click **Scan for Jobs** above to start searching.")
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

st.subheader(f"Jobs ({len(filtered)} of {len(df)})")

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
st.subheader("Job Details")
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
