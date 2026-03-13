import json
import streamlit as st
import pdfplumber
from auth import require_auth, logout
from db.models import init_db, upsert_user_profile, get_user_profile

init_db()
username = require_auth()
if username is None:
    st.stop()

with st.sidebar:
    st.write(f"Logged in as **{username}**")
    if st.button("Logout", key="logout_profile"):
        logout()

st.title("👤 Research Profile")
st.markdown("Fill out your research profile so we can find the most relevant academic positions for you.")

RESEARCH_FIELDS = [
    "Computational Biology", "Bioinformatics", "ML/AI", "Genomics",
    "Plant Sciences", "Neuroscience", "Physics", "Astrophysics",
    "Chemistry", "Biochemistry", "Ecology", "Environmental Science",
    "Biomedical Sciences", "Engineering", "Computer Science",
    "Mathematics", "Statistics", "Economics", "Social Sciences",
    "Psychology", "Materials Science", "Earth Sciences",
    "Clinical Research", "Pharmacology", "Other",
]

POSITION_TYPES = [
    "Postdoc", "PhD", "Research Scientist", "Research Assistant",
    "Internship", "Lecturer", "Assistant Professor", "Associate Professor",
    "Professor", "Fellowship", "Other",
]

LOCATIONS = [
    "US", "Europe", "UK", "Canada", "Asia", "Australia/NZ", "No preference",
]

DEGREE_LEVELS = [
    "BS / Bachelor's",
    "MS / Master's",
    "PhD / Doctorate",
    "MD",
    "Other",
]

FELLOWSHIP_PROGRAMS = [
    "MSCA Marie Curie Postdoctoral Fellowship",
    "EMBO Postdoctoral Fellowship",
    "HFSP Postdoctoral Fellowship",
    "Alexander von Humboldt Fellowship",
    "Newton International Fellowship (Royal Society)",
    "Swiss NSF Postdoc.Mobility",
    "JSPS Postdoctoral Fellowship (Japan)",
    "Fulbright Postdoctoral Fellowship",
    "DFG Walter Benjamin Programme",
    "ARC DECRA (Australia)",
    "ERC Starting Grant",
    "Branco Weiss Fellowship",
    "Life Sciences Research Foundation (LSRF)",
    "Helen Hay Whitney Fellowship",
    "Damon Runyon Fellowship",
    "Wellcome Trust Early Career Award",
    "HHMI Hanna Gray Fellowship",
    "Other fellowship",
]

# Load existing profile
existing = get_user_profile(username) or {}
existing_fields = []
if existing.get("research_fields"):
    try:
        existing_fields = json.loads(existing["research_fields"])
    except (json.JSONDecodeError, TypeError):
        existing_fields = []

with st.form("profile_form"):
    name = st.text_input("Full name", value=existing.get("name", ""))
    email = st.text_input("Email", value=existing.get("email", ""))

    research_fields = st.multiselect(
        "Research fields",
        options=RESEARCH_FIELDS,
        default=[f for f in existing_fields if f in RESEARCH_FIELDS],
        help="Select all that apply",
    )

    existing_pos_types = []
    if existing.get("position_types"):
        try:
            existing_pos_types = json.loads(existing["position_types"])
        except (json.JSONDecodeError, TypeError):
            existing_pos_types = []

    position_types = st.multiselect(
        "Position type / level",
        options=POSITION_TYPES,
        default=[p for p in existing_pos_types if p in POSITION_TYPES] or ["Postdoc"],
        help="What level of positions are you looking for?",
    )

    existing_fellowships = []
    if existing.get("fellowship_programs"):
        try:
            existing_fellowships = json.loads(existing["fellowship_programs"])
        except (json.JSONDecodeError, TypeError):
            existing_fellowships = []

    fellowship_programs = st.multiselect(
        "Fellowship programs to search (optional)",
        options=FELLOWSHIP_PROGRAMS,
        default=[f for f in existing_fellowships if f in FELLOWSHIP_PROGRAMS],
        help="Select specific fellowship/funding programs to include in your search",
    )

    interests = st.text_area(
        "Research interests",
        value=existing.get("interests", ""),
        placeholder="e.g., deep learning for protein structure prediction, single-cell transcriptomics, CRISPR gene editing",
        help="Describe your specific research interests (free-form)",
    )

    location_pref_existing = []
    if existing.get("location_pref"):
        try:
            location_pref_existing = json.loads(existing["location_pref"])
        except (json.JSONDecodeError, TypeError):
            location_pref_existing = []

    location_pref = st.multiselect(
        "Preferred locations",
        options=LOCATIONS,
        default=[l for l in location_pref_existing if l in LOCATIONS],
    )

    skills = st.text_input(
        "Key technical skills",
        value=existing.get("skills", ""),
        placeholder="e.g., Python, R, PyTorch, Nextflow, HPC, Docker",
    )

    # --- Degrees completed with optional graduation dates ---
    existing_degrees = {}
    if existing.get("degrees"):
        try:
            existing_degrees = json.loads(existing["degrees"])
        except (json.JSONDecodeError, TypeError):
            existing_degrees = {}

    completed_degrees = st.multiselect(
        "Degrees completed",
        options=DEGREE_LEVELS,
        default=[d for d in existing_degrees if d in DEGREE_LEVELS],
        help="Select degrees you have earned",
    )

    degree_dates = {}
    for deg in completed_degrees:
        date_val = st.text_input(
            f"Graduation date — {deg} (optional)",
            value=existing_degrees.get(deg, ""),
            placeholder="e.g., May 2024",
            key=f"degree_date_{deg}",
        )
        degree_dates[deg] = date_val

    cv_file = st.file_uploader("Upload CV (PDF)", type=["pdf"])

    submitted = st.form_submit_button("Save Profile", type="primary")

if submitted:
    cv_text = existing.get("cv_text", "")
    if cv_file is not None:
        try:
            with pdfplumber.open(cv_file) as pdf:
                pages_text = [p.extract_text() or "" for p in pdf.pages]
                cv_text = "\n".join(pages_text)
        except Exception as e:
            st.warning(f"Could not extract text from CV: {e}")

    upsert_user_profile(
        username,
        name=name,
        email=email,
        research_fields=json.dumps(research_fields),
        position_types=json.dumps(position_types),
        fellowship_programs=json.dumps(fellowship_programs),
        interests=interests,
        skills=skills,
        location_pref=json.dumps(location_pref),
        degrees=json.dumps(degree_dates),
        cv_text=cv_text,
    )

    st.success("Profile saved!")

    # Show summary
    st.divider()
    st.subheader("Profile Summary")
    st.write(f"**Name:** {name}")
    st.write(f"**Email:** {email}")
    st.write(f"**Fields:** {', '.join(research_fields)}")
    st.write(f"**Position types:** {', '.join(position_types)}")
    if fellowship_programs:
        st.write(f"**Fellowship programs:** {', '.join(fellowship_programs)}")
    st.write(f"**Interests:** {interests}")
    st.write(f"**Skills:** {skills}")
    st.write(f"**Location preference:** {', '.join(location_pref)}")
    if degree_dates:
        deg_parts = []
        for deg, dt in degree_dates.items():
            deg_parts.append(f"{deg} ({dt})" if dt else deg)
        st.write(f"**Degrees:** {', '.join(deg_parts)}")
    if cv_text:
        st.write(f"**CV:** {len(cv_text)} characters extracted")
