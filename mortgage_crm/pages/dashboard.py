"""
Dashboard Page - Main view for loan officers (Phase 4)

Shows a table of all clients with columns:
- Name
- Current Rate
- Trigger Rate (current - optimal drop)
- Available Rate (live)
- Difference (trigger - available, color-coded)
- Last Updated
- Actions (Edit button)

Features:
- Filter toggle: "Show only ready to refinance"
- Sort by difference (highest first)
- Search by name
- "Refresh All Rates" button
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from database import (
    get_clients_by_user, get_client_by_id, bulk_update_client_rates,
    get_admin_settings, log_rate_check, get_rate_check_history, get_contact_history
)


def render_dashboard(user_id: int, role: str):
    """Render the main dashboard"""
    settings = get_admin_settings()

    st.header("Client Dashboard")

    # Top controls row
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        search = st.text_input("Search by name", placeholder="Enter name...", label_visibility="collapsed")

    with col2:
        show_ready_only = st.checkbox("Show only ready to refinance", value=False)

    with col3:
        base_conv = settings.get('base_rate_conventional', '6.500')
        base_fha = settings.get('base_rate_fha', '6.250')
        st.info(f"Base Rates: Conv {base_conv}% | FHA {base_fha}%")

    with col4:
        if st.button("Refresh All Rates", type="primary", use_container_width=True):
            with st.spinner("Recalculating all client rates..."):
                count = bulk_update_client_rates(user_id)
                st.success(f"Updated {count} clients")
                st.rerun()

    st.markdown("---")

    # Get clients
    clients = get_clients_by_user(user_id, ready_only=show_ready_only, search=search if search else None)

    if not clients:
        if show_ready_only:
            st.info("No clients are ready to refinance yet.")
        else:
            st.warning("No clients found. Add your first client to get started!")

        if st.button("Add New Client", type="primary"):
            st.session_state.page = "add_client"
            st.rerun()
        return

    # Summary metrics
    total_clients = len(clients)
    ready_clients = len([c for c in clients if c.get('ready_to_refinance')])
    total_balance = sum(c.get('current_mortgage_balance', 0) or 0 for c in clients)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Clients", total_clients)
    with col2:
        st.metric("Ready to Refinance", ready_clients)
    with col3:
        st.metric("Total Mortgage Balance", f"${total_balance:,.0f}")
    with col4:
        ready_list = [c for c in clients if c.get('difference') is not None and c.get('difference', 0) > 0]
        if ready_list:
            avg_diff = sum(c.get('difference', 0) * 100 for c in ready_list) / len(ready_list)
            st.metric("Avg Savings (Ready)", f"{avg_diff:.2f}%")
        else:
            st.metric("Avg Savings (Ready)", "N/A")

    st.markdown("---")

    # Build data for table display
    table_data = []
    for c in clients:
        current_rate = c.get('current_mortgage_rate')
        trigger_rate = c.get('trigger_rate')
        available_rate = c.get('available_rate')
        difference = c.get('difference')

        # Determine status
        if difference is not None and difference > 0.005:  # > 0.5%
            status = "READY NOW!"
            status_color = "🟢"
        elif difference is not None and difference > 0:
            status = "Ready"
            status_color = "🟡"
        elif difference is not None:
            status = "Wait"
            status_color = "🔴"
        else:
            status = "Needs Calc"
            status_color = "⚪"

        table_data.append({
            'id': c['id'],
            'Status': status_color,
            'Name': f"{c['first_name']} {c['last_name']}",
            'Current Rate': f"{current_rate*100:.3f}%" if current_rate else "N/A",
            'Trigger Rate': f"{trigger_rate*100:.3f}%" if trigger_rate else "N/A",
            'Available Rate': f"{available_rate*100:.3f}%" if available_rate else "N/A",
            'Difference': f"{difference*100:+.3f}%" if difference else "N/A",
            'Balance': f"${c.get('current_mortgage_balance', 0):,.0f}",
            'Last Updated': c.get('updated_at', '')[:10] if c.get('updated_at') else 'N/A',
            'status_value': status,
            'difference_value': difference or -999
        })

    # Create DataFrame
    df = pd.DataFrame(table_data)

    # Display as interactive table
    st.subheader(f"Client List ({len(table_data)} clients)")

    # Column config for display
    column_config = {
        'id': None,  # Hide
        'status_value': None,  # Hide
        'difference_value': None,  # Hide
        'Status': st.column_config.TextColumn('', width='small'),
        'Name': st.column_config.TextColumn('Name', width='medium'),
        'Current Rate': st.column_config.TextColumn('Current', width='small'),
        'Trigger Rate': st.column_config.TextColumn('Trigger', width='small'),
        'Available Rate': st.column_config.TextColumn('Available', width='small'),
        'Difference': st.column_config.TextColumn('Diff', width='small'),
        'Balance': st.column_config.TextColumn('Balance', width='small'),
        'Last Updated': st.column_config.TextColumn('Updated', width='small'),
    }

    # Use selectbox for row selection
    selected_idx = st.selectbox(
        "Select a client to view/edit:",
        options=range(len(table_data)),
        format_func=lambda i: f"{table_data[i]['Name']} - {table_data[i]['status_value']}",
        key="client_select"
    )

    # Show the table
    st.dataframe(
        df[['Status', 'Name', 'Current Rate', 'Trigger Rate', 'Available Rate', 'Difference', 'Balance', 'Last Updated']],
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # Action buttons for selected client
    if selected_idx is not None and len(table_data) > 0:
        selected_client = table_data[selected_idx]
        client_id = selected_client['id']

        st.markdown(f"### Selected: {selected_client['Name']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("View Details", use_container_width=True):
                st.session_state.selected_client_id = client_id
                st.session_state.page = "view_client"
                st.rerun()
        with col2:
            if st.button("Edit Client", use_container_width=True):
                st.session_state.edit_client_id = client_id
                st.session_state.page = "edit_client"
                st.rerun()
        with col3:
            if st.button("Delete", use_container_width=True):
                st.session_state.delete_client_id = client_id
                st.session_state.page = "delete_client"
                st.rerun()


def render_client_detail(client_id: int):
    """Render detailed client view"""
    client = get_client_by_id(client_id)
    if not client:
        st.error("Client not found")
        return

    # Back button
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.header(f"{client['first_name']} {client['last_name']}")

    # Status badge
    difference = client.get('difference')
    if difference is not None and difference > 0.005:
        st.success("🟢 READY TO REFINANCE NOW!")
    elif difference is not None and difference > 0:
        st.warning("🟡 Ready to Refinance")
    elif difference is not None:
        st.info(f"🔴 Need rates to drop {-difference*100:.2f}% more")
    else:
        st.info("⚪ Rates not calculated yet")

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Overview", "Rate History", "Contact Log"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Contact Information")
            st.markdown(f"**Email:** {client.get('email') or 'N/A'}")
            st.markdown(f"**Phone:** {client.get('phone') or 'N/A'}")
            st.markdown(f"**State:** {client.get('state') or 'N/A'}")

            st.subheader("Current Mortgage")
            st.markdown(f"**Loan Type:** {client.get('loan_type', 'Conventional')}")
            st.markdown(f"**Current Rate:** {client.get('current_mortgage_rate', 0)*100:.3f}%")
            st.markdown(f"**Balance:** ${client.get('current_mortgage_balance', 0):,.0f}")
            st.markdown(f"**Years Remaining:** {client.get('remaining_years', 0)}")

        with col2:
            st.subheader("Rate Calculation")
            st.markdown(f"**Credit Score:** {client.get('credit_score', 'N/A')}")
            st.markdown(f"**LTV:** {client.get('ltv', 0):.1f}%")
            st.markdown(f"**Property Type:** {client.get('property_type', 'N/A')}")
            st.markdown(f"**Occupancy:** {client.get('occupancy', 'N/A')}")

            st.markdown("---")
            trigger = client.get('trigger_rate')
            available = client.get('available_rate')
            diff = client.get('difference')

            st.markdown(f"**Trigger Rate:** {trigger*100:.3f}%" if trigger else "**Trigger Rate:** Not calculated")
            st.markdown(f"**Available Rate:** {available*100:.3f}%" if available else "**Available Rate:** Not calculated")

            if diff is not None:
                if diff > 0:
                    st.markdown(f"**Difference:** :green[{diff*100:+.3f}%] (Ready!)")
                else:
                    st.markdown(f"**Difference:** :red[{diff*100:+.3f}%]")

        # Advanced parameters (collapsible)
        with st.expander("Advanced Parameters"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Discount Rate:** {client.get('discount_rate', 0.05)*100:.1f}%")
                st.markdown(f"**Rate Volatility:** {client.get('rate_volatility', 0.0109):.4f}")
                st.markdown(f"**Tax Rate:** {client.get('tax_rate', 0.28)*100:.0f}%")
            with col2:
                st.markdown(f"**Fixed Refi Cost:** ${client.get('fixed_refi_cost', 2000):,.0f}")
                st.markdown(f"**Points:** {client.get('points_pct', 0.01)*100:.1f}%")
                st.markdown(f"**Moving Probability:** {client.get('prob_moving', 0.10)*100:.0f}%")
                st.markdown(f"**Inflation Rate:** {client.get('inflation_rate', 0.03)*100:.1f}%")

        # Edit button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit Client", type="primary", use_container_width=True):
                st.session_state.edit_client_id = client_id
                st.session_state.page = "edit_client"
                st.rerun()

    with tab2:
        st.subheader("Rate Check History")
        history = get_rate_check_history(client_id)
        if history:
            df = pd.DataFrame(history)
            df['check_date'] = pd.to_datetime(df['check_date']).dt.strftime('%Y-%m-%d %H:%M')
            df['available_rate'] = df['available_rate'].apply(lambda x: f"{x*100:.3f}%")
            df['trigger_rate'] = df['trigger_rate'].apply(lambda x: f"{x*100:.3f}%")
            df['difference'] = df['difference'].apply(lambda x: f"{x*100:+.3f}%")
            st.dataframe(
                df[['check_date', 'available_rate', 'trigger_rate', 'difference', 'is_ready_to_refinance']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No rate check history yet.")

    with tab3:
        st.subheader("Contact History")
        contacts = get_contact_history(client_id)
        if contacts:
            for contact in contacts:
                st.markdown(f"**{contact['contact_date']}** - {contact['contact_type']}")
                if contact.get('notes'):
                    st.markdown(f"> {contact['notes']}")
                st.markdown(f"*Outcome: {contact.get('outcome', 'N/A')}* | *By: {contact.get('contacted_by', 'Unknown')}*")
                st.markdown("---")
        else:
            st.info("No contact history yet.")
