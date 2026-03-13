# AcademicFinder

A multi-user Streamlit app that scrapes 8 academic job boards and matches academic positions to your research profile using TF-IDF cosine similarity.

## Features

- **Multi-user auth** — Register/login with hashed passwords, optional Google SSO
- **Generalized profiles** — 20+ research fields, degree background, fellowship programs, CV upload
- **8 job boards** — EURAXESS, AcademicTransfer, CSIRO, IPK Gatersleben, JIC, EMBL-EBI, jobs.ac.uk, AcademicPositions
- **Dynamic search keywords** — Auto-generated from your profile (not hardcoded)
- **Background scanning** — Navigate between pages while jobs are being scraped
- **Email notifications** — Get notified when a scan completes (optional, Gmail SMTP)
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

1. **Register** an account on the login page (or sign in with Google)
2. **Profile** — Fill in your research fields, degrees, interests, skills, and optionally upload your CV
3. **Jobs** — Click "Scan for Jobs" to scrape all 8 boards with your personalized search keywords
4. **Matches** — View positions ranked by match % and deadline urgency, export to CSV

## Optional Configuration

Copy `.streamlit/secrets.toml` and fill in your credentials:

### Google SSO

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID (Web application)
3. Set authorized redirect URI to your app URL (e.g., `http://localhost:8501`)
4. Add `client_id` and `client_secret` to `.streamlit/secrets.toml`

### Email Notifications

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Generate an app password for "Mail"
3. Add your Gmail address and app password to `.streamlit/secrets.toml`

Both features are optional — the app works without them.

## Tech Stack

- **Streamlit** — Frontend
- **requests + BeautifulSoup4** — Web scraping (no Playwright)
- **scikit-learn** — TF-IDF cosine similarity
- **SQLite** — Local database
- **pdfplumber** — CV text extraction
- **rapidfuzz** — Fuzzy deduplication
- **bcrypt** — Password hashing
- **streamlit-google-auth** — Google OAuth (optional)

## Deployment

Deploy for free on [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push to GitHub
2. Connect repo on Streamlit Cloud
3. Set `app.py` as the main file
4. Deploy — your app will be at `https://<app-name>.streamlit.app`

> **Note:** SQLite data is ephemeral on Streamlit Cloud (reset on app restart). Scrape results are regenerated each time you click "Scan for Jobs".

## Cost

$0/month — no external databases, APIs, or services required.
