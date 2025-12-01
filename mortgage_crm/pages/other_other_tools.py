"""
Other Other Tools Page - Additional Calculators

Contains:
- Buy Points Analysis (for home purchase)
- Rent vs Buy Calculator

These are separate from the main ADL/NBER refinancing tools.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.special import lambertw

from database import get_admin_settings


# =============================================================================
# CORE CALCULATION FUNCTIONS (same as other_tools.py)
# =============================================================================

def calculate_lambda(mu, i0, Gamma, pi):
    """Calculate λ (lambda) as per page 19 and Appendix C of the paper"""
    if i0 * Gamma < 100:
        lambda_val = mu + i0 / (np.exp(i0 * Gamma) - 1) + pi
    else:
        lambda_val = mu + pi
    return lambda_val


def calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa, tau):
    """Calculate the optimal refinancing threshold x* using Lambert W function"""
    psi = np.sqrt(2 * (rho + lambda_val)) / sigma
    C_M = kappa / (1 - tau)
    phi = 1 + psi * (rho + lambda_val) * C_M / M

    try:
        w_arg = -np.exp(-phi)
        w_val = np.real(lambertw(w_arg, k=0))
        x_star = (1 / psi) * (phi + w_val)
    except:
        x_star = np.nan

    return x_star, psi, phi, C_M


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_other_other_tools(user_id: int):
    """Render the Other Other Tools page"""
    st.header("Additional Calculators")
    st.markdown("Buy Points Analysis and Rent vs Buy Calculator")

    tab1, tab2 = st.tabs([
        "🏠 Buy Points Analysis",
        "🏠 Rent vs Buy"
    ])

    with tab1:
        render_buy_points_analysis()

    with tab2:
        render_rent_vs_buy()


# =============================================================================
# BUY POINTS ANALYSIS (EXACT from original tab7)
# =============================================================================

def render_buy_points_analysis():
    """Render Buy Points Analysis - EXACT from original tab7"""
    st.header("🏠 Points Analysis for Home Purchase")

    st.markdown("""
    Analyze whether to pay points or take lender credits when purchasing a home.
    This uses the same refinancing formula to compare different rate/cost combinations.
    """)

    # Input parameters
    st.subheader("📊 Loan Parameters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        points_loan_amount = st.number_input(
            "Loan Amount ($)",
            min_value=50000,
            max_value=5000000,
            value=400000,
            step=10000,
            help="The amount you're borrowing",
            key="bp_loan_amount"
        )

    with col2:
        points_par_rate = st.number_input(
            "Par Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=6.0,
            step=0.001,
            format="%.3f",
            help="The par rate",
            key="bp_par_rate"
        ) / 100

    with col3:
        points_loan_term = st.number_input(
            "Loan Term (years)",
            min_value=15,
            max_value=30,
            value=30,
            step=5,
            help="Length of the mortgage",
            key="bp_loan_term"
        )

    with col4:
        par_cost = st.number_input(
            "Cost at Par Rate ($)",
            min_value=-10000,
            max_value=10000,
            value=1000,
            step=100,
            help="The cost for the par rate",
            key="bp_par_cost"
        )

    # Add tax rate to second row
    col1b, col2b, col3b, col4b = st.columns(4)

    with col1b:
        points_tax_rate = st.number_input(
            "Marginal Tax Rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=28.0,
            step=1.0,
            help="Your marginal tax rate",
            key="bp_tax_rate"
        ) / 100

    st.subheader("🔧 Economic Parameters")

    col1c, col2c, col3c, col4c = st.columns(4)

    with col1c:
        points_discount_rate = st.number_input(
            "Discount Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.5,
            help="Your personal discount rate",
            key="bp_discount_rate"
        ) / 100

    with col2c:
        points_invest_rate = st.number_input(
            "Investment Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.5,
            help="Return on invested savings",
            key="bp_invest_rate"
        ) / 100

    with col3c:
        points_move_prob = st.number_input(
            "Annual Probability of Moving (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Annual probability of selling/refinancing",
            key="bp_move_prob"
        ) / 100

    with col4c:
        points_inflation = st.number_input(
            "Expected Inflation Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Expected inflation rate",
            key="bp_inflation"
        ) / 100

    # Volatility input (needed for optimal threshold calculation)
    sigma = st.number_input(
        "Interest Rate Volatility (σ)",
        min_value=0.001,
        max_value=0.05,
        value=0.0109,
        step=0.001,
        format="%.4f",
        help="Annual standard deviation of mortgage rate",
        key="bp_sigma"
    )

    # Calculate lambda for this scenario
    points_lambda = points_move_prob + points_par_rate / (np.exp(points_par_rate * points_loan_term) - 1) + points_inflation

    st.markdown("---")
    st.subheader("📋 Rate & Cost Scenarios")

    st.info("""
    Enter different rate/cost combinations below. The "Cost Above Par" is automatically calculated.
    """)

    # Create input table with Actual Cost and Cost Above Par
    scenarios_data = pd.DataFrame({
        'Rate (%)': [points_par_rate * 100, 5.75, 5.50, 5.25, 6.25, 6.50, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'Actual Cost ($)': [par_cost, 5000, 9000, 13000, -3000, -7000, 0, 0, 0, 0, 0, 0],
        'Cost Above Par ($)': [0, 4000, 8000, 12000, -4000, -8000, 0, 0, 0, 0, 0, 0]
    })

    edited_scenarios = st.data_editor(
        scenarios_data,
        column_config={
            'Rate (%)': st.column_config.NumberColumn(
                'Rate (%)',
                help="Interest rate for this scenario",
                format="%.3f",
                min_value=0.0,
                max_value=20.0,
                step=0.125
            ),
            'Actual Cost ($)': st.column_config.NumberColumn(
                'Actual Cost ($)',
                help="Total cost for this rate",
                format="$%.0f",
                step=100
            ),
            'Cost Above Par ($)': st.column_config.NumberColumn(
                'Cost Above Par ($)',
                help="Cost relative to par rate",
                format="$%.0f",
                step=100,
                disabled=True
            )
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="bp_scenarios"
    )

    # Calculate Cost Above Par for each row
    edited_scenarios['Cost Above Par ($)'] = edited_scenarios['Actual Cost ($)'] - par_cost

    # Filter active scenarios
    active_scenarios = edited_scenarios[edited_scenarios['Rate (%)'] > 0].copy()

    if len(active_scenarios) >= 2:
        # Calculate optimal thresholds using existing formula
        st.markdown("---")
        st.subheader("🎯 Optimal Rate Analysis")

        # For each scenario, calculate what would be the optimal threshold
        results = []
        for idx, row in active_scenarios.iterrows():
            rate = row['Rate (%)']
            actual_cost = row['Actual Cost ($)']
            cost_above_par = row['Cost Above Par ($)']

            # Use the existing formula with actual cost
            temp_x_star, _, _, _ = calculate_optimal_threshold(
                points_loan_amount,
                points_discount_rate,
                points_lambda,
                sigma,
                abs(cost_above_par),
                points_tax_rate
            )

            # The optimal threshold tells us how much the rate needs to drop
            optimal_rate_drop = temp_x_star * 10000
            actual_drop = (points_par_rate - rate / 100) * 10000
            difference = actual_drop - optimal_rate_drop

            # Simple net benefit calculation
            x = rate / 100 - points_par_rate
            net_benefit = ((-x * points_loan_amount * (1 - points_tax_rate)) / (points_discount_rate + points_lambda)) - actual_cost

            results.append({
                'Rate (%)': rate,
                'Actual Cost': actual_cost,
                'Cost Above Par': cost_above_par,
                'Optimal Drop Needed (bps)': optimal_rate_drop,
                'Actual Drop (bps)': actual_drop,
                'Difference (bps)': difference,
                'Simple Net Benefit ($)': net_benefit
            })

        results_df = pd.DataFrame(results)

        # Print calculation for the first row
        if len(results) > 0:
            first_row = results[0]
            st.info(f"""
            **Net Benefit Calculation for Rate {first_row['Rate (%)']}%:**

            Formula: Net Benefit = (-x × M × (1-τ)) / (ρ + λ) - C

            Where:
            - x = Rate differential = {first_row['Rate (%)']/100:.5f} - {points_par_rate:.5f} = {first_row['Rate (%)']/100 - points_par_rate:.5f}
            - M = Loan amount = ${points_loan_amount:,.0f}
            - τ = Tax rate = {points_tax_rate:.2%}
            - ρ = Discount rate = {points_discount_rate:.2%}
            - λ = Lambda = {points_lambda:.4f}
            - C = Actual cost = ${first_row['Actual Cost']:,.0f}

            Calculation:
            Net Benefit = (-{first_row['Rate (%)']/100 - points_par_rate:.5f} × ${points_loan_amount:,.0f} × {1-points_tax_rate:.2f}) / ({points_discount_rate:.3f} + {points_lambda:.4f}) - ${first_row['Actual Cost']:,.0f}
            Net Benefit = ${first_row['Simple Net Benefit ($)']:,.2f}
            """)

        # Custom styling function for the difference column
        def style_difference(val):
            if isinstance(val, (int, float)):
                if val >= 0:
                    return 'background-color: lightgreen'
                else:
                    return 'background-color: lightcoral'
            return ''

        # Display with formatting and color coding
        styled_df = results_df.style.format({
            'Rate (%)': '{:.3f}%',
            'Actual Cost': '${:,.0f}',
            'Cost Above Par': '${:,.0f}',
            'Optimal Drop Needed (bps)': '{:.0f}',
            'Actual Drop (bps)': '{:.0f}',
            'Difference (bps)': '{:+.0f}',
            'Simple Net Benefit ($)': '${:,.2f}'
        }).map(style_difference, subset=['Difference (bps)'])

        st.dataframe(styled_df, use_container_width=True)

        # Selection for comparison
        st.markdown("---")
        st.subheader("📊 Detailed Comparison")

        st.markdown("Select two scenarios to compare:")

        col1s, col2s = st.columns(2)

        with col1s:
            scenario_1_idx = st.selectbox(
                "Scenario 1",
                range(len(active_scenarios)),
                format_func=lambda x: f"Rate: {active_scenarios.iloc[x]['Rate (%)']}%, Cost: ${active_scenarios.iloc[x]['Actual Cost ($)']:,.0f}",
                key="bp_scenario_1"
            )

        with col2s:
            scenario_2_idx = st.selectbox(
                "Scenario 2",
                range(len(active_scenarios)),
                index=1 if len(active_scenarios) > 1 else 0,
                format_func=lambda x: f"Rate: {active_scenarios.iloc[x]['Rate (%)']}%, Cost: ${active_scenarios.iloc[x]['Actual Cost ($)']:,.0f}",
                key="bp_scenario_2"
            )

        if scenario_1_idx != scenario_2_idx:
            # Get selected scenarios
            s1 = active_scenarios.iloc[scenario_1_idx]
            s2 = active_scenarios.iloc[scenario_2_idx]

            # Calculate detailed comparison
            def payment(principal, monthly_rate, n_months):
                """Level payment on an amortizing loan."""
                if monthly_rate == 0:
                    return principal / n_months
                denom = 1.0 - (1.0 + monthly_rate) ** (-n_months)
                return principal * monthly_rate / denom

            # Calculate for both scenarios
            n_months = int(points_loan_term * 12)

            # Scenario 1
            r1_monthly = s1['Rate (%)'] / 100 / 12
            principal1 = points_loan_amount + s1['Actual Cost ($)']
            pmt1 = payment(principal1, r1_monthly, n_months)

            # Scenario 2
            r2_monthly = s2['Rate (%)'] / 100 / 12
            principal2 = points_loan_amount + s2['Actual Cost ($)']
            pmt2 = payment(principal2, r2_monthly, n_months)

            # Calculate month-by-month comparison
            bal1 = principal1
            bal2 = principal2
            savings_account = 0.0
            r_inv_monthly = points_invest_rate / 12

            # Find breakeven month
            breakeven_month = None
            breakeven_savings = 0
            breakeven_interest_earned = 0

            for month in range(1, n_months + 1):
                # Calculate interest and principal for both
                int1 = bal1 * r1_monthly
                prin1 = pmt1 - int1
                bal1 -= prin1

                int2 = bal2 * r2_monthly
                prin2 = pmt2 - int2
                bal2 -= prin2

                # Payment difference
                if points_tax_rate > 0:
                    after_tax_pmt1 = pmt1 - (int1 * points_tax_rate)
                    after_tax_pmt2 = pmt2 - (int2 * points_tax_rate)
                    pmt_diff = after_tax_pmt1 - after_tax_pmt2
                else:
                    pmt_diff = pmt1 - pmt2

                # Update savings account
                interest_earned = savings_account * r_inv_monthly
                savings_account = savings_account * (1 + r_inv_monthly) + pmt_diff

                # Net position
                balance_diff = bal1 - bal2
                net_position = savings_account + balance_diff

                # Check for breakeven
                if breakeven_month is None and net_position >= 0:
                    breakeven_month = month
                    breakeven_savings = savings_account
                    breakeven_interest_earned = interest_earned

            # Display results
            st.markdown("---")
            st.subheader("📈 Comparison Results")

            col1r, col2r = st.columns(2)

            with col1r:
                st.metric("Scenario 1 Rate", f"{s1['Rate (%)']}%")
                st.metric("Scenario 1 Monthly Payment", f"${pmt1:,.2f}")
                st.metric("Scenario 1 Total Cost", f"${s1['Actual Cost ($)']:,.0f}")

            with col2r:
                st.metric("Scenario 2 Rate", f"{s2['Rate (%)']}%")
                st.metric("Scenario 2 Monthly Payment", f"${pmt2:,.2f}")
                st.metric("Scenario 2 Total Cost", f"${s2['Actual Cost ($)']:,.0f}")

            st.markdown("---")

            # Breakeven analysis
            if breakeven_month:
                years = breakeven_month / 12
                st.success(f"**Breakeven: {breakeven_month} months ({years:.1f} years)**")

                col1b, col2b, col3b = st.columns(3)

                with col1b:
                    st.metric("Savings at Breakeven", f"${breakeven_savings:,.2f}")

                with col2b:
                    st.metric("Total Interest Earned", f"${breakeven_interest_earned * breakeven_month:,.2f}")

                with col3b:
                    st.metric("Monthly Payment Difference", f"${abs(pmt1 - pmt2):,.2f}")

                # Final position at end of term
                st.markdown("---")
                st.subheader("🏁 End of Term Analysis")

                final_savings = savings_account
                final_bal1 = bal1
                final_bal2 = bal2

                col1f, col2f, col3f = st.columns(3)

                with col1f:
                    st.metric("Final Savings Balance", f"${final_savings:,.2f}")

                with col2f:
                    st.metric("Scenario 1 Final Balance", f"${final_bal1:,.2f}")

                with col3f:
                    st.metric("Scenario 2 Final Balance", f"${final_bal2:,.2f}")

                total_advantage = final_savings + (final_bal1 - final_bal2)

                if total_advantage > 0:
                    st.success(f"**Scenario 1 is better by ${total_advantage:,.2f} at loan maturity**")
                else:
                    st.success(f"**Scenario 2 is better by ${-total_advantage:,.2f} at loan maturity**")

                # ENPV calculation with mortality
                st.markdown("---")
                st.subheader("💰 Expected Net Present Value (ENPV)")

                SMM = 1 - (1 - points_move_prob)**(1/12)

                # Recalculate with present value
                bal1_pv = principal1
                bal2_pv = principal2
                savings_pv = 0.0
                enpv = 0.0
                survival = 1.0

                for month in range(1, n_months + 1):
                    int1 = bal1_pv * r1_monthly
                    prin1 = pmt1 - int1
                    bal1_pv -= prin1

                    int2 = bal2_pv * r2_monthly
                    prin2 = pmt2 - int2
                    bal2_pv -= prin2

                    if points_tax_rate > 0:
                        after_tax_pmt1 = pmt1 - (int1 * points_tax_rate)
                        after_tax_pmt2 = pmt2 - (int2 * points_tax_rate)
                        pmt_diff = after_tax_pmt1 - after_tax_pmt2
                    else:
                        pmt_diff = pmt1 - pmt2

                    savings_pv = savings_pv * (1 + r_inv_monthly) + pmt_diff

                    net_position = savings_pv + (bal1_pv - bal2_pv)

                    # Discount to present value
                    pv_factor = 1 / ((1 + points_discount_rate / 12) ** month)
                    npv = net_position * pv_factor

                    # Add mortality-weighted NPV
                    mortality = survival * SMM
                    enpv += npv * mortality
                    survival = survival * (1 - SMM)

                st.metric("Expected NPV (ENPV)", f"${enpv:,.2f}")

                if enpv > 0:
                    st.info(f"Based on ENPV analysis, **Scenario 1** ({s1['Rate (%)']}%) is preferable")
                else:
                    st.info(f"Based on ENPV analysis, **Scenario 2** ({s2['Rate (%)']}%) is preferable")

            else:
                st.warning("No breakeven point found within the loan term")

        else:
            st.warning("Please select two different scenarios to compare")

    else:
        st.info("Enter at least 2 rate scenarios above to begin analysis")


# =============================================================================
# RENT VS BUY CALCULATOR (EXACT from original tab10)
# =============================================================================

def render_rent_vs_buy():
    """Render Rent vs Buy Calculator - EXACT from original tab10"""
    st.header("🏠 Rent vs Buy Calculator")

    st.markdown("""
    This calculator compares the 30-year financial outcomes of renting vs buying a home,
    accounting for mortgage payments, investment returns, taxes, maintenance, and moving costs.
    """)

    # ===========================================
    # INPUT PARAMETERS
    # ===========================================
    st.subheader("📝 Input Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🏠 Property Details**")
        rb_home_price = st.number_input(
            "Home Purchase Price ($)",
            min_value=50000,
            max_value=10000000,
            value=500000,
            step=10000,
            key="rb_home_price"
        )
        rb_down_payment_pct = st.slider(
            "Down Payment (%)",
            min_value=0.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
            key="rb_down_payment_pct"
        ) / 100
        rb_mortgage_rate = st.slider(
            "Mortgage Interest Rate (%)",
            min_value=1.0,
            max_value=15.0,
            value=7.0,
            step=0.125,
            key="rb_mortgage_rate"
        ) / 100
        rb_home_appreciation = st.slider(
            "Annual Home Appreciation (%)",
            min_value=-5.0,
            max_value=15.0,
            value=3.0,
            step=0.5,
            key="rb_home_appreciation"
        ) / 100

    with col2:
        st.markdown("**💰 Rental Details**")
        rb_rent_pct = st.slider(
            "Annual Rent (% of Home Price)",
            min_value=1.0,
            max_value=15.0,
            value=6.0,
            step=0.25,
            help="Typical range: 4-8% of home value annually",
            key="rb_rent_pct"
        ) / 100
        # Calculate monthly rent from percentage
        rb_annual_rent_calc = rb_home_price * rb_rent_pct
        rb_monthly_rent = rb_annual_rent_calc / 12
        st.markdown(f"**Calculated Monthly Rent: ${rb_monthly_rent:,.0f}**")
        st.markdown(f"*(Annual: ${rb_annual_rent_calc:,.0f})*")

        rb_rent_increase = st.slider(
            "Annual Rent Increase (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="rb_rent_increase"
        ) / 100
        rb_renters_insurance = st.number_input(
            "Annual Renters Insurance ($)",
            min_value=0,
            max_value=5000,
            value=300,
            step=50,
            key="rb_renters_insurance"
        )

    with col3:
        st.markdown("**📈 Investment & Savings**")
        rb_investment_return = st.slider(
            "Annual Investment Return (%)",
            min_value=0.0,
            max_value=15.0,
            value=7.0,
            step=0.5,
            key="rb_investment_return"
        ) / 100
        rb_inflation_rate = st.slider(
            "Annual Inflation Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=2.5,
            step=0.5,
            key="rb_inflation_rate"
        ) / 100

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🏦 Homeowner Costs**")
        rb_property_tax_rate = st.slider(
            "Property Tax Rate (% of home value)",
            min_value=0.0,
            max_value=5.0,
            value=1.25,
            step=0.05,
            key="rb_property_tax_rate"
        ) / 100
        rb_maintenance_rate = st.slider(
            "Annual Maintenance (% of home value)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.25,
            key="rb_maintenance_rate"
        ) / 100
        rb_home_insurance_rate = st.slider(
            "Home Insurance (% of home value)",
            min_value=0.0,
            max_value=2.0,
            value=0.5,
            step=0.1,
            key="rb_home_insurance_rate"
        ) / 100
        rb_hoa_monthly = st.number_input(
            "Monthly HOA Fees ($)",
            min_value=0,
            max_value=2000,
            value=0,
            step=50,
            key="rb_hoa_monthly"
        )

        st.markdown("**🔒 Mortgage Insurance (PMI)**")
        rb_pmi_rate = st.slider(
            "PMI Rate (% of loan, annual)",
            min_value=0.0,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Typically 0.3% - 1.5% of loan amount. Only applies when LTV > 78%",
            key="rb_pmi_rate"
        ) / 100

    with col2:
        st.markdown("**🚚 Moving & Transaction Costs**")
        rb_years_before_move = st.slider(
            "Years Before Moving (on average)",
            min_value=1,
            max_value=30,
            value=7,
            step=1,
            key="rb_years_before_move"
        )
        rb_buying_costs_pct = st.slider(
            "Buying Closing Costs (% of price)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="rb_buying_costs_pct"
        ) / 100
        rb_selling_costs_pct = st.slider(
            "Selling Costs (% of sale price)",
            min_value=0.0,
            max_value=10.0,
            value=6.0,
            step=0.5,
            key="rb_selling_costs_pct"
        ) / 100
        rb_moving_cost = st.number_input(
            "Moving Cost Each Time ($)",
            min_value=0,
            max_value=50000,
            value=5000,
            step=500,
            key="rb_moving_cost"
        )

    with col3:
        st.markdown("**📋 Tax Information**")
        rb_marginal_tax_rate = st.slider(
            "Marginal Tax Rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=25.0,
            step=1.0,
            key="rb_marginal_tax_rate"
        ) / 100
        rb_itemize_deductions = st.checkbox(
            "Itemize Deductions (mortgage interest)?",
            value=True,
            key="rb_itemize_deductions"
        )
        rb_capital_gains_rate = st.slider(
            "Capital Gains Tax Rate (%)",
            min_value=0.0,
            max_value=30.0,
            value=15.0,
            step=1.0,
            key="rb_capital_gains_rate"
        ) / 100
        rb_cap_gains_exclusion = st.number_input(
            "Capital Gains Exclusion ($)",
            min_value=0,
            max_value=1000000,
            value=250000,
            step=50000,
            help="$250k single / $500k married",
            key="rb_cap_gains_exclusion"
        )

    # ===========================================
    # CALCULATIONS
    # ===========================================

    # Derived values
    rb_down_payment = rb_home_price * rb_down_payment_pct
    rb_loan_amount = rb_home_price - rb_down_payment
    rb_monthly_rate = rb_mortgage_rate / 12
    rb_num_payments = 360  # 30 years

    # Initial LTV
    rb_initial_ltv = rb_loan_amount / rb_home_price if rb_home_price > 0 else 0

    # Monthly mortgage payment (P&I)
    if rb_loan_amount > 0 and rb_monthly_rate > 0:
        rb_monthly_mortgage = rb_loan_amount * (rb_monthly_rate * (1 + rb_monthly_rate)**rb_num_payments) / ((1 + rb_monthly_rate)**rb_num_payments - 1)
    else:
        rb_monthly_mortgage = 0

    # Initial closing costs for buying
    rb_initial_buying_costs = rb_home_price * rb_buying_costs_pct

    # Initialize tracking arrays
    years = 30

    # BUYING scenario arrays
    buy_home_value = np.zeros(years + 1)
    buy_loan_balance = np.zeros(years + 1)
    buy_equity = np.zeros(years + 1)
    buy_ltv = np.zeros(years + 1)
    buy_annual_mortgage = np.zeros(years)
    buy_annual_interest = np.zeros(years)
    buy_annual_principal = np.zeros(years)
    buy_annual_property_tax = np.zeros(years)
    buy_annual_maintenance = np.zeros(years)
    buy_annual_insurance = np.zeros(years)
    buy_annual_hoa = np.zeros(years)
    buy_annual_pmi = np.zeros(years)
    buy_tax_savings = np.zeros(years)
    buy_transaction_costs = np.zeros(years)
    buy_total_cost = np.zeros(years)
    buy_net_worth = np.zeros(years + 1)

    # RENTING scenario arrays
    rent_annual_rent = np.zeros(years)
    rent_annual_insurance = np.zeros(years)
    rent_investment_balance = np.zeros(years + 1)
    rent_total_cost = np.zeros(years)
    rent_net_worth = np.zeros(years + 1)
    rent_moving_costs = np.zeros(years)

    # Initial values
    buy_home_value[0] = rb_home_price
    buy_loan_balance[0] = rb_loan_amount
    buy_equity[0] = rb_down_payment
    buy_ltv[0] = rb_initial_ltv

    # Renter invests the down payment + closing costs they didn't spend
    rent_investment_balance[0] = rb_down_payment + rb_initial_buying_costs

    # Initial net worth
    buy_net_worth[0] = buy_equity[0] - rb_initial_buying_costs
    rent_net_worth[0] = rent_investment_balance[0]

    # Track loan balance month by month for accurate interest calculation
    current_loan_balance = rb_loan_amount
    original_home_price = rb_home_price

    # Year-by-year simulation
    for year in range(years):
        # ===========================================
        # BUYING SCENARIO
        # ===========================================

        # Home appreciation
        buy_home_value[year + 1] = buy_home_value[year] * (1 + rb_home_appreciation)

        # Calculate mortgage payments for the year (month by month for accuracy)
        annual_interest = 0
        annual_principal = 0
        annual_pmi = 0

        for month in range(12):
            if current_loan_balance > 0:
                interest_payment = current_loan_balance * rb_monthly_rate
                principal_payment = min(rb_monthly_mortgage - interest_payment, current_loan_balance)
                annual_interest += interest_payment
                annual_principal += principal_payment

                # PMI calculation
                current_ltv = current_loan_balance / original_home_price
                if current_ltv > 0.78:
                    monthly_pmi = (current_loan_balance * rb_pmi_rate) / 12
                    annual_pmi += monthly_pmi

                current_loan_balance -= principal_payment

        buy_annual_mortgage[year] = rb_monthly_mortgage * 12
        buy_annual_interest[year] = annual_interest
        buy_annual_principal[year] = annual_principal
        buy_annual_pmi[year] = annual_pmi
        buy_loan_balance[year + 1] = max(0, current_loan_balance)

        # Calculate LTV at end of year
        buy_ltv[year + 1] = buy_loan_balance[year + 1] / original_home_price if original_home_price > 0 else 0

        # Property costs
        buy_annual_property_tax[year] = buy_home_value[year] * rb_property_tax_rate
        buy_annual_maintenance[year] = buy_home_value[year] * rb_maintenance_rate
        buy_annual_insurance[year] = buy_home_value[year] * rb_home_insurance_rate
        buy_annual_hoa[year] = rb_hoa_monthly * 12

        # Tax savings
        if rb_itemize_deductions:
            buy_tax_savings[year] = buy_annual_interest[year] * rb_marginal_tax_rate

        # Transaction costs when moving
        if rb_years_before_move > 0 and (year + 1) % rb_years_before_move == 0 and year < years - 1:
            selling_costs = buy_home_value[year + 1] * rb_selling_costs_pct
            buying_costs = buy_home_value[year + 1] * rb_buying_costs_pct
            buy_transaction_costs[year] = selling_costs + buying_costs + rb_moving_cost
            original_home_price = buy_home_value[year + 1]

        # Total annual cost
        buy_total_cost[year] = (
            buy_annual_mortgage[year] +
            buy_annual_property_tax[year] +
            buy_annual_maintenance[year] +
            buy_annual_insurance[year] +
            buy_annual_hoa[year] +
            buy_annual_pmi[year] -
            buy_tax_savings[year] +
            buy_transaction_costs[year]
        )

        # Equity
        buy_equity[year + 1] = buy_home_value[year + 1] - buy_loan_balance[year + 1]

        # Net worth
        cumulative_transaction_costs = np.sum(buy_transaction_costs[:year + 1])
        buy_net_worth[year + 1] = buy_equity[year + 1] - cumulative_transaction_costs

        # ===========================================
        # RENTING SCENARIO
        # ===========================================

        rent_annual_rent[year] = rb_monthly_rent * 12 * ((1 + rb_rent_increase) ** year)
        rent_annual_insurance[year] = rb_renters_insurance * ((1 + rb_inflation_rate) ** year)

        # Moving costs for renters
        if rb_years_before_move > 0 and (year + 1) % rb_years_before_move == 0 and year < years - 1:
            rent_moving_costs[year] = rb_moving_cost

        rent_total_cost[year] = rent_annual_rent[year] + rent_annual_insurance[year] + rent_moving_costs[year]

        # Renter invests the difference
        cost_difference = buy_total_cost[year] - rent_total_cost[year]

        rent_investment_balance[year + 1] = rent_investment_balance[year] * (1 + rb_investment_return)
        if cost_difference > 0:
            rent_investment_balance[year + 1] += cost_difference
        else:
            rent_investment_balance[year + 1] += cost_difference

        rent_net_worth[year + 1] = rent_investment_balance[year + 1]

    # ===========================================
    # FINAL CALCULATIONS
    # ===========================================

    total_appreciation = buy_home_value[years] - rb_home_price
    taxable_gain = max(0, total_appreciation - rb_cap_gains_exclusion)
    capital_gains_tax = taxable_gain * rb_capital_gains_rate

    final_selling_costs = buy_home_value[years] * rb_selling_costs_pct

    buy_final_net_worth = buy_equity[years] - final_selling_costs - capital_gains_tax

    rent_total_contributions = rb_down_payment + rb_initial_buying_costs + np.sum(np.maximum(0, buy_total_cost - rent_total_cost))
    rent_investment_gains = rent_investment_balance[years] - rent_total_contributions
    rent_capital_gains_tax = max(0, rent_investment_gains) * rb_capital_gains_rate
    rent_final_net_worth = rent_investment_balance[years] - rent_capital_gains_tax

    total_pmi_paid = np.sum(buy_annual_pmi)

    pmi_dropoff_year = None
    for i in range(years + 1):
        if buy_ltv[i] <= 0.78:
            pmi_dropoff_year = i
            break

    # ===========================================
    # DISPLAY RESULTS
    # ===========================================

    st.markdown("---")
    st.subheader("📊 30-Year Analysis Results")

    # PMI Info box
    if rb_initial_ltv > 0.78:
        if pmi_dropoff_year:
            st.info(f"🔒 **PMI Info:** Starting LTV is {rb_initial_ltv*100:.1f}%. PMI of ${buy_annual_pmi[0]:,.0f}/year applies until LTV reaches 78% (Year {pmi_dropoff_year}). Total PMI paid: ${total_pmi_paid:,.0f}")
        else:
            st.info(f"🔒 **PMI Info:** Starting LTV is {rb_initial_ltv*100:.1f}%. PMI applies for the full 30 years. Total PMI paid: ${total_pmi_paid:,.0f}")
    else:
        st.success(f"✅ **No PMI Required:** Down payment of {rb_down_payment_pct*100:.0f}% results in LTV of {rb_initial_ltv*100:.1f}%, below the 78% threshold.")

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🏠 Buying")
        st.metric("Final Home Value", f"${buy_home_value[years]:,.0f}")
        st.metric("Final Loan Balance", f"${buy_loan_balance[years]:,.0f}")
        st.metric("Final Equity", f"${buy_equity[years]:,.0f}")
        st.metric("Less: Final Selling Costs", f"-${final_selling_costs:,.0f}")
        st.metric("Less: Capital Gains Tax", f"-${capital_gains_tax:,.0f}")
        st.metric("**Net Worth (After Sale)**", f"${buy_final_net_worth:,.0f}")

    with col2:
        st.markdown("### 🏢 Renting")
        st.metric("Investment Balance", f"${rent_investment_balance[years]:,.0f}")
        st.metric("Total Contributions", f"${rent_total_contributions:,.0f}")
        st.metric("Investment Gains", f"${rent_investment_gains:,.0f}")
        st.metric("Less: Capital Gains Tax", f"-${rent_capital_gains_tax:,.0f}")
        st.metric("**Net Worth (After Tax)**", f"${rent_final_net_worth:,.0f}")

    with col3:
        st.markdown("### 📈 Comparison")
        difference = buy_final_net_worth - rent_final_net_worth
        if difference > 0:
            st.metric("**Buying Advantage**", f"${difference:,.0f}", delta=f"Buying wins by ${difference:,.0f}")
        else:
            st.metric("**Renting Advantage**", f"${-difference:,.0f}", delta=f"Renting wins by ${-difference:,.0f}")

        st.metric("Total Paid (Buying)", f"${np.sum(buy_total_cost):,.0f}")
        st.metric("Total Paid (Renting)", f"${np.sum(rent_total_cost):,.0f}")
        st.metric("Total PMI Paid", f"${total_pmi_paid:,.0f}")

    # ===========================================
    # CHARTS
    # ===========================================

    st.markdown("---")
    st.subheader("📈 Net Worth Over Time")

    # Create DataFrame for plotting
    chart_data = pd.DataFrame({
        'Year': range(years + 1),
        'Buying Net Worth': buy_net_worth,
        'Renting Net Worth': rent_net_worth
    })

    fig_networth = go.Figure()
    fig_networth.add_trace(go.Scatter(
        x=chart_data['Year'],
        y=chart_data['Buying Net Worth'],
        mode='lines',
        name='Buying',
        line=dict(color='green', width=3)
    ))
    fig_networth.add_trace(go.Scatter(
        x=chart_data['Year'],
        y=chart_data['Renting Net Worth'],
        mode='lines',
        name='Renting',
        line=dict(color='blue', width=3)
    ))
    fig_networth.update_layout(
        title='Net Worth Comparison: Buying vs Renting',
        xaxis_title='Year',
        yaxis_title='Net Worth ($)',
        hovermode='x unified',
        yaxis_tickformat='$,.0f'
    )
    st.plotly_chart(fig_networth, use_container_width=True)

    # Crossover point
    crossover_year = None
    for i in range(1, years + 1):
        if buy_net_worth[i] > rent_net_worth[i] and buy_net_worth[i-1] <= rent_net_worth[i-1]:
            crossover_year = i
            break
        elif buy_net_worth[i] < rent_net_worth[i] and buy_net_worth[i-1] >= rent_net_worth[i-1]:
            crossover_year = i
            break

    if crossover_year:
        st.info(f"📍 Crossover point: Year {crossover_year} - After this point, {'buying' if buy_net_worth[crossover_year] > rent_net_worth[crossover_year] else 'renting'} becomes more advantageous.")

    # ===========================================
    # LTV CHART
    # ===========================================

    st.markdown("---")
    st.subheader("📉 Loan-to-Value (LTV) Over Time")

    fig_ltv = go.Figure()
    fig_ltv.add_trace(go.Scatter(
        x=list(range(years + 1)),
        y=buy_ltv * 100,
        mode='lines',
        name='LTV %',
        line=dict(color='purple', width=3)
    ))
    fig_ltv.add_hline(y=78, line_dash="dash", line_color="red", annotation_text="78% PMI Threshold")
    fig_ltv.update_layout(
        title='LTV Ratio Over Time (PMI drops at 78%)',
        xaxis_title='Year',
        yaxis_title='LTV (%)',
        hovermode='x unified',
        yaxis_tickformat='.1f'
    )
    st.plotly_chart(fig_ltv, use_container_width=True)

    # ===========================================
    # ANNUAL COST BREAKDOWN
    # ===========================================

    st.markdown("---")
    st.subheader("💸 Annual Cost Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Year 1 Costs - Buying")
        buy_year1_data = {
            'Category': ['Mortgage (P&I)', 'Property Tax', 'Maintenance', 'Insurance', 'HOA', 'PMI', 'Tax Savings', 'Net Cost'],
            'Amount': [
                buy_annual_mortgage[0],
                buy_annual_property_tax[0],
                buy_annual_maintenance[0],
                buy_annual_insurance[0],
                buy_annual_hoa[0],
                buy_annual_pmi[0],
                -buy_tax_savings[0],
                buy_total_cost[0]
            ]
        }
        st.dataframe(pd.DataFrame(buy_year1_data).style.format({'Amount': '${:,.0f}'}), hide_index=True)

    with col2:
        st.markdown("### Year 1 Costs - Renting")
        rent_year1_data = {
            'Category': ['Rent', 'Renters Insurance', 'Total Cost'],
            'Amount': [
                rent_annual_rent[0],
                rent_annual_insurance[0],
                rent_total_cost[0]
            ]
        }
        st.dataframe(pd.DataFrame(rent_year1_data).style.format({'Amount': '${:,.0f}'}), hide_index=True)

    # ===========================================
    # DETAILED YEARLY TABLE
    # ===========================================

    st.markdown("---")
    with st.expander("📋 Detailed Year-by-Year Analysis"):
        detailed_data = pd.DataFrame({
            'Year': range(1, years + 1),
            'Home Value': buy_home_value[1:],
            'Loan Balance': buy_loan_balance[1:],
            'LTV %': buy_ltv[1:] * 100,
            'PMI': buy_annual_pmi,
            'Buy Equity': buy_equity[1:],
            'Buy Annual Cost': buy_total_cost,
            'Buy Net Worth': buy_net_worth[1:],
            'Rent Annual Cost': rent_total_cost,
            'Rent Investments': rent_investment_balance[1:],
            'Rent Net Worth': rent_net_worth[1:],
            'Buy vs Rent': buy_net_worth[1:] - rent_net_worth[1:]
        })

        st.dataframe(
            detailed_data.style.format({
                'Home Value': '${:,.0f}',
                'Loan Balance': '${:,.0f}',
                'LTV %': '{:.1f}%',
                'PMI': '${:,.0f}',
                'Buy Equity': '${:,.0f}',
                'Buy Annual Cost': '${:,.0f}',
                'Buy Net Worth': '${:,.0f}',
                'Rent Annual Cost': '${:,.0f}',
                'Rent Investments': '${:,.0f}',
                'Rent Net Worth': '${:,.0f}',
                'Buy vs Rent': '${:,.0f}'
            }),
            hide_index=True,
            use_container_width=True
        )

    # ===========================================
    # KEY ASSUMPTIONS
    # ===========================================

    st.markdown("---")
    with st.expander("📝 Key Assumptions & Notes"):
        st.markdown(f"""
        **Buying Scenario:**
        - Home price: ${rb_home_price:,.0f}
        - Down payment: ${rb_down_payment:,.0f} ({rb_down_payment_pct*100:.0f}%)
        - Loan amount: ${rb_loan_amount:,.0f}
        - Initial LTV: {rb_initial_ltv*100:.1f}%
        - Monthly mortgage payment (P&I): ${rb_monthly_mortgage:,.2f}
        - Initial closing costs: ${rb_initial_buying_costs:,.0f}
        - PMI rate: {rb_pmi_rate*100:.2f}% annually (until LTV ≤ 78%)
        - PMI drops off: {'Year ' + str(pmi_dropoff_year) if pmi_dropoff_year else 'Never (LTV stays above 78%)' if rb_initial_ltv > 0.78 else 'N/A (no PMI required)'}
        - Total PMI paid: ${total_pmi_paid:,.0f}
        - Number of moves in 30 years: {30 // rb_years_before_move if rb_years_before_move > 0 else 0}
        - Each move costs: ${rb_moving_cost:,.0f} + {rb_selling_costs_pct*100:.1f}% selling + {rb_buying_costs_pct*100:.1f}% buying

        **Renting Scenario:**
        - Monthly rent: ${rb_monthly_rent:,.0f} ({rb_rent_pct*100:.1f}% of home price annually)
        - Initial investment: ${rb_down_payment + rb_initial_buying_costs:,.0f} (down payment + closing costs saved)
        - Renter invests any monthly savings vs buying costs
        - Investment returns compounded annually at {rb_investment_return*100:.1f}%

        **Tax Treatment:**
        - Mortgage interest deduction: {'Yes' if rb_itemize_deductions else 'No'}
        - Capital gains exclusion on home sale: ${rb_cap_gains_exclusion:,.0f}
        - Capital gains tax rate: {rb_capital_gains_rate*100:.0f}%

        **PMI Rules:**
        - PMI is required when LTV > 78%
        - PMI is calculated based on the ORIGINAL purchase price (not current market value)
        - PMI automatically drops off when loan balance reaches 78% of original purchase price

        **Notes:**
        - This is a simplified model. Actual results will vary.
        - Does not account for: opportunity cost of time spent on maintenance, emotional factors
        - Home appreciation and investment returns are not guaranteed
        - Tax laws may change over time
        """)
