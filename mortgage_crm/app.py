"""
Mortgage Refinancing CRM for Loan Officers
Main entry point with authentication and page routing

Combines:
1. Optimal Refinancing Calculator (ADL/NBER model)
2. Live Rate Calculator (with LLPA adjustments)

The goal: Help loan officers track clients and automatically flag when someone is ready to refinance.

For each client:
- trigger_rate = current_mortgage_rate - optimal_rate_drop (from ADL model)
- available_rate = live rate they'd qualify for today (with LLPA adjustments)
- difference = trigger_rate - available_rate
- If difference > 0: Client is ready to refinance NOW
"""

import streamlit as st
from database import init_database
from auth import (
    init_session_state, is_authenticated, get_current_user,
    get_current_user_id, get_current_role, is_admin as check_is_admin,
    login_page, logout_button, ensure_seed_users
)
from pages.dashboard import render_dashboard, render_client_detail
from pages.add_client import render_add_client, render_edit_client, render_delete_client
from pages.calculator import render_calculator
from pages.other_tools import render_other_tools
from pages.other_other_tools import render_other_other_tools
from pages.admin import render_admin_panel

# Page configuration
st.set_page_config(
    page_title="Mortgage CRM",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1f4788;
        margin-bottom: 1rem;
    }
    .status-ready {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .status-waiting {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .status-pending {
        background-color: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 1rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def seed_initial_data():
    """Seed initial users and data if needed"""
    count = ensure_seed_users()
    if count > 0:
        st.info(f"Created {count} seed users. Login with admin/admin123, john_lo/loan123, or sarah_lo/loan456")


def main():
    """Main application entry point"""
    # Initialize database
    init_database()

    # Seed initial users if needed
    seed_initial_data()

    # Initialize session state
    init_session_state()

    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

    # Check authentication
    if not is_authenticated():
        login_page()
        return

    # Get current user info
    user = get_current_user()
    user_id = get_current_user_id()
    role = get_current_role()
    is_admin = check_is_admin()

    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### 🏠 Mortgage CRM")
        st.markdown(f"Welcome, **{user.get('full_name', user.get('username'))}**")

        st.markdown("---")

        # Navigation buttons
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()

        if st.button("➕ Add Client", use_container_width=True):
            st.session_state.page = 'add_client'
            st.rerun()

        if st.button("🧮 Calculator", use_container_width=True):
            st.session_state.page = 'calculator'
            st.rerun()

        if st.button("🔧 Other Tools", use_container_width=True):
            st.session_state.page = 'other_tools'
            st.rerun()

        if st.button("🏠 Other Other Tools", use_container_width=True):
            st.session_state.page = 'other_other_tools'
            st.rerun()

        if is_admin:
            st.markdown("---")
            if st.button("⚙️ Admin Panel", use_container_width=True):
                st.session_state.page = 'admin'
                st.rerun()

        st.markdown("---")
        logout_button()

    # Main content area - route to appropriate page
    page = st.session_state.get('page', 'dashboard')

    if page == 'dashboard':
        render_dashboard(user_id, role)

    elif page == 'view_client':
        client_id = st.session_state.get('selected_client_id')
        if client_id:
            render_client_detail(client_id)
        else:
            st.session_state.page = 'dashboard'
            st.rerun()

    elif page == 'add_client':
        render_add_client(user_id)

    elif page == 'edit_client':
        client_id = st.session_state.get('edit_client_id')
        if client_id:
            render_edit_client(user_id, client_id)
        else:
            st.session_state.page = 'dashboard'
            st.rerun()

    elif page == 'delete_client':
        client_id = st.session_state.get('delete_client_id')
        if client_id:
            render_delete_client(client_id)
        else:
            st.session_state.page = 'dashboard'
            st.rerun()

    elif page == 'calculator':
        render_calculator()

    elif page == 'other_tools':
        render_other_tools(user_id)

    elif page == 'other_other_tools':
        render_other_other_tools(user_id)

    elif page == 'admin':
        if is_admin:
            render_admin_panel(user_id, is_admin)
        else:
            st.warning("Admin access required")
            st.session_state.page = 'dashboard'
            st.rerun()

    else:
        st.session_state.page = 'dashboard'
        st.rerun()


if __name__ == "__main__":
    main()
