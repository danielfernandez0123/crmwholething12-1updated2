"""
Other Tools Page - Advanced Analysis Tools from ADL/NBER Refinancing Model

Contains all the analysis tools from the original streamlit_app.py:
- Main Calculator (Optimal Refinancing Results)
- Sensitivity Analysis
- Paper Explanation
- Additional Tools
- Points Analysis
- ENPV Analysis
- Net Benefit Timeline
- Value Matching Debug

Users can either:
1. Import a client from their database to use their parameters
2. Manually input parameters for analysis
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy.special import lambertw
import math

from database import get_clients_by_user, get_client_by_id, get_admin_settings


# =============================================================================
# CORE CALCULATION FUNCTIONS (EXACT from original streamlit_app.py)
# =============================================================================

def calculate_lambda(mu, i0, Gamma, pi):
    """Calculate λ (lambda) as per page 19 and Appendix C of the paper"""
    if i0 * Gamma < 100:  # Prevent overflow
        lambda_val = mu + i0 / (np.exp(i0 * Gamma) - 1) + pi
    else:
        lambda_val = mu + pi  # Simplified for very large values
    return lambda_val


def calculate_kappa(M, points, fixed_cost, tau):
    """Calculate κ(M) - tax-adjusted refinancing cost (Appendix A)"""
    kappa = fixed_cost + points * M
    return kappa


def calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa, tau):
    """
    Calculate the optimal refinancing threshold x* using Lambert W function
    As per Theorem 2 (page 13) and equation (12)
    """
    # Calculate ψ (psi) as per equation in Theorem 2
    psi = np.sqrt(2 * (rho + lambda_val)) / sigma

    # Calculate φ (phi) as per equation in Theorem 2
    C_M = kappa / (1 - tau)  # Normalized refinancing cost
    phi = 1 + psi * (rho + lambda_val) * C_M / M

    # Calculate x* using Lambert W function (equation 12)
    try:
        w_arg = -np.exp(-phi)
        w_val = np.real(lambertw(w_arg, k=0))
        x_star = (1 / psi) * (phi + w_val)
    except:
        x_star = np.nan

    return x_star, psi, phi, C_M


def calculate_square_root_approximation(M, rho, lambda_val, sigma, kappa, tau):
    """
    Calculate the square root approximation (second-order Taylor expansion)
    As per Section 2.3 (page 16-17)
    """
    sqrt_term = sigma * np.sqrt(kappa / (M * (1 - tau))) * np.sqrt(2 * (rho + lambda_val))
    return -sqrt_term


def calculate_npv_threshold(M, rho, lambda_val, kappa, tau):
    """
    Calculate the NPV break-even threshold
    As per Definition 3 (page 16)
    """
    C_M = kappa / (1 - tau)
    x_npv = -(rho + lambda_val) * C_M / M
    return x_npv


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_other_tools(user_id: int):
    """Render the Other Tools page with all advanced analysis"""
    st.header("Advanced Analysis Tools")
    st.markdown("Based on the NBER Working Paper 13487 by Agarwal, Driscoll, and Laibson (2007)")

    # Parameter Input Section
    st.markdown("---")
    params = render_parameter_input(user_id)

    if params is None:
        st.info("Please configure parameters above to use the analysis tools.")
        return

    # Extract parameters
    M = params['M']
    i0 = params['i0']
    Gamma = params['Gamma']
    rho = params['rho']
    sigma = params['sigma']
    tau = params['tau']
    mu = params['mu']
    pi = params['pi']
    points = params['points']
    fixed_cost = params['fixed_cost']

    # Calculate derived values (same as original)
    lambda_val = calculate_lambda(mu, i0, Gamma, pi)
    kappa = calculate_kappa(M, points, fixed_cost, tau)
    x_star, psi, phi, C_M = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa, tau)
    x_star_sqrt = calculate_square_root_approximation(M, rho, lambda_val, sigma, kappa, tau)
    x_npv = calculate_npv_threshold(M, rho, lambda_val, kappa, tau)

    # Convert to basis points for display
    x_star_bp = -x_star * 10000 if not np.isnan(x_star) else np.nan
    x_star_sqrt_bp = -x_star_sqrt * 10000
    x_npv_bp = -x_npv * 10000

    # Store all calculated values for tabs
    calc = {
        'M': M, 'i0': i0, 'Gamma': Gamma, 'rho': rho, 'sigma': sigma,
        'tau': tau, 'mu': mu, 'pi': pi, 'points': points, 'fixed_cost': fixed_cost,
        'lambda_val': lambda_val, 'kappa': kappa, 'x_star': x_star,
        'psi': psi, 'phi': phi, 'C_M': C_M,
        'x_star_bp': x_star_bp, 'x_star_sqrt_bp': x_star_sqrt_bp, 'x_npv_bp': x_npv_bp
    }

    st.markdown("---")

    # Create tabs (matching original script structure)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🏠 Main Calculator",
        "📈 Sensitivity Analysis",
        "📖 Paper Explanation",
        "🔧 Additional Tools",
        "💰 Points Analysis",
        "📊 ENPV Analysis",
        "Net Benefit Timeline",
        "Value Matching Debug"
    ])

    with tab1:
        render_main_calculator(calc)

    with tab2:
        render_sensitivity_analysis(calc)

    with tab3:
        render_paper_explanation(calc)

    with tab4:
        render_additional_tools(calc)

    with tab5:
        render_points_analysis(calc)

    with tab6:
        render_enpv_analysis(calc)

    with tab7:
        render_net_benefit_timeline(calc)

    with tab8:
        render_value_matching_debug(calc)


# =============================================================================
# PARAMETER INPUT SECTION
# =============================================================================

def render_parameter_input(user_id: int):
    """Render parameter input section with option to import from database"""

    st.subheader("📊 Input Parameters")

    # Option to import from database or manual input
    input_method = st.radio(
        "Parameter Source:",
        ["Manual Input", "Import from Client Database"],
        horizontal=True
    )

    if input_method == "Import from Client Database":
        clients = get_clients_by_user(user_id)

        if not clients:
            st.warning("No clients found. Add clients first or use manual input.")
            return None

        # Client selector
        client_options = {f"{c['first_name']} {c['last_name']}": c['id'] for c in clients}
        selected_name = st.selectbox("Select Client:", list(client_options.keys()))

        if selected_name:
            client = get_client_by_id(client_options[selected_name])

            if client:
                st.success(f"Loaded parameters for {selected_name}")

                return {
                    'M': client.get('current_mortgage_balance', 250000),
                    'i0': client.get('current_mortgage_rate', 0.06),
                    'Gamma': client.get('remaining_years', 25),
                    'rho': client.get('discount_rate', 0.05),
                    'sigma': client.get('rate_volatility', 0.0109),
                    'tau': client.get('tax_rate', 0.28),
                    'mu': client.get('prob_moving', 0.10),
                    'pi': client.get('inflation_rate', 0.03),
                    'points': client.get('points_pct', 0.01),
                    'fixed_cost': client.get('fixed_refi_cost', 2000),
                }

        return None

    else:
        # Manual input - EXACT same inputs as original sidebar
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Mortgage Information**")
            M = st.number_input(
                "Remaining Mortgage Value ($)",
                min_value=10000,
                max_value=5000000,
                value=250000,
                step=10000,
                help="The remaining principal balance on your mortgage (M in the paper)"
            )

            i0 = st.number_input(
                "Original Mortgage Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=6.0,
                step=0.1,
                help="The interest rate on your current mortgage (i₀ in the paper)"
            ) / 100

            Gamma = st.number_input(
                "Remaining Mortgage Years",
                min_value=1,
                max_value=30,
                value=25,
                help="Years remaining on mortgage (Γ in the paper)"
            )

            st.markdown("**Economic Parameters**")
            rho = st.number_input(
                "Real Discount Rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=5.0,
                step=0.5,
                help="Your personal discount rate (ρ in the paper, page 17)"
            ) / 100

            sigma = st.number_input(
                "Interest Rate Volatility",
                min_value=0.001,
                max_value=0.05,
                value=0.0109,
                step=0.001,
                format="%.4f",
                help="Annual standard deviation of mortgage rate (σ in the paper, calibrated on page 18)"
            )

        with col2:
            st.markdown("**Tax & Cost Information**")
            tau = st.number_input(
                "Marginal Tax Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=28.0,
                step=1.0,
                help="Your marginal tax rate (τ in the paper)"
            ) / 100

            fixed_cost = st.number_input(
                "Fixed Refinancing Cost ($)",
                min_value=0,
                max_value=20000,
                value=2000,
                step=100,
                help="Fixed costs like inspection, title insurance, lawyers (page 17)"
            )

            points = st.number_input(
                "Points (%)",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.1,
                help="Points charged as percentage of mortgage"
            ) / 100

            st.markdown("**Prepayment Parameters**")
            mu = st.number_input(
                "Annual Probability of Moving (%)",
                min_value=0.0,
                max_value=50.0,
                value=10.0,
                step=1.0,
                help="Annual probability of relocating (μ in the paper)"
            ) / 100

            pi = st.number_input(
                "Expected Inflation Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=3.0,
                step=0.5,
                help="Expected inflation rate (π in the paper)"
            ) / 100

        return {
            'M': M, 'i0': i0, 'Gamma': Gamma, 'rho': rho, 'sigma': sigma,
            'tau': tau, 'mu': mu, 'pi': pi, 'points': points, 'fixed_cost': fixed_cost
        }


# =============================================================================
# TAB 1: MAIN CALCULATOR (EXACT from original tab1)
# =============================================================================

def render_main_calculator(calc):
    """Render the main calculator results - EXACT from original tab1"""
    st.header("📊 Optimal Refinancing Results")

    M = calc['M']
    i0 = calc['i0']
    x_star = calc['x_star']
    x_star_bp = calc['x_star_bp']
    x_star_sqrt_bp = calc['x_star_sqrt_bp']
    x_npv_bp = calc['x_npv_bp']
    lambda_val = calc['lambda_val']
    kappa = calc['kappa']
    psi = calc['psi']
    phi = calc['phi']
    C_M = calc['C_M']

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Exact Optimal Threshold",
            f"{x_star_bp:.0f} bps" if not np.isnan(x_star_bp) else "N/A",
            help="Refinance when current rate is this many basis points below original rate (Theorem 2, page 13)"
        )

    with col2:
        st.metric(
            "Square Root Approximation",
            f"{x_star_sqrt_bp:.0f} bps",
            help="Second-order approximation from equation (15), page 16"
        )

    with col3:
        st.metric(
            "NPV Rule (No Option Value)",
            f"{x_npv_bp:.0f} bps",
            help="Simple break-even analysis ignoring option value (Definition 3, page 16)"
        )

    st.markdown("---")

    # Show key results
    new_rate = i0 - abs(x_star) if not np.isnan(x_star) else None

    if new_rate and not np.isnan(x_star):
        st.markdown(f"""
        <div style='background-color: #e8f4ea; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #4CAF50; margin: 1rem 0;'>
        <h3>📌 Key Result</h3>
        <p style='font-size: 1.2rem;'>
        With your current mortgage rate of <b>{i0*100:.2f}%</b>, you should refinance when market rates drop to
        <b style='color: #2e7d32; font-size: 1.5rem;'>{new_rate*100:.2f}%</b> or lower.
        </p>
        <p>This is a rate drop of <b>{x_star_bp:.0f} basis points</b> ({x_star_bp/100:.2f} percentage points)</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📐 Model Parameters")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **Inputs:**
        - M (Mortgage Balance) = **${M:,.0f}**
        - i₀ (Original Rate) = **{i0*100:.2f}%**
        - ρ (Discount Rate) = **{calc['rho']*100:.1f}%**
        - σ (Volatility) = **{calc['sigma']:.4f}**
        - τ (Tax Rate) = **{calc['tau']*100:.0f}%**
        - μ (Moving Probability) = **{calc['mu']*100:.0f}%**
        - π (Inflation) = **{calc['pi']*100:.1f}%**
        - Γ (Years Remaining) = **{calc['Gamma']}**
        """)

    with col2:
        st.markdown(f"""
        **Calculated Values:**
        - λ (Lambda) = **{lambda_val:.4f}**
        - κ (Refinancing Cost) = **${kappa:,.0f}**
        - ψ (Psi) = **{psi:.4f}**
        - φ (Phi) = **{phi:.4f}**
        - C(M) = **${C_M:,.0f}**
        - x* = **{x_star:.6f}** ({x_star_bp:.0f} bps)
        """)

    # Add interpretation
    st.markdown("---")
    st.info("""
    **Interpretation:**
    - The **Exact Optimal Threshold** accounts for the option value of waiting for potentially better rates
    - The **NPV Rule** only looks at immediate break-even, ignoring future opportunities
    - The difference between these (typically 50-100+ bps) represents the value of waiting
    - Higher volatility → larger difference (more value in waiting)
    """)


# =============================================================================
# TAB 2: SENSITIVITY ANALYSIS (EXACT from original tab2)
# =============================================================================

def render_sensitivity_analysis(calc):
    """Render sensitivity analysis - EXACT from original tab2"""
    st.header("📈 Sensitivity Analysis")
    st.markdown("Explore how different parameters affect the optimal refinancing threshold")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    sigma = calc['sigma']
    tau = calc['tau']
    mu = calc['mu']
    pi = calc['pi']
    points = calc['points']
    fixed_cost = calc['fixed_cost']
    lambda_val = calc['lambda_val']
    kappa = calc['kappa']
    x_star_bp = calc['x_star_bp']

    analysis_type = st.selectbox(
        "Select Analysis",
        ["Mortgage Size vs Threshold (Table 1)",
         "Interest Rate Volatility vs Threshold",
         "Tax Rate vs Threshold (Table 2)",
         "Expected Time to Move vs Threshold (Table 3)",
         "Refinancing Costs vs Threshold (Table 4)"]
    )

    if analysis_type == "Mortgage Size vs Threshold (Table 1)":
        st.subheader("Table 1: Effect of Mortgage Size on Optimal Refinancing Threshold")

        M_values = np.array([100000, 150000, 200000, 250000, 300000, 400000, 500000, 750000, 1000000])
        results = []

        for M_test in M_values:
            kappa_test = calculate_kappa(M_test, points, fixed_cost, tau)
            x_exact, _, _, _ = calculate_optimal_threshold(M_test, rho, lambda_val, sigma, kappa_test, tau)
            x_sqrt = calculate_square_root_approximation(M_test, rho, lambda_val, sigma, kappa_test, tau)
            x_npv = calculate_npv_threshold(M_test, rho, lambda_val, kappa_test, tau)

            results.append({
                'Mortgage': f"${M_test:,.0f}",
                'Exact Optimal (bps)': -x_exact * 10000 if not np.isnan(x_exact) else np.nan,
                '2nd Order Approx (bps)': -x_sqrt * 10000,
                'NPV Rule (bps)': -x_npv * 10000
            })

        df = pd.DataFrame(results)

        # Style the dataframe
        st.dataframe(df.style.format({
            'Exact Optimal (bps)': '{:.0f}',
            '2nd Order Approx (bps)': '{:.0f}',
            'NPV Rule (bps)': '{:.0f}'
        }), use_container_width=True, hide_index=True)

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=M_values/1000, y=[-calculate_optimal_threshold(m, rho, lambda_val, sigma, calculate_kappa(m, points, fixed_cost, tau), tau)[0]*10000 for m in M_values],
                                mode='lines+markers', name='Exact Optimal'))
        fig.add_trace(go.Scatter(x=M_values/1000, y=[-calculate_square_root_approximation(m, rho, lambda_val, sigma, calculate_kappa(m, points, fixed_cost, tau), tau)*10000 for m in M_values],
                                mode='lines+markers', name='Square Root Approx', line=dict(dash='dash')))
        fig.add_trace(go.Scatter(x=M_values/1000, y=[-calculate_npv_threshold(m, rho, lambda_val, calculate_kappa(m, points, fixed_cost, tau), tau)*10000 for m in M_values],
                                mode='lines+markers', name='NPV Rule', line=dict(dash='dot')))

        # Mark current
        fig.add_trace(go.Scatter(x=[M/1000], y=[x_star_bp], mode='markers', name='Current',
                                marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Refinancing Threshold vs Mortgage Size",
            xaxis_title="Mortgage Size ($1000s)",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Key Insight (Page 17):** Larger mortgages require smaller rate drops to refinance.
        This is because the fixed costs become a smaller percentage of the loan.
        """)

    elif analysis_type == "Interest Rate Volatility vs Threshold":
        st.subheader("Effect of Interest Rate Volatility on Optimal Threshold")

        sigma_values = np.linspace(0.005, 0.025, 50)
        results_exact = []
        results_sqrt = []

        for sigma_test in sigma_values:
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma_test, kappa, tau)
            x_sqrt = calculate_square_root_approximation(M, rho, lambda_val, sigma_test, kappa, tau)
            results_exact.append(-x_exact * 10000 if not np.isnan(x_exact) else np.nan)
            results_sqrt.append(-x_sqrt * 10000)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sigma_values, y=results_exact, mode='lines', name='Exact Optimal'))
        fig.add_trace(go.Scatter(x=sigma_values, y=results_sqrt, mode='lines', name='Square Root Approx', line=dict(dash='dash')))

        # Mark current
        fig.add_trace(go.Scatter(x=[sigma], y=[x_star_bp], mode='markers', name='Current',
                                marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Refinancing Threshold vs Interest Rate Volatility",
            xaxis_title="Volatility (σ)",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Key Insight:** Higher volatility increases the optimal threshold.
        When rates are more volatile, the option to wait becomes more valuable.
        """)

    elif analysis_type == "Tax Rate vs Threshold (Table 2)":
        st.subheader("Table 2: Effect of Tax Rate on Optimal Refinancing Threshold")

        tau_values = np.array([0, 0.10, 0.15, 0.22, 0.24, 0.28, 0.32, 0.35, 0.37])
        results = []

        for tau_test in tau_values:
            kappa_test = calculate_kappa(M, points, fixed_cost, tau_test)
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa_test, tau_test)

            results.append({
                'Tax Rate': f"{tau_test*100:.0f}%",
                'Optimal Threshold (bps)': -x_exact * 10000 if not np.isnan(x_exact) else np.nan
            })

        df = pd.DataFrame(results)
        st.dataframe(df.style.format({'Optimal Threshold (bps)': '{:.0f}'}), use_container_width=True, hide_index=True)

        # Chart
        fig = go.Figure()
        thresholds = [-calculate_optimal_threshold(M, rho, lambda_val, sigma, calculate_kappa(M, points, fixed_cost, t), t)[0]*10000 for t in tau_values]
        fig.add_trace(go.Bar(x=[f"{t*100:.0f}%" for t in tau_values], y=thresholds))

        fig.update_layout(
            title="Optimal Threshold vs Tax Rate",
            xaxis_title="Marginal Tax Rate",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Key Insight (Page 17):** Higher tax rates increase the optimal threshold.
        The mortgage interest deduction reduces the after-tax benefit of refinancing.
        """)

    elif analysis_type == "Expected Time to Move vs Threshold (Table 3)":
        st.subheader("Table 3: Effect of Expected Time to Move on Optimal Threshold")

        mu_values = np.array([0.05, 0.0667, 0.10, 0.1333, 0.20, 0.25, 0.333])
        expected_years = 1 / mu_values
        results = []

        for mu_test in mu_values:
            lambda_test = calculate_lambda(mu_test, i0, Gamma, pi)
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_test, sigma, kappa, tau)

            results.append({
                'Expected Years': f"{1/mu_test:.1f}",
                'μ': f"{mu_test*100:.1f}%",
                'Optimal Threshold (bps)': -x_exact * 10000 if not np.isnan(x_exact) else np.nan
            })

        df = pd.DataFrame(results)
        st.dataframe(df.style.format({'Optimal Threshold (bps)': '{:.0f}'}), use_container_width=True, hide_index=True)

        # Chart
        fig = go.Figure()
        thresholds = []
        for mu_test in mu_values:
            lambda_test = calculate_lambda(mu_test, i0, Gamma, pi)
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_test, sigma, kappa, tau)
            thresholds.append(-x_exact * 10000 if not np.isnan(x_exact) else np.nan)

        fig.add_trace(go.Scatter(x=expected_years, y=thresholds, mode='lines+markers'))

        # Mark current
        current_expected = 1/mu
        fig.add_trace(go.Scatter(x=[current_expected], y=[x_star_bp], mode='markers', name='Current',
                                marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Optimal Threshold vs Expected Time to Move",
            xaxis_title="Expected Years Until Move",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Key Insight (Page 17):** Longer expected tenure reduces the optimal threshold.
        If you expect to stay in your home longer, you can refinance with smaller rate drops.
        """)

    elif analysis_type == "Refinancing Costs vs Threshold (Table 4)":
        st.subheader("Table 4: Effect of Refinancing Costs on Optimal Threshold")

        # Vary fixed costs
        fixed_cost_values = np.array([0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000])
        results = []

        for fc in fixed_cost_values:
            kappa_test = calculate_kappa(M, points, fc, tau)
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa_test, tau)
            x_npv = calculate_npv_threshold(M, rho, lambda_val, kappa_test, tau)

            results.append({
                'Fixed Cost': f"${fc:,.0f}",
                'Total Cost': f"${kappa_test:,.0f}",
                'Optimal Threshold (bps)': -x_exact * 10000 if not np.isnan(x_exact) else np.nan,
                'NPV Rule (bps)': -x_npv * 10000
            })

        df = pd.DataFrame(results)
        st.dataframe(df.style.format({
            'Optimal Threshold (bps)': '{:.0f}',
            'NPV Rule (bps)': '{:.0f}'
        }), use_container_width=True, hide_index=True)

        # Chart
        fig = go.Figure()
        thresholds_exact = []
        thresholds_npv = []

        for fc in fixed_cost_values:
            kappa_test = calculate_kappa(M, points, fc, tau)
            x_exact, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa_test, tau)
            x_npv = calculate_npv_threshold(M, rho, lambda_val, kappa_test, tau)
            thresholds_exact.append(-x_exact * 10000 if not np.isnan(x_exact) else np.nan)
            thresholds_npv.append(-x_npv * 10000)

        fig.add_trace(go.Scatter(x=fixed_cost_values, y=thresholds_exact, mode='lines+markers', name='Exact Optimal'))
        fig.add_trace(go.Scatter(x=fixed_cost_values, y=thresholds_npv, mode='lines+markers', name='NPV Rule', line=dict(dash='dash')))

        # Mark current
        fig.add_trace(go.Scatter(x=[fixed_cost], y=[x_star_bp], mode='markers', name='Current',
                                marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Optimal Threshold vs Fixed Refinancing Costs",
            xaxis_title="Fixed Costs ($)",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Key Insight:** Higher refinancing costs increase the optimal threshold.
        Higher costs require larger rate drops to justify refinancing.
        """)


# =============================================================================
# TAB 3: PAPER EXPLANATION (EXACT from original tab3)
# =============================================================================

def render_paper_explanation(calc):
    """Render paper explanation - EXACT from original tab3"""
    st.header("📖 Paper Explanation")
    st.markdown("Understanding the Agarwal, Driscoll, and Laibson (2007) Model")

    st.markdown("""
    ## The Optimal Mortgage Refinancing Problem

    ### 1. The Core Question
    When should a homeowner refinance their mortgage? This seems simple - refinance when rates drop enough
    to cover closing costs. But this ignores a crucial factor: **the option value of waiting**.

    ### 2. Key Insight: It's an Options Problem
    The right to refinance is like a **perpetual American call option**:
    - You can exercise (refinance) at any time
    - The "strike price" is your current rate
    - The "underlying" is the market mortgage rate
    - The "premium" is the closing costs

    Just like with stock options, **it's often optimal to wait** even when refinancing would be immediately profitable.

    ### 3. The Model Parameters

    | Symbol | Name | Description |
    |--------|------|-------------|
    | M | Mortgage Balance | Remaining principal |
    | i₀ | Original Rate | Your current mortgage rate |
    | ρ | Discount Rate | Your personal time preference |
    | σ | Volatility | How much rates fluctuate |
    | τ | Tax Rate | Marginal income tax rate |
    | μ | Moving Probability | Chance of moving each year |
    | π | Inflation | Expected inflation rate |
    | Γ | Years Remaining | Time left on mortgage |

    ### 4. The Lambda (λ) Parameter
    """)

    st.latex(r"\lambda = \mu + \frac{i_0}{e^{i_0 \Gamma} - 1} + \pi")

    st.markdown("""
    This captures the **expected real rate of mortgage termination** from:
    - Moving (μ)
    - Principal repayment
    - Inflation erosion

    ### 5. The Optimal Threshold Formula
    """)

    st.latex(r"x^* = \frac{1}{\psi}\left[\phi + W(-e^{-\phi})\right]")

    st.markdown("""
    Where:
    """)

    st.latex(r"\psi = \frac{\sqrt{2(\rho + \lambda)}}{\sigma}")
    st.latex(r"\phi = 1 + \psi(\rho + \lambda)\frac{C(M)}{M}")

    st.markdown("""
    And W is the **Lambert W function** (also called the product log).

    ### 6. Square Root Approximation

    For quick calculations, use:
    """)

    st.latex(r"|x^*| \approx \sigma \sqrt{\frac{2(\rho + \lambda) \cdot C(M)}{M}}")

    st.markdown("""
    This is equation (15) on page 16 of the paper.

    ### 7. Why NPV Analysis is Wrong

    The NPV rule says: refinance when:
    """)

    st.latex(r"|x| > \frac{(\rho + \lambda) \cdot C(M)}{M}")

    st.markdown("""
    But this **ignores the option value of waiting**. The optimal threshold is typically
    **50-100+ basis points higher** than the NPV rule suggests.

    ### 8. Practical Implications

    1. **Larger mortgages** → smaller thresholds (fixed costs matter less)
    2. **Higher volatility** → larger thresholds (more value in waiting)
    3. **Higher tax rates** → larger thresholds (interest deduction reduces benefit)
    4. **Shorter expected tenure** → larger thresholds (less time to recoup costs)

    ### 9. Reference

    Agarwal, S., Driscoll, J. C., & Laibson, D. (2007).
    *Optimal Mortgage Refinancing: A Closed Form Solution.*
    NBER Working Paper No. 13487.
    """)


# =============================================================================
# TAB 4: ADDITIONAL TOOLS (EXACT from original tab4)
# =============================================================================

def render_additional_tools(calc):
    """Render additional tools - EXACT from original tab4"""
    st.header("🔧 Additional Tools")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    sigma = calc['sigma']
    tau = calc['tau']
    lambda_val = calc['lambda_val']
    kappa = calc['kappa']
    x_star = calc['x_star']
    x_star_bp = calc['x_star_bp']

    tool = st.selectbox("Select Tool", [
        "Rate Drop Calculator",
        "Closing Cost Analysis",
        "Time Value Analysis"
    ])

    if tool == "Rate Drop Calculator":
        st.subheader("📉 Rate Drop Calculator")
        st.markdown("Calculate the benefit of different rate drops")

        rate_drop = st.slider(
            "Rate Drop (basis points)",
            min_value=0,
            max_value=300,
            value=int(x_star_bp) if not np.isnan(x_star_bp) else 100,
            step=25
        )

        new_rate = i0 - rate_drop/10000

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Current Rate", f"{i0*100:.3f}%")
            st.metric("New Rate", f"{new_rate*100:.3f}%")
            st.metric("Rate Drop", f"{rate_drop} bps")

        with col2:
            # Simple monthly payment calculation
            n_months = Gamma * 12
            old_pmt = M * (i0/12) / (1 - (1 + i0/12)**(-n_months)) if i0 > 0 else M/n_months
            new_pmt = M * (new_rate/12) / (1 - (1 + new_rate/12)**(-n_months)) if new_rate > 0 else M/n_months

            st.metric("Old Payment", f"${old_pmt:,.2f}")
            st.metric("New Payment", f"${new_pmt:,.2f}")
            st.metric("Monthly Savings", f"${old_pmt - new_pmt:,.2f}")

        # Simple break-even
        monthly_savings = old_pmt - new_pmt
        if monthly_savings > 0:
            breakeven_months = kappa / monthly_savings
            st.info(f"**Simple Break-even:** {breakeven_months:.1f} months ({breakeven_months/12:.1f} years)")

            if rate_drop >= x_star_bp:
                st.success(f"✅ This rate drop of {rate_drop} bps exceeds your optimal threshold of {x_star_bp:.0f} bps. Consider refinancing!")
            else:
                st.warning(f"⚠️ This rate drop of {rate_drop} bps is below your optimal threshold of {x_star_bp:.0f} bps. Waiting may be better.")

    elif tool == "Closing Cost Analysis":
        st.subheader("💰 Closing Cost Analysis")
        st.markdown("See how different closing costs affect your threshold")

        cost_range = np.arange(0, 15001, 500)

        thresholds = []
        trigger_rates = []

        for cost in cost_range:
            kappa_test = cost + calc['points'] * M
            x_test, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa_test, tau)
            thresholds.append(-x_test * 10000 if not np.isnan(x_test) else np.nan)
            trigger_rates.append((i0 - abs(x_test)) * 100 if not np.isnan(x_test) else np.nan)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cost_range, y=trigger_rates, mode='lines', name='Trigger Rate'))

        # Mark current
        current_trigger = (i0 - abs(x_star)) * 100 if not np.isnan(x_star) else None
        if current_trigger:
            fig.add_trace(go.Scatter(x=[calc['fixed_cost']], y=[current_trigger], mode='markers',
                                    name='Current', marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Trigger Rate vs Closing Costs",
            xaxis_title="Closing Costs ($)",
            yaxis_title="Trigger Rate (%)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table
        st.markdown("### Closing Cost → Threshold Table")
        table_data = []
        for i, cost in enumerate(cost_range[::2]):  # Every other value
            if i < len(thresholds)//2 + 1:
                idx = i * 2
                if idx < len(thresholds):
                    table_data.append({
                        'Closing Costs': f"${cost:,.0f}",
                        'Threshold (bps)': f"{thresholds[idx]:.0f}" if not np.isnan(thresholds[idx]) else "N/A",
                        'Trigger Rate': f"{trigger_rates[idx]:.3f}%" if not np.isnan(trigger_rates[idx]) else "N/A"
                    })

        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    elif tool == "Time Value Analysis":
        st.subheader("⏰ Time Value Analysis")
        st.markdown("How does remaining mortgage term affect the threshold?")

        gamma_range = np.arange(5, 31, 1)
        thresholds = []

        for gamma_test in gamma_range:
            lambda_test = calculate_lambda(calc['mu'], i0, gamma_test, calc['pi'])
            x_test, _, _, _ = calculate_optimal_threshold(M, rho, lambda_test, sigma, kappa, tau)
            thresholds.append(-x_test * 10000 if not np.isnan(x_test) else np.nan)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=gamma_range, y=thresholds, mode='lines+markers'))

        # Mark current
        fig.add_trace(go.Scatter(x=[Gamma], y=[x_star_bp], mode='markers', name='Current',
                                marker=dict(size=15, color='red', symbol='star')))

        fig.update_layout(
            title="Optimal Threshold vs Years Remaining",
            xaxis_title="Years Remaining on Mortgage",
            yaxis_title="Threshold (basis points)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info("""
        **Insight:** With more years remaining, you have more time to benefit from lower rates,
        so a smaller rate drop can justify refinancing.
        """)


# =============================================================================
# TAB 5: POINTS ANALYSIS (EXACT from original tab5)
# =============================================================================

def render_points_analysis(calc):
    """Render points analysis - EXACT from original tab5"""
    st.header("💰 Points Analysis")
    st.markdown("Analyze the trade-off between points paid and interest rate")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    sigma = calc['sigma']
    tau = calc['tau']
    lambda_val = calc['lambda_val']

    st.subheader("🎯 Points vs Rate Trade-off")

    st.markdown("""
    Points (also called discount points) are upfront fees paid to reduce the interest rate.
    - **1 point = 1% of loan amount**
    - Each point typically reduces the rate by ~0.125% to 0.25%

    Use this tool to determine if paying points is worthwhile given your situation.
    """)

    col1, col2 = st.columns(2)

    with col1:
        base_rate = st.number_input(
            "Base Rate (no points) %",
            min_value=1.0,
            max_value=15.0,
            value=i0 * 100,
            step=0.125
        ) / 100

        rate_reduction_per_point = st.number_input(
            "Rate Reduction per Point (%)",
            min_value=0.0,
            max_value=0.5,
            value=0.25,
            step=0.0625
        ) / 100

    with col2:
        max_points = st.number_input(
            "Maximum Points to Analyze",
            min_value=1.0,
            max_value=5.0,
            value=3.0,
            step=0.5
        )

        fixed_costs = st.number_input(
            "Other Closing Costs ($)",
            min_value=0,
            max_value=20000,
            value=int(calc['fixed_cost']),
            step=500
        )

    st.markdown("---")

    # Calculate for different point levels
    point_levels = np.arange(0, max_points + 0.5, 0.5)
    results = []

    for pts in point_levels:
        rate = base_rate - pts * rate_reduction_per_point
        point_cost = pts * M / 100
        total_cost = fixed_costs + point_cost

        # Calculate optimal threshold for this scenario
        kappa_test = total_cost
        x_test, _, _, _ = calculate_optimal_threshold(M, rho, lambda_val, sigma, kappa_test, tau)

        # Monthly payment
        n_months = Gamma * 12
        monthly_pmt = M * (rate/12) / (1 - (1 + rate/12)**(-n_months)) if rate > 0 else M/n_months

        # Total interest over remaining term
        total_paid = monthly_pmt * n_months
        total_interest = total_paid - M

        results.append({
            'Points': pts,
            'Rate': f"{rate*100:.3f}%",
            'Point Cost': f"${point_cost:,.0f}",
            'Total Closing': f"${total_cost:,.0f}",
            'Monthly Payment': f"${monthly_pmt:,.2f}",
            'Total Interest': f"${total_interest:,.0f}",
            'Total Cost': f"${total_interest + total_cost:,.0f}"
        })

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Comparison chart
    fig = go.Figure()

    total_costs = []
    for pts in point_levels:
        rate = base_rate - pts * rate_reduction_per_point
        point_cost = pts * M / 100
        total_closing = fixed_costs + point_cost
        n_months = Gamma * 12
        monthly_pmt = M * (rate/12) / (1 - (1 + rate/12)**(-n_months)) if rate > 0 else M/n_months
        total_interest = monthly_pmt * n_months - M
        total_costs.append(total_interest + total_closing)

    fig.add_trace(go.Bar(
        x=[f"{p:.1f}" for p in point_levels],
        y=total_costs,
        text=[f"${c:,.0f}" for c in total_costs],
        textposition='outside'
    ))

    fig.update_layout(
        title="Total Cost Over Loan Term (Interest + Closing Costs)",
        xaxis_title="Points Paid",
        yaxis_title="Total Cost ($)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # Find optimal
    min_cost_idx = np.argmin(total_costs)
    optimal_points = point_levels[min_cost_idx]

    st.success(f"**Optimal Points:** {optimal_points:.1f} points minimizes your total cost over the loan term.")

    # Break-even analysis
    st.markdown("---")
    st.subheader("⏱️ Break-even Analysis")

    if len(point_levels) >= 2:
        # Compare 0 points vs each point level
        base_monthly = M * (base_rate/12) / (1 - (1 + base_rate/12)**(-Gamma*12)) if base_rate > 0 else M/(Gamma*12)

        breakeven_data = []
        for pts in point_levels[1:]:  # Skip 0 points
            rate = base_rate - pts * rate_reduction_per_point
            point_cost = pts * M / 100

            monthly = M * (rate/12) / (1 - (1 + rate/12)**(-Gamma*12)) if rate > 0 else M/(Gamma*12)
            monthly_savings = base_monthly - monthly

            if monthly_savings > 0:
                breakeven_months = point_cost / monthly_savings
                breakeven_data.append({
                    'Points': f"{pts:.1f}",
                    'Monthly Savings': f"${monthly_savings:,.2f}",
                    'Point Cost': f"${point_cost:,.0f}",
                    'Break-even': f"{breakeven_months:.0f} months ({breakeven_months/12:.1f} years)"
                })

        if breakeven_data:
            st.dataframe(pd.DataFrame(breakeven_data), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 6: ENPV ANALYSIS (EXACT from original tab6)
# =============================================================================

def render_enpv_analysis(calc):
    """Render ENPV analysis - EXACT from original tab6"""
    st.header("📊 Expected Net Present Value (ENPV) Analysis")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    tau = calc['tau']

    st.markdown("""
    This analysis calculates the Expected Net Present Value (ENPV) of refinancing,
    accounting for prepayment risk through a Conditional Prepayment Rate (CPR).
    """)

    # Inputs specific to ENPV
    st.subheader("📝 ENPV Parameters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        enpv_new_rate = st.number_input(
            "New Interest Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=(i0 - 0.01) * 100,
            step=0.125,
            format="%.3f",
            help="The rate you would get if you refinance"
        ) / 100

    with col2:
        enpv_new_term = st.number_input(
            "New Loan Term (years)",
            min_value=10,
            max_value=30,
            value=30,
            step=5,
            help="Term of the new loan"
        )

    with col3:
        enpv_closing_costs = st.number_input(
            "Closing Costs ($)",
            min_value=0,
            max_value=50000,
            value=int(calc['kappa']),
            step=500,
            help="Total closing costs"
        )

    with col4:
        enpv_finance_costs = st.checkbox(
            "Finance closing costs?",
            value=False,
            help="Roll closing costs into the new loan"
        )

    col1b, col2b, col3b, col4b = st.columns(4)

    with col1b:
        enpv_invest_rate = st.number_input(
            "Investment Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=rho * 100,
            step=0.5,
            help="Return on invested savings"
        ) / 100

    with col2b:
        enpv_discount_rate = st.number_input(
            "Discount Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=rho * 100,
            step=0.5,
            help="Personal discount rate"
        ) / 100

    with col3b:
        enpv_cpr = st.number_input(
            "CPR (annual %)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Conditional Prepayment Rate"
        ) / 100

    with col4b:
        include_taxes = st.checkbox(
            "Include tax effects",
            value=True,
            help="Account for mortgage interest deduction"
        )

    # Helper function
    def payment(principal, monthly_rate, n_months):
        """Level payment on an amortizing loan."""
        if monthly_rate == 0:
            return principal / n_months
        denom = 1.0 - (1.0 + monthly_rate) ** (-n_months)
        return principal * monthly_rate / denom

    def compute_enpv_full(current_balance, current_rate, new_rate, remaining_years_old, new_term_years,
                         closing_costs, finance_costs_in_loan, invest_rate, discount_rate, cpr, tau_rate, include_tax):
        """Full ENPV calculation matching the imp file"""
        n_old = int(round(remaining_years_old * 12))
        n_new = int(round(new_term_years * 12))
        horizon = max(n_old, n_new)
        gamma_month = n_old

        r_old = current_rate / 12.0
        r_new = new_rate / 12.0
        r_inv = invest_rate / 12.0
        r_disc = discount_rate / 12.0

        old_principal = current_balance
        if finance_costs_in_loan:
            new_principal = current_balance + closing_costs
        else:
            new_principal = current_balance

        # Monthly payments
        pmt_old = payment(old_principal, r_old, n_old)
        pmt_new = payment(new_principal, r_new, n_new)

        bal_old = old_principal
        bal_new = new_principal
        cum_sav = 0.0
        inv_bal = 0.0

        history = []
        opt1_sav = 0.0
        opt2_sav = 0.0

        for t in range(1, horizon + 1):
            # Old loan
            if t <= n_old and bal_old > 0:
                interest_old = r_old * bal_old
                principal_old = pmt_old - interest_old
                bal_old = max(0.0, bal_old - principal_old)
                if include_tax:
                    p_old_t = pmt_old - (interest_old * tau_rate)
                else:
                    p_old_t = pmt_old
            else:
                p_old_t = 0.0
                bal_old = 0.0

            # New loan
            if t <= n_new and bal_new > 0:
                interest_new = r_new * bal_new
                principal_new = pmt_new - interest_new
                bal_new = max(0.0, bal_new - principal_new)
                if include_tax:
                    p_new_t = pmt_new - (interest_new * tau_rate)
                else:
                    p_new_t = pmt_new
            else:
                p_new_t = 0.0
                bal_new = 0.0

            # Payment savings
            pmt_sav_t = p_old_t - p_new_t
            cum_sav += pmt_sav_t

            # Investment account and total advantage
            if t < gamma_month:
                inv_bal = inv_bal * (1.0 + r_inv) + pmt_sav_t
                balance_adv = bal_old - bal_new
                total_adv = inv_bal + balance_adv
            elif t == gamma_month:
                inv_bal = inv_bal * (1.0 + r_inv) + pmt_sav_t
                opt2_sav = inv_bal
                opt1_sav = 0.0
                balance_adv = bal_old - bal_new
                total_adv = inv_bal + balance_adv
            else:
                opt1_sav = opt1_sav * (1.0 + r_inv) + pmt_old
                opt2_sav = opt2_sav * (1.0 + r_inv)
                total_adv = (opt2_sav - bal_new) - opt1_sav

            rec = {
                "month": t,
                "p_old": p_old_t,
                "p_new": p_new_t,
                "pmt_sav_t": pmt_sav_t,
                "cum_sav": cum_sav,
                "inv_bal": inv_bal if t <= gamma_month else opt2_sav,
                "bal_old": bal_old,
                "bal_new": bal_new,
                "balance_adv": bal_old - bal_new,
                "total_adv": total_adv,
            }
            history.append(rec)

        return history, pmt_old, pmt_new, gamma_month

    # Run calculation
    history, pmt_old_calc, pmt_new_calc, gamma_month = compute_enpv_full(
        current_balance=M,
        current_rate=i0,
        new_rate=enpv_new_rate,
        remaining_years_old=Gamma,
        new_term_years=enpv_new_term,
        closing_costs=enpv_closing_costs,
        finance_costs_in_loan=enpv_finance_costs,
        invest_rate=enpv_invest_rate,
        discount_rate=enpv_discount_rate,
        cpr=enpv_cpr,
        tau_rate=tau if include_taxes else 0,
        include_tax=include_taxes
    )

    # Calculate NPV and ENPV
    months = [rec["month"] for rec in history]
    net_gain_fv = [rec["total_adv"] for rec in history]
    net_gain_pv = [gain / ((1.0 + enpv_discount_rate/12) ** t) for gain, t in zip(net_gain_fv, months)]

    # Calculate ENPV with mortality
    SMM = 1 - (1 - enpv_cpr)**(1/12)
    survival = 1.0
    mortality = []
    npv_times_mortality = []

    # Extend to 360 months
    last_pv = net_gain_pv[-1] if net_gain_pv else 0
    while len(net_gain_pv) < 360:
        net_gain_pv.append(last_pv)

    for t in range(360):
        m_t = survival * SMM
        mortality.append(m_t)
        npv_times_mort = net_gain_pv[t] * m_t
        npv_times_mortality.append(npv_times_mort)
        survival = survival * (1 - SMM)

    # Add remaining survival to month 360
    if survival > 0.001:
        mortality[-1] += survival
        npv_times_mortality[-1] = net_gain_pv[-1] * mortality[-1]

    ENPV = sum(npv_times_mortality)

    # Display results
    st.markdown("---")
    st.subheader("📊 Results Summary")

    col1r, col2r, col3r, col4r = st.columns(4)

    with col1r:
        st.metric("Old Payment", f"${pmt_old_calc:,.2f}")

    with col2r:
        st.metric("New Payment", f"${pmt_new_calc:,.2f}")

    with col3r:
        monthly_savings = pmt_old_calc - pmt_new_calc
        st.metric("Monthly Savings", f"${monthly_savings:,.2f}")

    with col4r:
        st.metric("**ENPV**", f"**${ENPV:,.2f}**",
                 "Good deal!" if ENPV > 0 else "Consider waiting")

    # Additional metrics
    st.markdown("---")
    col1m, col2m, col3m = st.columns(3)

    with col1m:
        st.metric("SMM (monthly)", f"{SMM*100:.5f}%")

    with col2m:
        # Find break-even month
        breakeven_month = None
        for rec in history:
            if rec["total_adv"] >= 0:
                breakeven_month = rec["month"]
                break
        if breakeven_month:
            st.metric("Break-even", f"{breakeven_month} months ({breakeven_month/12:.1f} years)")
        else:
            st.metric("Break-even", "Never")

    with col3m:
        st.metric("Gamma (Γ)", f"{gamma_month} months ({gamma_month/12:.1f} years)")

    # Charts
    st.markdown("---")
    st.subheader("📈 Visualizations")

    # Chart 1: Net Benefit (Future Value)
    months_display = [rec["month"] for rec in history]
    net_gain_fv_display = [rec["total_adv"] for rec in history]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=months_display,
        y=net_gain_fv_display,
        mode='lines',
        name='Net Benefit',
        line=dict(width=2, color='blue')
    ))
    fig1.add_hline(y=0, line_dash="dash", line_color="gray")
    fig1.add_vline(x=gamma_month, line_dash="dash", line_color="red",
                  annotation_text=f"Gamma ({gamma_month} months)")

    fig1.update_layout(
        title="Net Benefit of Refinancing (Future Value)",
        xaxis_title="Month",
        yaxis_title="Net Gain (FV $)",
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Explanation
    st.info("""
    **Understanding ENPV Analysis:**

    - **ENPV** = Expected Net Present Value, accounting for the probability of prepayment each month
    - **Mortality** = Probability of prepaying in that specific month (based on CPR)
    - **Gamma (Γ)** = Month when the original loan would be paid off
    - **Break-even**: The month when cumulative benefits exceed refinancing costs

    The ENPV gives the expected value of refinancing, weighted by how long you're likely to keep the mortgage.
    """)


# =============================================================================
# TAB 7: NET BENEFIT TIMELINE (EXACT from original tab8)
# =============================================================================

def render_net_benefit_timeline(calc):
    """Render net benefit timeline - EXACT from original tab8"""
    st.header("📈 Net Benefit Over Time Analysis")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    tau = calc['tau']
    lambda_val = calc['lambda_val']
    kappa = calc['kappa']
    x_star = calc['x_star']
    x_star_bp = calc['x_star_bp']
    psi = calc['psi']
    phi = calc['phi']
    C_M = calc['C_M']

    st.markdown("""
    This analysis shows the net benefit of refinancing based on the paper's value matching condition
    and uses actual amortization schedules for precise calculations.
    """)

    # Value Matching Formula Display
    st.subheader("📐 Value Matching Condition (Theorem 2)")

    st.markdown("""
    At the optimal refinancing threshold x*, the following **value matching condition** holds:
    """)

    st.latex(r"R(x^*) = R(0) - C(M) - \frac{x^* \cdot M}{\rho + \lambda}")

    st.markdown(f"""
    **Your Parameter Values:**
    - M = **${M:,.0f}**
    - i₀ = **{i0*100:.3f}%**
    - ρ = **{rho*100:.2f}%**
    - λ = **{lambda_val:.4f}**
    - C(M) = **${C_M:,.0f}**
    - x* = **{x_star:.6f}** ({x_star_bp:.0f} bps)
    """)

    # Net Benefit Analysis Parameters
    st.markdown("---")
    st.subheader("🔧 Net Benefit Analysis Parameters")

    col1p, col2p, col3p = st.columns(3)

    with col1p:
        nb_rate_reduction = st.number_input(
            "Rate Reduction (bps)",
            min_value=1,
            max_value=500,
            value=int(abs(x_star_bp)) if not np.isnan(x_star_bp) else 100,
            step=25,
            help="How much lower is the new rate (in basis points)",
            key="nb_rate_reduction"
        ) / 10000

        nb_closing_costs = st.number_input(
            "Refinancing Costs ($)",
            min_value=0,
            max_value=50000,
            value=int(kappa),
            step=500,
            help="Total costs to refinance",
            key="nb_closing"
        )

    with col2p:
        nb_discount_rate = st.number_input(
            "PV Discount Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=rho * 100,
            step=0.5,
            help="Discount rate for present value calculations",
            key="nb_discount"
        ) / 100

        nb_invest_rate = st.number_input(
            "Investment Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=rho * 100,
            step=0.5,
            help="Return on invested payment savings",
            key="nb_invest"
        ) / 100

    with col3p:
        nb_new_term = st.number_input(
            "New Loan Term (years)",
            min_value=10,
            max_value=30,
            value=Gamma,
            step=5,
            help="Term of the refinanced loan",
            key="nb_new_term"
        )

        nb_include_prepay = st.checkbox(
            "Include Prepayment Risk (λ)",
            value=True,
            help="Account for probability of moving/prepaying",
            key="nb_prepay"
        )

    # Display effective rates
    st.markdown("### 📋 Scenario Summary")
    col1s, col2s, col3s, col4s = st.columns(4)
    with col1s:
        st.metric("Original Rate", f"{i0*100:.3f}%")
    with col2s:
        st.metric("New Rate", f"{(i0-nb_rate_reduction)*100:.3f}%")
    with col3s:
        st.metric("Rate Savings", f"{nb_rate_reduction*10000:.0f} bps")
    with col4s:
        st.metric("Closing Costs", f"${nb_closing_costs:,.0f}")

    # Actual Amortization Calculation
    st.markdown("---")
    st.subheader("💰 Net Benefit Analysis (Actual Amortization)")

    # Helper function for monthly payment
    def calc_monthly_payment(principal, annual_rate, months):
        if annual_rate == 0:
            return principal / months
        monthly_rate = annual_rate / 12
        return principal * monthly_rate / (1 - (1 + monthly_rate)**(-months))

    # Setup
    n_months_old = int(Gamma * 12)
    n_months_new = int(nb_new_term * 12)
    n_months_analysis = max(n_months_old, n_months_new)

    r_old_monthly = i0 / 12
    r_new_monthly = (i0 - nb_rate_reduction) / 12
    r_discount_monthly = nb_discount_rate / 12
    r_invest_monthly = nb_invest_rate / 12

    pmt_old = calc_monthly_payment(M, i0, n_months_old)
    pmt_new = calc_monthly_payment(M, i0 - nb_rate_reduction, n_months_new)

    # Build amortization schedules
    results = []

    bal_old = M
    bal_new = M
    cumulative_savings_invested = 0
    cumulative_pv_savings = 0
    prepay_survival_prob = 1.0

    for month in range(1, n_months_analysis + 1):
        # Old loan calculations
        if month <= n_months_old and bal_old > 0:
            interest_old = bal_old * r_old_monthly
            principal_old = pmt_old - interest_old
            bal_old = max(0, bal_old - principal_old)
            payment_old = pmt_old
            tax_benefit_old = interest_old * tau
            after_tax_payment_old = pmt_old - tax_benefit_old
        else:
            interest_old = 0
            payment_old = 0
            after_tax_payment_old = 0

        # New loan calculations
        if month <= n_months_new and bal_new > 0:
            interest_new = bal_new * r_new_monthly
            principal_new = pmt_new - interest_new
            bal_new = max(0, bal_new - principal_new)
            payment_new = pmt_new
            tax_benefit_new = interest_new * tau
            after_tax_payment_new = pmt_new - tax_benefit_new
        else:
            interest_new = 0
            payment_new = 0
            after_tax_payment_new = 0

        # Monthly savings (after tax)
        monthly_savings = after_tax_payment_old - after_tax_payment_new

        # Invested savings with compound interest
        cumulative_savings_invested = cumulative_savings_invested * (1 + r_invest_monthly) + monthly_savings

        # Present value of this month's savings
        pv_factor = 1 / ((1 + r_discount_monthly) ** month)
        cumulative_pv_savings += monthly_savings * pv_factor

        # Prepayment-adjusted calculations
        if nb_include_prepay:
            lambda_monthly = lambda_val / 12
            prepay_survival_prob *= (1 - lambda_monthly)

        # Net benefit calculations
        fv_net_benefit = cumulative_savings_invested - nb_closing_costs
        pv_net_benefit = cumulative_pv_savings - nb_closing_costs

        # Paper's formula (time-adjusted)
        t_years = month / 12
        effective_lambda = lambda_val if nb_include_prepay else 0
        discount_factor = 1 - np.exp(-(rho + effective_lambda) * t_years)
        paper_formula_benefit = (nb_rate_reduction * M * (1 - tau) / (rho + effective_lambda)) * discount_factor - nb_closing_costs

        results.append({
            'month': month,
            'year': month / 12,
            'balance_old': bal_old,
            'balance_new': bal_new,
            'monthly_savings': monthly_savings,
            'fv_net_benefit': fv_net_benefit,
            'pv_net_benefit': pv_net_benefit,
            'paper_formula': paper_formula_benefit,
            'survival_prob': prepay_survival_prob
        })

    df_amort = pd.DataFrame(results)

    # Key Metrics
    st.markdown("### 📊 Key Metrics")

    col1m, col2m, col3m, col4m = st.columns(4)

    with col1m:
        st.metric(
            "Monthly Payment Savings",
            f"${pmt_old - pmt_new:,.2f}",
            help="Difference in nominal monthly payments"
        )

    with col2m:
        breakeven_fv = df_amort[df_amort['fv_net_benefit'] >= 0]['month'].min()
        if pd.notna(breakeven_fv):
            st.metric("Breakeven (FV)", f"{int(breakeven_fv)} months")
        else:
            st.metric("Breakeven (FV)", "Beyond analysis")

    with col3m:
        breakeven_pv = df_amort[df_amort['pv_net_benefit'] >= 0]['month'].min()
        if pd.notna(breakeven_pv):
            st.metric("Breakeven (PV)", f"{int(breakeven_pv)} months")
        else:
            st.metric("Breakeven (PV)", "Beyond analysis")

    with col4m:
        final_fv = df_amort['fv_net_benefit'].iloc[-1]
        st.metric(f"Total Benefit ({nb_new_term}yr)", f"${final_fv:,.0f}")

    # Charts
    st.markdown("---")
    st.subheader("📈 Net Benefit Charts")

    fig1 = go.Figure()

    # Future Value Net Benefit
    fig1.add_trace(go.Scatter(
        x=df_amort['year'],
        y=df_amort['fv_net_benefit'],
        mode='lines',
        name='Net Benefit (FV with investment)',
        line=dict(color='green', width=3)
    ))

    # Present Value Net Benefit
    fig1.add_trace(go.Scatter(
        x=df_amort['year'],
        y=df_amort['pv_net_benefit'],
        mode='lines',
        name=f'Net Benefit (PV @ {nb_discount_rate*100:.1f}%)',
        line=dict(color='blue', width=3)
    ))

    # Paper's formula
    fig1.add_trace(go.Scatter(
        x=df_amort['year'],
        y=df_amort['paper_formula'],
        mode='lines',
        name="Paper's Formula (time-adjusted)",
        line=dict(color='purple', width=2, dash='dash')
    ))

    # Breakeven line
    fig1.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Breakeven")

    # Paper's infinite horizon value
    effective_lambda = lambda_val if nb_include_prepay else 0
    paper_infinite_benefit = (nb_rate_reduction * M * (1 - tau)) / (rho + effective_lambda) - nb_closing_costs
    fig1.add_hline(y=paper_infinite_benefit, line_dash="dot", line_color="purple",
                  annotation_text=f"Paper's Formula (∞): ${paper_infinite_benefit:,.0f}")

    fig1.update_layout(
        title="Net Benefit Over Time - Actual Amortization vs Paper's Formula",
        xaxis_title="Years",
        yaxis_title="Net Benefit ($)",
        hovermode='x unified',
        height=600,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.info("""
    **Chart Explanation:**
    - **Green (FV)**: Your actual accumulated savings with investment returns, minus closing costs
    - **Blue (PV)**: Present value of savings discounted at your discount rate
    - **Purple dashed**: Paper's formula adjusted for finite time horizon
    - **Purple dotted**: Paper's infinite horizon value (theoretical maximum)
    """)


# =============================================================================
# TAB 8: VALUE MATCHING DEBUG (EXACT from original tab9)
# =============================================================================

def render_value_matching_debug(calc):
    """Render value matching debug - EXACT from original tab9"""
    st.header("🔍 Value Matching Verification")

    M = calc['M']
    i0 = calc['i0']
    Gamma = calc['Gamma']
    rho = calc['rho']
    sigma = calc['sigma']
    tau = calc['tau']
    mu = calc['mu']
    pi = calc['pi']
    points = calc['points']
    fixed_cost = calc['fixed_cost']
    lambda_val = calc['lambda_val']
    kappa = calc['kappa']
    x_star = calc['x_star']
    psi = calc['psi']
    phi = calc['phi']
    C_M = calc['C_M']

    st.markdown("""
    This tab verifies that the optimal threshold x* satisfies the value matching condition
    from Theorem 2 (page 12-14) of the paper.
    """)

    # Force x* to be negative (it represents a rate DROP)
    if not np.isnan(x_star):
        x_star_negative = -abs(x_star)
    else:
        x_star_negative = np.nan

    # Step 0: Show x* Calculation
    st.subheader("Step 0: x* Calculation (Verified Correct)")

    st.markdown("""
    **From Theorem 2 (page 13), equation (12):**
    """)
    st.latex(r"x^* = \frac{1}{\psi} \left[ \phi + W(-e^{-\phi}) \right]")

    st.markdown("""
    **Where:**
    """)
    st.latex(r"\psi = \frac{\sqrt{2(\rho + \lambda)}}{\sigma}")
    st.latex(r"\phi = 1 + \psi (\rho + \lambda) \frac{C(M)}{M}")

    # Recalculate step by step
    st.markdown("### Calculation Steps:")

    psi_calc = np.sqrt(2 * (rho + lambda_val)) / sigma
    st.markdown(f"""
    **ψ = √(2(ρ+λ)) / σ**
    = √(2 × ({rho:.4f} + {lambda_val:.4f})) / {sigma:.4f}
    = **{psi_calc:.6f}**
    """)

    C_M_calc = kappa / (1 - tau)
    st.markdown(f"""
    **C(M) = κ / (1-τ)**
    = {kappa:,.2f} / (1 - {tau:.2f})
    = **${C_M_calc:,.2f}**
    """)

    phi_calc = 1 + psi_calc * (rho + lambda_val) * C_M_calc / M
    st.markdown(f"""
    **φ = 1 + ψ(ρ+λ)C(M)/M**
    = 1 + {psi_calc:.6f} × {rho + lambda_val:.4f} × {C_M_calc:,.2f} / {M:,.0f}
    = **{phi_calc:.6f}**
    """)

    w_arg = -np.exp(-phi_calc)
    w_val = np.real(lambertw(w_arg, k=0))
    st.markdown(f"""
    **W argument = -e^(-φ)** = {w_arg:.10f}

    **W(-e^(-φ))** = **{w_val:.6f}**
    """)

    x_star_calc = (1 / psi_calc) * (phi_calc + w_val)
    st.markdown(f"""
    **x* = (1/ψ) × [φ + W(-e^(-φ))]**
    = (1/{psi_calc:.6f}) × [{phi_calc:.6f} + ({w_val:.6f})]
    = **{x_star_calc:.6f}**

    **x* in basis points** = {x_star_calc * 10000:.2f} bps
    **|x*| = rate drop needed** = {abs(x_star_calc) * 10000:.2f} bps
    """)

    if not np.isnan(x_star_negative):
        # Step 1: Verify equation (21)
        st.markdown("---")
        st.subheader("Step 1: Verify x* satisfies equation (21)")

        st.latex(r"e^{\psi x^*} - \psi x^* = 1 + \frac{C(M)}{M} \psi (\rho + \lambda)")

        eq21_LHS = np.exp(psi * x_star_negative) - psi * x_star_negative
        eq21_RHS = 1 + (C_M / M) * psi * (rho + lambda_val)

        st.markdown(f"""
        **LHS = e^(ψx*) - ψx*** = **{eq21_LHS:.6f}**

        **RHS = 1 + (C(M)/M) × ψ × (ρ+λ)** = **{eq21_RHS:.6f}**
        """)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("LHS", f"{eq21_LHS:.6f}")
        with col2:
            st.metric("RHS", f"{eq21_RHS:.6f}")
        with col3:
            st.metric("Difference", f"{abs(eq21_LHS - eq21_RHS):.8f}")

        if abs(eq21_LHS - eq21_RHS) < 0.001:
            st.success("✓ Equation (21) is satisfied!")
        else:
            st.error(f"✗ Equation (21) NOT satisfied! Difference: {abs(eq21_LHS - eq21_RHS):.6f}")

        # Step 2: Verify Value Matching
        st.markdown("---")
        st.subheader("Step 2: Verify Value Matching - Equation (17)")

        st.latex(r"K e^{-\psi x^*} = K - C(M) - \frac{x^* M}{\rho + \lambda}")

        K = M * np.exp(psi * x_star_negative) / (psi * (rho + lambda_val))

        st.markdown(f"""
        **K from equation (14):**
        K = M × e^(ψx*) / (ψ(ρ+λ))
        = **${K:,.2f}**
        """)

        eq17_LHS = K * np.exp(-psi * x_star_negative)
        term_xM = (x_star_negative * M) / (rho + lambda_val)
        eq17_RHS = K - C_M - term_xM

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("LHS: K×e^(-ψx*)", f"${eq17_LHS:,.2f}")
        with col2:
            st.metric("RHS: K-C(M)-x*M/(ρ+λ)", f"${eq17_RHS:,.2f}")
        with col3:
            st.metric("Difference", f"${abs(eq17_LHS - eq17_RHS):,.2f}")

        if abs(eq17_LHS - eq17_RHS) < 1:
            st.success("✓ Value matching equation (17) is satisfied!")
        else:
            st.error(f"✗ Value matching equation (17) NOT satisfied!")

        # Step 3: Option Values
        st.markdown("---")
        st.subheader("Step 3: Option Values R(x)")

        R_0 = K
        R_x_star = K * np.exp(-psi * x_star_negative)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("R(0) = K", f"${R_0:,.2f}")
        with col2:
            st.metric("R(x*)", f"${R_x_star:,.2f}")
        with col3:
            st.metric("C(M)", f"${C_M:,.2f}")
        with col4:
            st.metric("x*M/(ρ+λ)", f"${term_xM:,.2f}")

        # Step 4: All Input Parameters
        st.markdown("---")
        st.subheader("Step 4: All Input Parameters")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Loan Info**")
            st.metric("M (mortgage)", f"${M:,.0f}")
            st.metric("i₀ (original rate)", f"{i0*100:.2f}%")
            st.metric("Γ (years remaining)", f"{Gamma}")
        with col2:
            st.markdown("**Rates**")
            st.metric("ρ (discount rate)", f"{rho*100:.1f}%")
            st.metric("μ (moving prob)", f"{mu*100:.1f}%")
            st.metric("π (inflation)", f"{pi*100:.1f}%")
        with col3:
            st.markdown("**Costs**")
            st.metric("Points", f"{points*100:.2f}%")
            st.metric("Fixed cost", f"${fixed_cost:,.0f}")
            st.metric("κ (total)", f"${kappa:,.0f}")
        with col4:
            st.markdown("**Other**")
            st.metric("σ (volatility)", f"{sigma:.4f}")
            st.metric("τ (tax rate)", f"{tau*100:.0f}%")
            st.metric("λ (lambda)", f"{lambda_val:.4f}")

        # Summary
        st.markdown("---")
        st.subheader("Step 5: Summary")

        st.markdown(f"""
        | Parameter | Value | Notes |
        |-----------|-------|-------|
        | x* (calculated) | {x_star_calc:.6f} | |
        | x* in bps | {x_star_calc * 10000:.2f} | Rate drop needed to refinance |
        | ψ | {psi:.6f} | |
        | φ | {phi:.6f} | |
        | K | ${K:,.2f} | |
        | R(0) | ${R_0:,.2f} | Option value at x=0 |
        | R(x*) | ${R_x_star:,.2f} | Option value at threshold |
        | C(M) | ${C_M:,.2f} | Tax-adjusted refi cost |
        """)

    else:
        st.error("x* is NaN - cannot verify. Check your input parameters.")
