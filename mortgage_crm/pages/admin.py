"""
Admin Panel Page (Phase 7)

Features:
- User Management (list, add, delete, reset password)
- Global Default Settings for ADL model
- Rate Settings (base rates)
- Pricing Grid (rate/points matrix for live rate calculation)
- Bulk Update Tool (apply defaults to clients, recalculate rates)
"""

import streamlit as st
import json
from datetime import datetime

from database import (
    get_all_users, create_user, delete_user, update_user_password,
    get_admin_settings, set_admin_setting,
    apply_defaults_to_all_clients, bulk_update_client_rates, get_all_clients
)
from auth import hash_password


def render_admin_panel(user_id: int, is_admin: bool):
    """Render the admin panel"""
    if not is_admin:
        st.warning("You don't have admin access.")
        return

    st.header("Admin Panel")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Management",
        "Global Defaults",
        "Rate Settings",
        "Pricing Grid",
        "Bulk Update Tool"
    ])

    with tab1:
        render_user_management()

    with tab2:
        render_global_defaults()

    with tab3:
        render_rate_settings()

    with tab4:
        render_pricing_grid()

    with tab5:
        render_bulk_tools()


def render_user_management():
    """User management section"""
    st.subheader("User Management")

    # View users section
    st.markdown("### Current Users")

    users = get_all_users()

    if users:
        for user in users:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])

            with col1:
                st.markdown(f"**{user.get('full_name') or user['username']}**")
                st.caption(user.get('email') or 'No email')

            with col2:
                st.markdown(f"Username: `{user['username']}`")
                st.caption(f"Created: {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}")

            with col3:
                if user['role'] == 'admin':
                    st.markdown(":red[Admin]")
                else:
                    st.markdown("Loan Officer")

            with col4:
                if st.button("Reset PW", key=f"reset_pw_{user['id']}", disabled=False):
                    st.session_state[f"reset_pw_user_{user['id']}"] = True

            with col5:
                # Can't delete admin users
                if st.button("Delete", key=f"del_user_{user['id']}", disabled=(user['role'] == 'admin')):
                    delete_user(user['id'])
                    st.success(f"Deleted user {user['username']}")
                    st.rerun()

            # Reset password form (shown when button clicked)
            if st.session_state.get(f"reset_pw_user_{user['id']}", False):
                with st.form(key=f"reset_form_{user['id']}"):
                    new_password = st.text_input("New Password", type="password", key=f"new_pw_{user['id']}")
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Save"):
                            if new_password and len(new_password) >= 6:
                                update_user_password(user['id'], hash_password(new_password))
                                st.success(f"Password reset for {user['username']}")
                                st.session_state[f"reset_pw_user_{user['id']}"] = False
                                st.rerun()
                            else:
                                st.error("Password must be at least 6 characters")
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f"reset_pw_user_{user['id']}"] = False
                            st.rerun()

            st.markdown("---")
    else:
        st.info("No users found")

    # Add new user section
    st.markdown("### Add New User")
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_username = st.text_input("Username *")
            new_fullname = st.text_input("Full Name")

        with col2:
            new_email = st.text_input("Email")
            new_role = st.selectbox("Role", options=["loan_officer", "admin"])

        new_password = st.text_input("Password *", type="password")

        if st.form_submit_button("Add User", type="primary"):
            if not new_username or not new_password:
                st.error("Username and password are required")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                user_id = create_user(
                    username=new_username,
                    password_hash=hash_password(new_password),
                    role=new_role,
                    full_name=new_fullname,
                    email=new_email
                )
                if user_id:
                    st.success(f"User {new_username} created!")
                    st.rerun()
                else:
                    st.error("Username already exists")


def render_global_defaults():
    """Global default settings for ADL model parameters"""
    st.subheader("Global Default Settings")
    st.markdown("These defaults are used when creating new clients and for bulk updates.")

    settings = get_admin_settings()

    with st.form("defaults_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Economic Parameters**")

            discount_rate = st.number_input(
                "Discount Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=float(settings.get('default_discount_rate', 0.05)) * 100,
                step=0.1,
                format="%.2f",
                help="Annual discount rate for NPV calculations"
            )

            volatility = st.number_input(
                "Rate Volatility (sigma)",
                min_value=0.0,
                max_value=0.1,
                value=float(settings.get('default_volatility', 0.0109)),
                step=0.0001,
                format="%.4f",
                help="Interest rate volatility parameter"
            )

            tax_rate = st.number_input(
                "Tax Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(settings.get('default_tax_rate', 0.28)) * 100,
                step=1.0,
                format="%.0f",
                help="Marginal tax rate for mortgage interest deduction"
            )

            inflation_rate = st.number_input(
                "Inflation Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=float(settings.get('default_inflation', 0.03)) * 100,
                step=0.1,
                format="%.1f",
                help="Expected annual inflation rate"
            )

        with col2:
            st.markdown("**Refinancing Costs**")

            fixed_cost = st.number_input(
                "Fixed Refinancing Cost ($)",
                min_value=0,
                max_value=20000,
                value=int(float(settings.get('default_fixed_cost', 2000))),
                step=100,
                help="Fixed costs like appraisal, title, etc."
            )

            points = st.number_input(
                "Points (%)",
                min_value=0.0,
                max_value=5.0,
                value=float(settings.get('default_points', 0.01)) * 100,
                step=0.125,
                format="%.3f",
                help="Loan origination points"
            )

            st.markdown("**Behavioral Parameters**")

            prob_moving = st.number_input(
                "Probability of Moving (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(settings.get('default_prob_moving', 0.10)) * 100,
                step=1.0,
                format="%.0f",
                help="Annual probability of selling/moving"
            )

        if st.form_submit_button("Save Defaults", type="primary", use_container_width=True):
            # Convert percentages back to decimals where needed
            set_admin_setting('default_discount_rate', str(discount_rate / 100))
            set_admin_setting('default_volatility', str(volatility))
            set_admin_setting('default_tax_rate', str(tax_rate / 100))
            set_admin_setting('default_inflation', str(inflation_rate / 100))
            set_admin_setting('default_fixed_cost', str(fixed_cost))
            set_admin_setting('default_points', str(points / 100))
            set_admin_setting('default_prob_moving', str(prob_moving / 100))
            st.success("Default settings saved!")
            st.rerun()

    # Current defaults summary
    st.markdown("---")
    st.markdown("### Current Defaults Summary")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"- **Discount Rate:** {float(settings.get('default_discount_rate', 0.05))*100:.2f}%")
        st.markdown(f"- **Volatility:** {float(settings.get('default_volatility', 0.0109)):.4f}")
        st.markdown(f"- **Tax Rate:** {float(settings.get('default_tax_rate', 0.28))*100:.0f}%")
        st.markdown(f"- **Inflation Rate:** {float(settings.get('default_inflation', 0.03))*100:.1f}%")

    with col2:
        st.markdown(f"- **Fixed Cost:** ${float(settings.get('default_fixed_cost', 2000)):,.0f}")
        st.markdown(f"- **Points:** {float(settings.get('default_points', 0.01))*100:.3f}%")
        st.markdown(f"- **Prob Moving:** {float(settings.get('default_prob_moving', 0.10))*100:.0f}%")


def render_rate_settings():
    """Base rate settings"""
    st.subheader("Rate Settings")
    st.markdown("Set the base par rates used for available rate calculations.")

    settings = get_admin_settings()

    with st.form("rate_settings_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Conventional (Fannie Mae/Freddie Mac)**")
            conv_rate = st.number_input(
                "Base Rate (%)",
                min_value=0.0,
                max_value=15.0,
                value=float(settings.get('base_rate_conventional', 6.5)),
                step=0.125,
                format="%.3f",
                key="conv_base_rate"
            )

            st.markdown("---")
            st.markdown("**2025 Loan Limits**")
            st.markdown("- Conforming: **$806,500**")
            st.markdown("- High-Balance: **$1,209,750**")
            st.markdown("[Lookup by County](https://singlefamily.fanniemae.com/originating-underwriting/loan-limits)")

        with col2:
            st.markdown("**FHA**")
            fha_rate = st.number_input(
                "Base Rate (%)",
                min_value=0.0,
                max_value=15.0,
                value=float(settings.get('base_rate_fha', 6.25)),
                step=0.125,
                format="%.3f",
                key="fha_base_rate"
            )

            st.markdown("---")
            st.markdown("**2025 Loan Limits**")
            st.markdown("- Floor: **$498,257**")
            st.markdown("- Ceiling: **$1,149,825**")
            st.markdown("[Lookup by County](https://entp.hud.gov/idapp/html/hicostlook.cfm)")

        if st.form_submit_button("Save Rate Settings", type="primary", use_container_width=True):
            set_admin_setting('base_rate_conventional', str(conv_rate))
            set_admin_setting('base_rate_fha', str(fha_rate))
            st.success("Rate settings saved!")
            st.rerun()

    # Display current settings
    st.markdown("---")
    st.info(f"**Current Rates:** Conventional {settings.get('base_rate_conventional', '6.500')}% | FHA {settings.get('base_rate_fha', '6.250')}%")


def render_bulk_tools():
    """Bulk update tools"""
    st.subheader("Bulk Update Tools")

    st.markdown("### Apply New Defaults to All Clients")
    st.markdown("""
    This will update the advanced parameters (discount rate, volatility, tax rate, etc.)
    for **all existing clients** to match the current global defaults.
    """)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Apply Defaults", type="secondary", use_container_width=True):
            with st.spinner("Applying defaults to all clients..."):
                count = apply_defaults_to_all_clients()
                st.success(f"Updated {count} clients with new defaults!")

    st.markdown("---")

    st.markdown("### Recalculate All Client Rates")
    st.markdown("""
    This will recalculate:
    - **Trigger Rate** (using ADL model with each client's parameters)
    - **Available Rate** (using current base rates and LLPA)
    - **Difference** and **Ready to Refinance** status

    Use this after changing base rates or after applying new defaults.
    """)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Recalculate All", type="primary", use_container_width=True):
            with st.spinner("Recalculating all client rates..."):
                count = bulk_update_client_rates()
                st.success(f"Recalculated rates for {count} clients!")

    st.markdown("---")

    # Show current system stats
    st.markdown("### System Statistics")
    clients = get_all_clients()
    users = get_all_users()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Clients", len(clients))

    with col2:
        ready_count = len([c for c in clients if c.get('ready_to_refinance')])
        st.metric("Ready to Refinance", ready_count)

    with col3:
        st.metric("Total Users", len(users))

    with col4:
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        st.metric("Admin Users", admin_count)

    # Client distribution by loan officer
    st.markdown("---")
    st.markdown("### Clients by Loan Officer")

    lo_counts = {}
    for client in clients:
        lo_name = client.get('loan_officer_name') or client.get('loan_officer_username') or 'Unassigned'
        lo_counts[lo_name] = lo_counts.get(lo_name, 0) + 1

    if lo_counts:
        for lo_name, count in sorted(lo_counts.items(), key=lambda x: -x[1]):
            ready = len([c for c in clients
                        if (c.get('loan_officer_name') or c.get('loan_officer_username') or 'Unassigned') == lo_name
                        and c.get('ready_to_refinance')])
            st.markdown(f"**{lo_name}:** {count} clients ({ready} ready)")
    else:
        st.info("No clients in system yet")


def render_pricing_grid():
    """Pricing grid - rate/points matrix for live rate calculations"""
    st.subheader("Pricing Grid")
    st.markdown("""
    Enter the available rates and their corresponding points cost.
    - **Positive points** = borrower pays (discount points to buy down rate)
    - **Negative points** = lender credit (rebate to borrower)
    - **0 points** = par rate (no cost/credit)
    """)

    settings = get_admin_settings()

    # Select loan type
    loan_type = st.radio(
        "Select Loan Type:",
        ["Conventional", "FHA"],
        horizontal=True,
        key="pricing_grid_loan_type"
    )

    grid_key = f"pricing_grid_{loan_type.lower()}"

    # Load existing grid
    existing_grid_json = settings.get(grid_key, '{}')
    try:
        existing_grid = json.loads(existing_grid_json)
    except:
        existing_grid = {}

    st.markdown("---")

    # Grid generation section
    st.markdown("### Generate New Grid")
    st.markdown("Automatically generate a grid based on par rate and range.")

    col1, col2, col3 = st.columns(3)

    with col1:
        base_key = 'base_rate_fha' if loan_type == 'FHA' else 'base_rate_conventional'
        par_rate = st.number_input(
            "Par Rate (%)",
            min_value=3.0,
            max_value=12.0,
            value=float(settings.get(base_key, 6.5)),
            step=0.125,
            format="%.3f",
            key="grid_par_rate"
        )

    with col2:
        eighths_above = st.number_input(
            "Eighths Above Par",
            min_value=0,
            max_value=24,
            value=8,
            help="Number of 0.125% increments above par rate"
        )

    with col3:
        eighths_below = st.number_input(
            "Eighths Below Par",
            min_value=0,
            max_value=24,
            value=8,
            help="Number of 0.125% increments below par rate"
        )

    col1, col2 = st.columns(2)

    with col1:
        points_per_eighth = st.number_input(
            "Points per 1/8% (typical: 0.25-0.375)",
            min_value=0.0,
            max_value=1.0,
            value=0.30,
            step=0.05,
            format="%.3f",
            help="How many points for each 0.125% rate change"
        )

    with col2:
        if st.button("Generate Grid", type="primary"):
            new_grid = {}

            # Generate rates above par (higher rate = lender credit/negative points)
            for i in range(eighths_above, 0, -1):
                rate = round(par_rate + i * 0.125, 3)
                points = round(-i * points_per_eighth, 3)  # Negative = credit
                new_grid[str(rate)] = points

            # Par rate
            new_grid[str(par_rate)] = 0.0

            # Generate rates below par (lower rate = borrower pays/positive points)
            for i in range(1, eighths_below + 1):
                rate = round(par_rate - i * 0.125, 3)
                if rate > 0:
                    points = round(i * points_per_eighth, 3)  # Positive = cost
                    new_grid[str(rate)] = points

            # Save to database
            set_admin_setting(grid_key, json.dumps(new_grid))
            st.success(f"Generated {len(new_grid)} rate levels for {loan_type}!")
            st.rerun()

    st.markdown("---")

    # Display and edit current grid
    st.markdown(f"### Current {loan_type} Pricing Grid")

    if not existing_grid:
        st.warning("No pricing grid configured. Use 'Generate Grid' above or add rates manually below.")
    else:
        # Sort by rate descending
        sorted_rates = sorted(existing_grid.keys(), key=lambda x: float(x), reverse=True)

        # Display in columns
        st.markdown("**Rate** → **Points** (negative = credit, positive = cost)")

        # Create editable display
        cols_per_row = 4
        for i in range(0, len(sorted_rates), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(sorted_rates):
                    rate_str = sorted_rates[i + j]
                    rate_val = float(rate_str)
                    points_val = existing_grid[rate_str]

                    # Determine if this is par rate
                    base_key = 'base_rate_fha' if loan_type == 'FHA' else 'base_rate_conventional'
                    current_par = float(settings.get(base_key, 6.5))
                    is_par = abs(rate_val - current_par) < 0.001

                    # Color code
                    if points_val < 0:
                        color = "green"
                        label = "credit"
                    elif points_val > 0:
                        color = "red"
                        label = "cost"
                    else:
                        color = "blue"
                        label = "PAR"

                    with col:
                        if is_par:
                            st.markdown(f"**{rate_val:.3f}%** → :{color}[{points_val:+.3f} pts] (PAR)")
                        else:
                            st.markdown(f"**{rate_val:.3f}%** → :{color}[{points_val:+.3f} pts]")

    st.markdown("---")

    # Manual entry section
    st.markdown("### Add/Edit Individual Rate")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        new_rate = st.number_input(
            "Rate (%)",
            min_value=3.0,
            max_value=12.0,
            value=6.5,
            step=0.125,
            format="%.3f",
            key="manual_rate_input"
        )

    with col2:
        new_points = st.number_input(
            "Points",
            min_value=-5.0,
            max_value=5.0,
            value=0.0,
            step=0.125,
            format="%.3f",
            key="manual_points_input",
            help="Negative = lender credit, Positive = borrower cost"
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add/Update", use_container_width=True):
            existing_grid[str(new_rate)] = new_points
            set_admin_setting(grid_key, json.dumps(existing_grid))
            st.success(f"Added {new_rate:.3f}% at {new_points:+.3f} points")
            st.rerun()

    # Delete rate
    if existing_grid:
        st.markdown("### Remove Rate")
        col1, col2 = st.columns([3, 1])

        with col1:
            sorted_rates = sorted(existing_grid.keys(), key=lambda x: float(x), reverse=True)
            rate_to_delete = st.selectbox(
                "Select rate to remove:",
                sorted_rates,
                format_func=lambda x: f"{float(x):.3f}% ({existing_grid[x]:+.3f} pts)"
            )

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Remove", type="secondary", use_container_width=True):
                if rate_to_delete in existing_grid:
                    del existing_grid[rate_to_delete]
                    set_admin_setting(grid_key, json.dumps(existing_grid))
                    st.success(f"Removed {rate_to_delete}%")
                    st.rerun()

    # Clear grid button
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col3:
        if st.button("Clear All", type="secondary", use_container_width=True):
            set_admin_setting(grid_key, '{}')
            st.warning(f"Cleared {loan_type} pricing grid")
            st.rerun()

    # Export/Import section
    st.markdown("---")
    st.markdown("### Export/Import Grid")

    col1, col2 = st.columns(2)

    with col1:
        if existing_grid:
            # Create CSV format
            csv_data = "Rate,Points\n"
            for rate in sorted(existing_grid.keys(), key=lambda x: float(x), reverse=True):
                csv_data += f"{rate},{existing_grid[rate]}\n"

            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"pricing_grid_{loan_type.lower()}.csv",
                mime="text/csv"
            )

    with col2:
        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=['csv'],
            key=f"upload_grid_{loan_type}",
            help="CSV with columns: Rate,Points"
        )

        if uploaded_file is not None:
            try:
                import pandas as pd
                df = pd.read_csv(uploaded_file)
                new_grid = {}
                for _, row in df.iterrows():
                    rate = str(round(float(row['Rate']), 3))
                    points = round(float(row['Points']), 3)
                    new_grid[rate] = points

                set_admin_setting(grid_key, json.dumps(new_grid))
                st.success(f"Imported {len(new_grid)} rates!")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing CSV: {e}")
