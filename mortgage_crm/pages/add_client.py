"""
Add/Edit Client Page (Phase 5)

Single form with ALL inputs organized into sections:
- Section 1: Client Info
- Section 2: Current Mortgage (for optimal threshold calculation)
- Section 3: Loan Scenario (for live rate calculation)
- Section 4: Advanced Parameters (collapsible, use defaults)

On Save:
1. Calculate optimal_rate_drop using ADL model
2. Calculate trigger_rate = current_rate - optimal_rate_drop
3. Calculate available_rate using LLPA logic
4. Calculate difference = trigger_rate - available_rate
5. Set ready_to_refinance = (difference > 0)
"""

import streamlit as st
from datetime import datetime

from database import (
    create_client, get_client_by_id, update_client, delete_client,
    get_admin_settings
)
from utils.optimal_threshold import calculate_trigger_rate
from utils.rate_calculator import calculate_available_rate


# US States list
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "Washington DC", "West Virginia", "Wisconsin", "Wyoming"
]


def get_defaults():
    """Get default values from admin settings"""
    settings = get_admin_settings()
    return {
        'discount_rate': float(settings.get('default_discount_rate', 0.05)),
        'volatility': float(settings.get('default_volatility', 0.0109)),
        'tax_rate': float(settings.get('default_tax_rate', 0.28)),
        'fixed_cost': float(settings.get('default_fixed_cost', 2000)),
        'points': float(settings.get('default_points', 0.01)),
        'prob_moving': float(settings.get('default_prob_moving', 0.10)),
        'inflation': float(settings.get('default_inflation', 0.03)),
        'base_rate_conventional': float(settings.get('base_rate_conventional', 6.5)),
        'base_rate_fha': float(settings.get('base_rate_fha', 6.25)),
    }


def calculate_client_rates(client_data: dict, defaults: dict) -> dict:
    """Calculate all rate fields for a client"""
    # Calculate trigger rate using ADL model
    result = calculate_trigger_rate(
        current_rate=client_data['current_mortgage_rate'],
        remaining_balance=client_data['current_mortgage_balance'],
        remaining_years=client_data['remaining_years'],
        discount_rate=client_data.get('discount_rate', defaults['discount_rate']),
        volatility=client_data.get('rate_volatility', defaults['volatility']),
        tax_rate=client_data.get('tax_rate', defaults['tax_rate']),
        fixed_cost=client_data.get('fixed_refi_cost', defaults['fixed_cost']),
        points=client_data.get('points_pct', defaults['points']),
        prob_moving=client_data.get('prob_moving', defaults['prob_moving']),
        inflation_rate=client_data.get('inflation_rate', defaults['inflation'])
    )

    trigger_rate = result.get('trigger_rate')
    optimal_rate_drop = result.get('optimal_threshold_bps')

    # Calculate available rate
    base_rate = defaults['base_rate_fha'] if client_data.get('loan_type') == 'FHA' else defaults['base_rate_conventional']
    rate_info = calculate_available_rate(
        base_rate=base_rate,
        credit_score=client_data['credit_score'],
        ltv=client_data['ltv'],
        loan_amount=client_data.get('loan_amount') or client_data['current_mortgage_balance'],
        loan_type=client_data.get('loan_type', 'Conventional'),
        property_type=client_data.get('property_type', 'Single Family'),
        occupancy=client_data.get('occupancy', 'Primary Residence')
    )
    available_rate = rate_info['final_rate'] / 100  # Convert to decimal

    # Calculate difference
    difference = trigger_rate - available_rate if trigger_rate else None
    ready = difference > 0 if difference else False

    return {
        'optimal_rate_drop': optimal_rate_drop,
        'trigger_rate': trigger_rate,
        'available_rate': available_rate,
        'difference': difference,
        'ready_to_refinance': ready
    }


def render_add_client(user_id: int):
    """Render the add client form"""
    defaults = get_defaults()

    st.header("Add New Client")

    if st.button("← Cancel"):
        st.session_state.page = "dashboard"
        st.rerun()

    with st.form("add_client_form"):
        # Section 1: Client Info
        st.subheader("1. Client Information")
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name *")
            email = st.text_input("Email")

        with col2:
            last_name = st.text_input("Last Name *")
            phone = st.text_input("Phone")

        # Section 2: Current Mortgage
        st.markdown("---")
        st.subheader("2. Current Mortgage (for optimal threshold calculation)")

        col1, col2 = st.columns(2)

        with col1:
            current_mortgage_balance = st.number_input(
                "Current Mortgage Balance ($) *",
                min_value=10000,
                max_value=5000000,
                value=400000,
                step=10000
            )

            current_mortgage_rate = st.number_input(
                "Current Mortgage Rate (%) *",
                min_value=0.0,
                max_value=20.0,
                value=7.0,
                step=0.125,
                format="%.3f"
            )

        with col2:
            remaining_years = st.number_input(
                "Years Remaining *",
                min_value=1,
                max_value=30,
                value=25,
                step=1
            )

            loan_type = st.selectbox(
                "Loan Type",
                options=["Conventional", "FHA"]
            )

        # Section 3: Loan Scenario (for rate calculation)
        st.markdown("---")
        st.subheader("3. Loan Scenario (for live rate calculation)")

        col1, col2 = st.columns(2)

        with col1:
            credit_score = st.number_input(
                "Credit Score *",
                min_value=300,
                max_value=850,
                value=720,
                step=1
            )

            property_value = st.number_input(
                "Property Value ($)",
                min_value=10000,
                max_value=10000000,
                value=500000,
                step=10000
            )

            loan_amount = st.number_input(
                "Loan Amount ($)",
                min_value=10000,
                max_value=5000000,
                value=current_mortgage_balance,
                step=10000,
                help="Auto-filled from mortgage balance, or enter manually"
            )

        with col2:
            ltv = st.number_input(
                "Loan-to-Value (LTV) %",
                min_value=0.0,
                max_value=100.0,
                value=round((loan_amount / property_value) * 100, 1) if property_value > 0 else 80.0,
                step=0.1,
                format="%.1f"
            )

            state = st.selectbox(
                "State *",
                options=[""] + US_STATES
            )

            property_type = st.selectbox(
                "Property Type",
                options=["Single Family", "Condo", "2-Unit", "3-Unit", "4-Unit", "Manufactured Home"]
            )

            occupancy = st.selectbox(
                "Occupancy",
                options=["Primary Residence", "Second Home", "Investment Property"]
            )

            loan_purpose = st.selectbox(
                "Loan Purpose",
                options=["Rate/Term Refinance", "Cash-Out Refinance", "Purchase"]
            )

        # Section 4: Advanced Parameters (collapsible)
        st.markdown("---")
        with st.expander("4. Advanced Parameters (uses defaults if unchanged)"):
            col1, col2, col3 = st.columns(3)

            with col1:
                discount_rate = st.number_input(
                    "Real Discount Rate (%)",
                    min_value=0.0,
                    max_value=20.0,
                    value=defaults['discount_rate'] * 100,
                    step=0.5,
                    help="Default 5%"
                ) / 100

                prob_moving = st.number_input(
                    "Annual Probability of Moving (%)",
                    min_value=0.0,
                    max_value=50.0,
                    value=defaults['prob_moving'] * 100,
                    step=1.0,
                    help="Default 10%"
                ) / 100

            with col2:
                fixed_refi_cost = st.number_input(
                    "Fixed Refinancing Cost ($)",
                    min_value=0,
                    max_value=20000,
                    value=int(defaults['fixed_cost']),
                    step=100,
                    help="Default $2000"
                )

                points_pct = st.number_input(
                    "Points (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=defaults['points'] * 100,
                    step=0.1,
                    help="Default 1%"
                ) / 100

            with col3:
                tax_rate = st.number_input(
                    "Marginal Tax Rate (%)",
                    min_value=0.0,
                    max_value=50.0,
                    value=defaults['tax_rate'] * 100,
                    step=1.0,
                    help="Default 28%"
                ) / 100

                inflation_rate = st.number_input(
                    "Expected Inflation (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=defaults['inflation'] * 100,
                    step=0.5,
                    help="Default 3%"
                ) / 100

                rate_volatility = st.number_input(
                    "Interest Rate Volatility",
                    min_value=0.001,
                    max_value=0.05,
                    value=defaults['volatility'],
                    step=0.001,
                    format="%.4f",
                    help="Default 0.0109"
                )

        # Submit
        st.markdown("---")
        submitted = st.form_submit_button("Add Client", type="primary", use_container_width=True)

        if submitted:
            # Validation
            if not first_name or not last_name:
                st.error("First and last name are required")
            elif not state:
                st.error("State is required")
            elif current_mortgage_balance <= 0:
                st.error("Mortgage balance must be greater than 0")
            elif credit_score < 300:
                st.error("Please enter a valid credit score")
            else:
                # Build client data
                client_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'current_mortgage_balance': current_mortgage_balance,
                    'current_mortgage_rate': current_mortgage_rate / 100,  # Convert to decimal
                    'remaining_years': remaining_years,
                    'credit_score': credit_score,
                    'property_value': property_value,
                    'loan_amount': loan_amount,
                    'ltv': ltv,
                    'property_type': property_type,
                    'occupancy': occupancy,
                    'loan_purpose': loan_purpose,
                    'state': state,
                    'loan_type': loan_type,
                    'discount_rate': discount_rate,
                    'rate_volatility': rate_volatility,
                    'tax_rate': tax_rate,
                    'fixed_refi_cost': fixed_refi_cost,
                    'points_pct': points_pct,
                    'prob_moving': prob_moving,
                    'inflation_rate': inflation_rate,
                }

                # Calculate rates
                rate_data = calculate_client_rates(client_data, defaults)
                client_data.update(rate_data)

                # Create client
                client_id = create_client(user_id, client_data)

                if client_id:
                    st.success(f"Client {first_name} {last_name} added successfully!")

                    # Show calculated values
                    st.info(f"""
                    **Calculated Values:**
                    - Optimal Rate Drop: {rate_data['optimal_rate_drop']:.0f} bps
                    - Trigger Rate: {rate_data['trigger_rate']*100:.3f}%
                    - Available Rate: {rate_data['available_rate']*100:.3f}%
                    - Difference: {rate_data['difference']*100:+.3f}%
                    - Ready to Refinance: {'Yes!' if rate_data['ready_to_refinance'] else 'Not yet'}
                    """)

                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Failed to create client")


def render_edit_client(user_id: int, client_id: int):
    """Render the edit client form"""
    client = get_client_by_id(client_id)
    if not client:
        st.error("Client not found")
        return

    defaults = get_defaults()

    st.header(f"Edit Client: {client['first_name']} {client['last_name']}")

    if st.button("← Cancel"):
        st.session_state.page = "dashboard"
        st.rerun()

    with st.form("edit_client_form"):
        # Section 1: Client Info
        st.subheader("1. Client Information")
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name *", value=client.get('first_name', ''))
            email = st.text_input("Email", value=client.get('email', '') or '')

        with col2:
            last_name = st.text_input("Last Name *", value=client.get('last_name', ''))
            phone = st.text_input("Phone", value=client.get('phone', '') or '')

        # Section 2: Current Mortgage
        st.markdown("---")
        st.subheader("2. Current Mortgage")

        col1, col2 = st.columns(2)

        with col1:
            current_mortgage_balance = st.number_input(
                "Current Mortgage Balance ($) *",
                min_value=10000,
                max_value=5000000,
                value=int(client.get('current_mortgage_balance', 400000) or 400000),
                step=10000
            )

            current_mortgage_rate = st.number_input(
                "Current Mortgage Rate (%) *",
                min_value=0.0,
                max_value=20.0,
                value=float((client.get('current_mortgage_rate', 0.07) or 0.07) * 100),
                step=0.125,
                format="%.3f"
            )

        with col2:
            remaining_years = st.number_input(
                "Years Remaining *",
                min_value=1,
                max_value=30,
                value=int(client.get('remaining_years', 25) or 25),
                step=1
            )

            loan_types = ["Conventional", "FHA"]
            current_loan_type = client.get('loan_type', 'Conventional')
            loan_type_idx = loan_types.index(current_loan_type) if current_loan_type in loan_types else 0

            loan_type = st.selectbox(
                "Loan Type",
                options=loan_types,
                index=loan_type_idx
            )

        # Section 3: Loan Scenario
        st.markdown("---")
        st.subheader("3. Loan Scenario")

        col1, col2 = st.columns(2)

        with col1:
            credit_score = st.number_input(
                "Credit Score *",
                min_value=300,
                max_value=850,
                value=int(client.get('credit_score', 720) or 720),
                step=1
            )

            property_value = st.number_input(
                "Property Value ($)",
                min_value=10000,
                max_value=10000000,
                value=int(client.get('property_value', 500000) or 500000),
                step=10000
            )

            loan_amount = st.number_input(
                "Loan Amount ($)",
                min_value=10000,
                max_value=5000000,
                value=int(client.get('loan_amount', current_mortgage_balance) or current_mortgage_balance),
                step=10000
            )

        with col2:
            ltv = st.number_input(
                "Loan-to-Value (LTV) %",
                min_value=0.0,
                max_value=100.0,
                value=float(client.get('ltv', 80.0) or 80.0),
                step=0.1,
                format="%.1f"
            )

            current_state = client.get('state', '')
            state_idx = US_STATES.index(current_state) + 1 if current_state in US_STATES else 0
            state = st.selectbox("State *", options=[""] + US_STATES, index=state_idx)

            property_types = ["Single Family", "Condo", "2-Unit", "3-Unit", "4-Unit", "Manufactured Home"]
            current_prop = client.get('property_type', 'Single Family')
            prop_idx = property_types.index(current_prop) if current_prop in property_types else 0
            property_type = st.selectbox("Property Type", options=property_types, index=prop_idx)

            occupancy_types = ["Primary Residence", "Second Home", "Investment Property"]
            current_occ = client.get('occupancy', 'Primary Residence')
            occ_idx = occupancy_types.index(current_occ) if current_occ in occupancy_types else 0
            occupancy = st.selectbox("Occupancy", options=occupancy_types, index=occ_idx)

            purpose_types = ["Rate/Term Refinance", "Cash-Out Refinance", "Purchase"]
            current_purpose = client.get('loan_purpose', 'Rate/Term Refinance')
            purpose_idx = purpose_types.index(current_purpose) if current_purpose in purpose_types else 0
            loan_purpose = st.selectbox("Loan Purpose", options=purpose_types, index=purpose_idx)

        # Section 4: Advanced Parameters
        st.markdown("---")
        with st.expander("4. Advanced Parameters"):
            col1, col2, col3 = st.columns(3)

            with col1:
                discount_rate = st.number_input(
                    "Real Discount Rate (%)",
                    min_value=0.0,
                    max_value=20.0,
                    value=float((client.get('discount_rate', 0.05) or 0.05) * 100),
                    step=0.5
                ) / 100

                prob_moving = st.number_input(
                    "Annual Probability of Moving (%)",
                    min_value=0.0,
                    max_value=50.0,
                    value=float((client.get('prob_moving', 0.10) or 0.10) * 100),
                    step=1.0
                ) / 100

            with col2:
                fixed_refi_cost = st.number_input(
                    "Fixed Refinancing Cost ($)",
                    min_value=0,
                    max_value=20000,
                    value=int(client.get('fixed_refi_cost', 2000) or 2000),
                    step=100
                )

                points_pct = st.number_input(
                    "Points (%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=float((client.get('points_pct', 0.01) or 0.01) * 100),
                    step=0.1
                ) / 100

            with col3:
                tax_rate = st.number_input(
                    "Marginal Tax Rate (%)",
                    min_value=0.0,
                    max_value=50.0,
                    value=float((client.get('tax_rate', 0.28) or 0.28) * 100),
                    step=1.0
                ) / 100

                inflation_rate = st.number_input(
                    "Expected Inflation (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=float((client.get('inflation_rate', 0.03) or 0.03) * 100),
                    step=0.5
                ) / 100

                rate_volatility = st.number_input(
                    "Interest Rate Volatility",
                    min_value=0.001,
                    max_value=0.05,
                    value=float(client.get('rate_volatility', 0.0109) or 0.0109),
                    step=0.001,
                    format="%.4f"
                )

        # Submit
        st.markdown("---")
        submitted = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

        if submitted:
            if not first_name or not last_name:
                st.error("First and last name are required")
            elif not state:
                st.error("State is required")
            else:
                # Build client data
                client_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'current_mortgage_balance': current_mortgage_balance,
                    'current_mortgage_rate': current_mortgage_rate / 100,
                    'remaining_years': remaining_years,
                    'credit_score': credit_score,
                    'property_value': property_value,
                    'loan_amount': loan_amount,
                    'ltv': ltv,
                    'property_type': property_type,
                    'occupancy': occupancy,
                    'loan_purpose': loan_purpose,
                    'state': state,
                    'loan_type': loan_type,
                    'discount_rate': discount_rate,
                    'rate_volatility': rate_volatility,
                    'tax_rate': tax_rate,
                    'fixed_refi_cost': fixed_refi_cost,
                    'points_pct': points_pct,
                    'prob_moving': prob_moving,
                    'inflation_rate': inflation_rate,
                }

                # Calculate rates
                rate_data = calculate_client_rates(client_data, defaults)
                client_data.update(rate_data)

                # Update client
                update_client(client_id, client_data)

                st.success("Client updated successfully!")
                st.session_state.page = "dashboard"
                st.rerun()


def render_delete_client(client_id: int):
    """Render delete confirmation"""
    client = get_client_by_id(client_id)
    if not client:
        st.error("Client not found")
        return

    st.warning(f"Are you sure you want to delete {client['first_name']} {client['last_name']}?")
    st.markdown("This will permanently delete all client data and history.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    with col2:
        if st.button("Delete", type="primary", use_container_width=True):
            delete_client(client_id)
            st.success("Client deleted")
            st.session_state.page = "dashboard"
            st.rerun()
