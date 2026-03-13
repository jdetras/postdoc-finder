import logging

import bcrypt
import streamlit as st
from db.models import register_user, get_user_credentials, get_user_profile, init_db

logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _google_sso_available() -> bool:
    """Check if Google OAuth secrets are configured."""
    try:
        g = st.secrets.get("google")
        return bool(g and g.get("client_id") and g.get("client_secret"))
    except Exception:
        return False


def _google_login():
    """Render Google SSO button using standard authorization code flow."""
    import os
    from requests_oauthlib import OAuth2Session

    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    _SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    try:
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        redirect_uri = st.secrets["google"].get("redirect_uri", "http://localhost:8501")

        # Allow insecure transport only for local dev (http://localhost)
        if redirect_uri.startswith("http://localhost"):
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        else:
            os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)

        params = st.query_params

        if "code" in params:
            # --- Handle OAuth callback ---
            code = params["code"]
            oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri)
            oauth.fetch_token(
                _TOKEN_URL,
                code=code,
                client_secret=client_secret,
            )

            userinfo = oauth.get(_USERINFO_URL).json()
            email = userinfo.get("email", "")

            if email:
                existing = get_user_credentials()
                if email not in existing:
                    register_user(email, "__google_sso__")
                st.session_state["authenticated"] = True
                st.session_state["username"] = email
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Could not retrieve email from Google account.")
        else:
            # --- Build authorization URL and render button ---
            oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=_SCOPES)
            auth_url, _ = oauth.authorization_url(
                _AUTH_URL,
                access_type="offline",
                prompt="select_account",
            )

            st.markdown(
                f"""<div style="display:flex;justify-content:center;margin:8px 0">
                <a href="{auth_url}" target="_self"
                   style="background:#4285f4;color:#fff;padding:10px 16px;
                          border-radius:4px;text-decoration:none;font-size:15px;
                          display:flex;align-items:center;gap:10px;">
                  <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
                       width="20" height="20"
                       style="background:#fff;border-radius:2px;padding:2px">
                  Sign in with Google
                </a></div>""",
                unsafe_allow_html=True,
            )

    except Exception as exc:
        logger.error("Google SSO error: %s", exc)
        st.error(f"Google sign-in failed: {exc}")


def _login_form():
    """Render login form. Returns True if authenticated."""
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not username or not password:
            st.error("Please fill in all fields.")
            return False
        creds = get_user_credentials()
        if username not in creds:
            st.error("Username not found. Please register first.")
            return False
        if not _verify_password(password, creds[username]):
            st.error("Incorrect password.")
            return False
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.rerun()

    return False


def _register_form():
    """Render registration form."""
    st.subheader("Register")
    with st.form("register_form"):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        password_confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register")

    if submitted:
        if not username or not password:
            st.error("Please fill in all fields.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if password != password_confirm:
            st.error("Passwords do not match.")
            return
        creds = get_user_credentials()
        if username in creds:
            st.error("Username already taken.")
            return
        register_user(username, _hash_password(password))
        st.success("Registration successful! Please log in.")


def require_auth() -> str | None:
    """Gate for all pages. Returns username if authenticated, else shows login/register."""
    init_db()

    if st.session_state.get("authenticated"):
        return st.session_state["username"]

    # Show Google SSO if configured
    if _google_sso_available():
        st.markdown("#### Sign in with Google")
        _google_login()
        st.divider()

    tab_login, tab_register = st.tabs(["Login", "Register"])
    with tab_login:
        _login_form()
    with tab_register:
        _register_form()

    return None


def logout():
    """Clear session and rerun."""
    for key in ["authenticated", "username"]:
        st.session_state.pop(key, None)
    st.rerun()
