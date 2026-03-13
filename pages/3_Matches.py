import json
import pandas as pd
import streamlit as st

from auth import require_auth, logout
from db.models import init_db, get_user_profile, get_all_jobs
from matcher.engine import rank_jobs

init_db()
username = require_auth()
if username is None:
    st.stop()

with st.sidebar:
    st.write(f"Logged in as **{username}**")
    if st.button("Logout", key="logout_matches"):
        logout()

st.title("🏆 Matched Positions")

profile = get_user_profile(username)
if not profile or profile.get("research_fields", "[]") == "[]":
    st.warning("Please complete your profile first (Profile page).")
    st.stop()

jobs = get_all_jobs()
if not jobs:
    st.info("No jobs in database. Go to the **Jobs** page and click **Scan for Jobs** first.")
    st.stop()

# Rank jobs against profile
with st.spinner("Computing matches..."):
    ranked = rank_jobs(profile, jobs)

if not ranked:
    st.info("No matches found.")
    st.stop()

# --- Filter by minimum match % ---
min_match = st.slider("Minimum match %", 0, 100, 0, step=5)
ranked = [j for j in ranked if j.get("match_pct", 0) >= min_match]

st.subheader(f"Top Matches ({len(ranked)} positions)")

# --- Summary table ---
table_data = []
for j in ranked:
    days = j.get("days_until_deadline")
    if days is not None and days < 0:
        urgency_label = "⬛ Expired"
    elif days is not None and days <= 7:
        urgency_label = "🔴 < 7 days"
    elif days is not None and days <= 30:
        urgency_label = "🟠 < 30 days"
    elif days is not None:
        urgency_label = "🟢 30+ days"
    else:
        urgency_label = "⚪ Unknown"

    table_data.append({
        "Rank": len(table_data) + 1,
        "Title": j.get("title", ""),
        "Institution": j.get("institution", ""),
        "Match %": j.get("match_pct", 0),
        "Urgency": urgency_label,
        "Days Left": days if days is not None else "—",
        "Location": j.get("location", ""),
        "Source": j.get("source", ""),
        "URL": j.get("url", ""),
    })

df = pd.DataFrame(table_data)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn("Link", display_text="View"),
        "Match %": st.column_config.ProgressColumn("Match %", min_value=0, max_value=100),
    },
)

# --- Export CSV ---
csv = df.to_csv(index=False)
st.download_button("📥 Export to CSV", csv, "postdoc_matches.csv", "text/csv")

st.divider()

# --- Detailed cards ---
st.subheader("Position Details")
for j in ranked[:50]:
    match_pct = j.get("match_pct", 0)
    days = j.get("days_until_deadline")
    title = j.get("title", "Untitled")
    inst = j.get("institution", "")

    # Color-coded urgency badge
    if days is not None and days < 0:
        badge = "⬛ Expired"
    elif days is not None and days <= 7:
        badge = "🔴 Urgent"
    elif days is not None and days <= 30:
        badge = "🟠 Soon"
    elif days is not None:
        badge = "🟢 Open"
    else:
        badge = "⚪ Unknown"

    header = f"{badge} **{title}** — {inst} | Match: {match_pct}%"
    with st.expander(header):
        cols = st.columns([2, 1])
        with cols[0]:
            desc = j.get("description", "")
            if desc:
                st.write(desc[:2000])
            else:
                st.write("*No description available*")

            keywords = j.get("matched_keywords", [])
            if keywords:
                st.caption(f"Matched keywords: {', '.join(keywords)}")

        with cols[1]:
            st.metric("Match", f"{match_pct}%")
            st.write(f"**Rank Score:** {j.get('rank_score', 0)}")
            st.write(f"**Deadline:** {j.get('deadline', 'N/A')}")
            if days is not None:
                st.write(f"**Days remaining:** {days}")
            st.write(f"**Location:** {j.get('location', '')}")
            st.write(f"**Source:** {j.get('source', '')}")
            st.write(f"**Salary:** {j.get('salary_info', 'N/A')}")
            st.write(f"**Duration:** {j.get('duration', 'N/A')}")
            url = j.get("url", "")
            if url:
                st.link_button("Apply / View", url)
