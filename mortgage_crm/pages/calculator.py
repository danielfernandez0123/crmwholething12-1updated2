"""
Simplified Calculator Page (Phase 6)

Shows ONLY the main calculator inputs and result:
- All inputs from sidebar of original app
- Big result: "Optimal Rate Drop: X basis points"
- "Your Trigger Rate: X%"
- Green/red indicator showing if ready to refi based on current market

For advanced analysis tools, see the "Other Tools" page.
"""

import streamlit as st
import numpy as np
import pandas as pd

from database import get_admin_settings
from utils.optimal_threshold import calculate_trigger_rate, is_ready_to_refinance
from utils.rate_calculator import (
    calculate_available_rate, get_fha_mip_info,
    get_available_rates_with_points, get_pricing_grid
)
from utils.llpa import calculate_total_llpa


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


def render_calculator():
    """Render the simplified calculator page"""
    settings = get_admin_settings()
    base_rate_conv = float(settings.get('base_rate_conventional', 6.5))
    base_rate_fha = float(settings.get('base_rate_fha', 6.25))

    st.header("Refinancing Calculator")
    st.markdown("Calculate optimal refinancing thresholds using the ADL/NBER model")

    # Main input section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Mortgage")

        current_rate = st.number_input(
            "Current Mortgage Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=7.0,
            step=0.125,
            format="%.3f"
        )

        mortgage_balance = st.number_input(
            "Mortgage Balance ($)",
            min_value=10000,
            max_value=5000000,
            value=400000,
            step=10000
        )

        remaining_years = st.number_input(
            "Years Remaining",
            min_value=1,
            max_value=30,
            value=25
        )

        loan_type = st.selectbox("Loan Type", options=["Conventional", "FHA"])

    with col2:
        st.subheader("Borrower Profile")

        credit_score = st.number_input(
            "Credit Score",
            min_value=300,
            max_value=850,
            value=720
        )

        ltv = st.number_input(
            "Loan-to-Value (LTV) %",
            min_value=0.0,
            max_value=100.0,
            value=80.0,
            step=0.1,
            format="%.1f"
        )

        property_type = st.selectbox(
            "Property Type",
            options=["Single Family", "Condo", "2-Unit", "3-Unit", "4-Unit"]
        )

        occupancy = st.selectbox(
            "Occupancy",
            options=["Primary Residence", "Second Home", "Investment Property"]
        )

    # Calculate button
    if st.button("Calculate", type="primary", use_container_width=True):
        # Calculate optimal threshold
        result = calculate_trigger_rate(
            current_rate=current_rate / 100,
            remaining_balance=mortgage_balance,
            remaining_years=remaining_years
        )

        trigger_rate = result.get('trigger_rate')
        optimal_bps = result.get('optimal_threshold_bps')

        # Calculate available rate
        base_rate = base_rate_fha if loan_type == 'FHA' else base_rate_conv
        rate_info = calculate_available_rate(
            base_rate=base_rate,
            credit_score=credit_score,
            ltv=ltv,
            loan_amount=mortgage_balance,
            loan_type=loan_type,
            property_type=property_type,
            occupancy=occupancy
        )
        available_rate = rate_info['final_rate'] / 100

        # Check if ready
        ready_check = is_ready_to_refinance(trigger_rate, available_rate)

        st.markdown("---")

        # BIG RESULT DISPLAY
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Optimal Rate Drop",
                f"{optimal_bps:.0f} bps" if optimal_bps else "N/A",
                help="Rate must drop this much before refinancing"
            )

        with col2:
            st.metric(
                "Your Trigger Rate",
                f"{trigger_rate*100:.3f}%" if trigger_rate else "N/A",
                help="Refinance when rates reach this level"
            )

        with col3:
            st.metric(
                "Available Rate Today",
                f"{available_rate*100:.3f}%",
                help=f"Based on {loan_type} {base_rate:.3f}% + LLPA"
            )

        # Ready/Not Ready indicator
        st.markdown("---")

        if ready_check['is_ready']:
            diff_bps = ready_check['difference_bps']
            st.success(f"""
            ## Ready to Refinance!

            Available rate ({available_rate*100:.3f}%) is **{diff_bps:.0f} bps below** your trigger rate.

            **Current Rate:** {current_rate:.3f}%
            **Potential Savings:** {current_rate - available_rate*100:.3f}% rate reduction
            """)
        else:
            if ready_check['difference_bps']:
                need_drop = -ready_check['difference_bps']
                st.warning(f"""
                ## Not Ready Yet

                Rates need to drop **{need_drop:.0f} more bps** before refinancing makes sense.

                **Current Rate:** {current_rate:.3f}%
                **Trigger Rate:** {trigger_rate*100:.3f}%
                **Available Today:** {available_rate*100:.3f}%
                """)
            else:
                st.info("Unable to calculate. Please check your inputs.")

        # Rate breakdown section
        st.markdown("---")
        st.subheader("Rate Breakdown")

        if loan_type == 'Conventional':
            llpa = calculate_total_llpa(
                credit_score=credit_score,
                ltv=ltv,
                loan_amount=mortgage_balance,
                loan_purpose="Rate/Term Refinance",
                property_type=property_type,
                occupancy=occupancy
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Base Rate:** {base_rate:.3f}%")
                st.markdown(f"**Credit Score/LTV LLPA:** {llpa.get('Credit Score / LTV', 0):+.3f}%")
                st.markdown(f"**Property Type LLPA:** {llpa.get('Property Type', 0):+.3f}%")
            with col2:
                st.markdown(f"**Occupancy LLPA:** {llpa.get('Occupancy', 0):+.3f}%")
                st.markdown(f"**High Balance LLPA:** {llpa.get('High Balance', 0):+.3f}%")
                st.markdown(f"**Total LLPA:** {llpa.get('Total LLPA', 0):+.3f}%")
        else:
            st.markdown(f"**Base Rate:** {base_rate:.3f}%")
            st.markdown("*FHA loans do not have LLPAs*")

            mip = get_fha_mip_info(ltv, mortgage_balance)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**FHA Mortgage Insurance:**")
                st.markdown(f"- Upfront MIP: {mip['upfront_mip_rate']}% (${mip['upfront_mip_amount']:,.0f})")
            with col2:
                st.markdown(f"- Annual MIP: {mip['annual_mip_rate']}%")
                st.markdown(f"- Monthly MIP: ${mip['monthly_mip']:,.2f}")

        # Show pricing grid rates if available
        st.markdown("---")
        st.subheader("Available Rates & Points")

        pricing_grid = get_pricing_grid(loan_type)

        if pricing_grid:
            rates_with_points = get_available_rates_with_points(
                base_rate=base_rate,
                credit_score=credit_score,
                ltv=ltv,
                loan_amount=mortgage_balance,
                loan_type=loan_type,
                property_type=property_type,
                occupancy=occupancy
            )

            if rates_with_points:
                # Create table data
                table_data = []
                for r in rates_with_points:
                    # Determine status relative to trigger rate
                    if trigger_rate and r['rate'] / 100 <= trigger_rate:
                        status = "REFI NOW"
                    else:
                        status = ""

                    table_data.append({
                        'Rate': f"{r['rate']:.3f}%",
                        'Base Pts': f"{r['base_points']:+.3f}",
                        'LLPA Pts': f"{r['llpa_points']:+.3f}",
                        'Total Pts': f"{r['total_points']:+.3f}",
                        'Cost/Credit': f"${r['total_cost']:,.0f}",
                        'Status': status
                    })

                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True, height=300)

                st.caption("Negative points = lender credit (you receive money). Positive points = cost (you pay).")
        else:
            st.info("No pricing grid configured. Admin can set up available rates in Admin Panel > Pricing Grid.")

    # Link to advanced tools
    st.markdown("---")
    st.info("For comprehensive analysis tools (Sensitivity Analysis, ENPV, Points Trade-off, Monte Carlo, etc.), visit the **Other Tools** page from the sidebar.")
