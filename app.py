import streamlit as st
from auth import require_auth, logout
from db.models import init_db, get_all_jobs, get_user_profile

st.set_page_config(
    page_title="AcademicFinder",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

username = require_auth()
if username is None:
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.write(f"Logged in as **{username}**")
    if st.button("Logout"):
        logout()

# --- Home page ---
st.title("🎓 AcademicFinder")
st.markdown(
    "Find academic positions tailored to your research profile. "
    "Scrapes 8 academic job boards, matches positions to your skills "
    "and interests using AI, and ranks them by relevance and urgency."
)

st.divider()

col1, col2, col3 = st.columns(3)

profile = get_user_profile(username)
profile_complete = profile and profile.get("research_fields", "[]") != "[]"

with col1:
    st.metric("Profile", "✅ Complete" if profile_complete else "⚠️ Incomplete")

with col2:
    jobs = get_all_jobs()
    st.metric("Positions Found", len(jobs))

with col3:
    last_scan = st.session_state.get("last_scan_time", "Never")
    st.metric("Last Scan", last_scan)

st.divider()

st.markdown("### Getting Started")
st.markdown(
    "1. **Profile** — Fill in your research field, interests, and skills\n"
    "2. **Positions** — Click *Scan for Positions* to scrape 8 academic boards\n"
    "3. **Matches** — View positions ranked by match % and deadline urgency"
)
