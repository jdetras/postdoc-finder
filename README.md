# PostdocFinder

A multi-user Streamlit app that scrapes 8 academic job boards and matches postdoc positions to your research profile using TF-IDF cosine similarity.

## Features

- **Multi-user auth** — Register/login with hashed passwords
- **Generalized profiles** — 20+ research fields, free-form interests & skills, CV upload
- **8 job boards** — EURAXESS, AcademicTransfer, CSIRO, IPK Gatersleben, JIC, EMBL-EBI, jobs.ac.uk, AcademicPositions
- **Dynamic search keywords** — Auto-generated from your profile (not hardcoded)
- **TF-IDF matching** — Cosine similarity ranking with urgency scoring
- **Urgency color-coding** — Red (<7 days), orange (<30 days), green (30+ days)
- **CSV export** — Download your ranked matches

## Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd postdoc-finder

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Usage

1. **Register** an account on the login page
2. **Profile** — Fill in your research fields, interests, skills, and optionally upload your CV
3. **Jobs** — Click "Scan for Jobs" to scrape all 8 boards with your personalized search keywords
4. **Matches** — View positions ranked by match % and deadline urgency, export to CSV

## Tech Stack

- **Streamlit** — Frontend
- **requests + BeautifulSoup4** — Web scraping (no Playwright)
- **scikit-learn** — TF-IDF cosine similarity
- **SQLite** — Local database
- **pdfplumber** — CV text extraction
- **rapidfuzz** — Fuzzy deduplication
- **bcrypt** — Password hashing

## Deployment

Deploy for free on [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push to GitHub
2. Connect repo on Streamlit Cloud
3. Set `app.py` as the main file
4. Deploy — your app will be at `https://<app-name>.streamlit.app`

> **Note:** SQLite data is ephemeral on Streamlit Cloud (reset on app restart). Scrape results are regenerated each time you click "Scan for Jobs".

## Cost

$0/month — no external databases, APIs, or services required.
