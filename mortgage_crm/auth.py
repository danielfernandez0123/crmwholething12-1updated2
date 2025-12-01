"""
Authentication module for Mortgage CRM
Handles user login, registration, and session management

Seed users (Phase 3):
- admin / admin123 (admin)
- john_lo / loan123 (loan_officer)
- sarah_lo / loan456 (loan_officer)
"""

import bcrypt
import streamlit as st
from database import create_user, get_user_by_username, get_user_by_id, seed_users


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def ensure_seed_users():
    """Ensure seed users exist on first run"""
    return seed_users(hash_password)


def register_user(username: str, password: str, role: str = 'loan_officer',
                  full_name: str = None, email: str = None) -> bool:
    """Register a new user"""
    password_hash = hash_password(password)
    user_id = create_user(username, password_hash, role, full_name, email)
    return user_id is not None


def login_user(username: str, password: str) -> dict:
    """
    Attempt to log in a user

    Returns:
        User dict if successful, None otherwise
    """
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        return user
    return None


def init_session_state():
    """Initialize session state for authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'role' not in st.session_state:
        st.session_state.role = None


def is_authenticated() -> bool:
    """Check if user is authenticated"""
    init_session_state()
    return st.session_state.authenticated


def is_admin() -> bool:
    """Check if current user is admin"""
    init_session_state()
    return st.session_state.role == 'admin'


def get_current_user() -> dict:
    """Get the current logged-in user"""
    init_session_state()
    return st.session_state.user


def get_current_user_id() -> int:
    """Get the current logged-in user's ID"""
    init_session_state()
    return st.session_state.user_id


def get_current_role() -> str:
    """Get the current user's role"""
    init_session_state()
    return st.session_state.role


def set_user_session(user: dict):
    """Set user session after successful login"""
    st.session_state.authenticated = True
    st.session_state.user = user
    st.session_state.user_id = user['id']
    st.session_state.role = user.get('role', 'loan_officer')


def clear_user_session():
    """Clear user session (logout)"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.role = None


def login_form():
    """Display login form"""
    st.markdown("### 🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if username and password:
                user = login_user(username, password)
                if user:
                    set_user_session(user)
                    st.success(f"Welcome, {user.get('full_name', username)}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter username and password")


def registration_form():
    """Display registration form"""
    st.markdown("### 📝 Register New Account")

    with st.form("register_form"):
        username = st.text_input("Username")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register", use_container_width=True)

        if submit:
            if not username or not password:
                st.warning("Username and password are required")
            elif password != password_confirm:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                if register_user(username, password, full_name, email):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists")


def login_page():
    """Display login/registration page"""
    st.title("🏠 Mortgage CRM")
    st.markdown("### Loan Officer Client Management System")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_form()

    with tab2:
        registration_form()


def logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        clear_user_session()
        st.rerun()


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        init_session_state()
        if not is_authenticated():
            login_page()
            st.stop()
        return func(*args, **kwargs)
    return wrapper
