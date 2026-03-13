import bcrypt
import streamlit as st
from db.models import register_user, get_user_credentials, get_user_profile, init_db


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


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
