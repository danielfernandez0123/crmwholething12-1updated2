"""
Optimal Mortgage Refinancing Calculator
Based on: "Optimal Mortgage Refinancing: A Closed Form Solution"
By Sumit Agarwal, John C. Driscoll, and David Laibson
NBER Working Paper No. 13487 (October 2007)

Extracted core calculation logic for CRM integration
"""

import numpy as np
from scipy.special import lambertw


def calculate_lambda(mu: float, i0: float, Gamma: int, pi: float) -> float:
    """
    Calculate λ (lambda) as per page 19 and Appendix C of the paper

    Args:
        mu: Annual probability of moving
        i0: Original mortgage rate (decimal)
        Gamma: Remaining mortgage years
        pi: Expected inflation rate (decimal)

    Returns:
        Lambda value
    """
    if i0 * Gamma < 100:  # Prevent overflow
        lambda_val = mu + i0 / (np.exp(i0 * Gamma) - 1) + pi
    else:
        lambda_val = mu + pi  # Simplified for very large values
    return lambda_val


def calculate_kappa(M: float, points: float, fixed_cost: float, tau: float) -> float:
    """
    Calculate κ(M) - tax-adjusted refinancing cost (Appendix A)

    Args:
        M: Remaining mortgage value
        points: Points as decimal (e.g., 0.01 for 1%)
        fixed_cost: Fixed refinancing costs
        tau: Marginal tax rate (decimal)

    Returns:
        Kappa value
    """
    kappa = fixed_cost + points * M
    return kappa


def calculate_optimal_threshold(M: float, rho: float, lambda_val: float,
                                 sigma: float, kappa: float, tau: float) -> tuple:
    """
    Calculate the optimal refinancing threshold x* using Lambert W function
    As per Theorem 2 (page 13) and equation (12)

    Args:
        M: Remaining mortgage value
        rho: Real discount rate (decimal)
        lambda_val: Lambda value from calculate_lambda
        sigma: Interest rate volatility
        kappa: Kappa value from calculate_kappa
        tau: Marginal tax rate (decimal)

    Returns:
        Tuple of (x_star, psi, phi, C_M)
    """
    # Calculate ψ (psi) as per equation in Theorem 2
    psi = np.sqrt(2 * (rho + lambda_val)) / sigma

    # Calculate φ (phi) as per equation in Theorem 2
    C_M = kappa / (1 - tau)  # Normalized refinancing cost
    phi = 1 + psi * (rho + lambda_val) * C_M / M

    # Calculate x* using Lambert W function (equation 12)
    # x* = (1/ψ)[φ + W(-exp(-φ))]
    try:
        w_arg = -np.exp(-phi)
        w_val = np.real(lambertw(w_arg, k=0))
        x_star = (1 / psi) * (phi + w_val)
    except:
        x_star = np.nan

    return x_star, psi, phi, C_M


def calculate_square_root_approximation(M: float, rho: float, lambda_val: float,
                                         sigma: float, kappa: float, tau: float) -> float:
    """
    Calculate the square root approximation (second-order Taylor expansion)
    As per Section 2.3 (page 16-17)

    Returns:
        Approximate x* value
    """
    sqrt_term = sigma * np.sqrt(kappa / (M * (1 - tau))) * np.sqrt(2 * (rho + lambda_val))
    return -sqrt_term


def calculate_npv_threshold(M: float, rho: float, lambda_val: float,
                            kappa: float, tau: float) -> float:
    """
    Calculate the NPV break-even threshold
    As per Definition 3 (page 16)

    Returns:
        NPV threshold x value
    """
    C_M = kappa / (1 - tau)
    x_npv = -(rho + lambda_val) * C_M / M
    return x_npv


def calculate_trigger_rate(current_rate: float, remaining_balance: float,
                           remaining_years: int, discount_rate: float = 0.05,
                           volatility: float = 0.0109, tax_rate: float = 0.28,
                           fixed_cost: float = 2000, points: float = 0.01,
                           prob_moving: float = 0.10, inflation_rate: float = 0.03) -> dict:
    """
    Calculate the trigger rate for refinancing

    This is the main function to use for CRM integration.
    It calculates when a client should refinance based on the ADL/NBER model.

    Args:
        current_rate: Current mortgage rate (as decimal, e.g., 0.065 for 6.5%)
        remaining_balance: Remaining mortgage balance
        remaining_years: Years remaining on mortgage
        discount_rate: Real discount rate (default 5%)
        volatility: Interest rate volatility (default 0.0109)
        tax_rate: Marginal tax rate (default 28%)
        fixed_cost: Fixed refinancing costs (default $2000)
        points: Points as decimal (default 1%)
        prob_moving: Annual probability of moving (default 10%)
        inflation_rate: Expected inflation rate (default 3%)

    Returns:
        Dictionary with:
            - optimal_threshold_bps: Optimal threshold in basis points
            - trigger_rate: The rate at which to refinance (decimal)
            - x_star: Raw x* value
            - sqrt_approx_bps: Square root approximation in bps
            - npv_threshold_bps: NPV threshold in bps
            - all intermediate values
    """
    # Convert rate to decimal if needed
    if current_rate > 1:
        current_rate = current_rate / 100

    # Calculate intermediate values
    lambda_val = calculate_lambda(prob_moving, current_rate, remaining_years, inflation_rate)
    kappa = calculate_kappa(remaining_balance, points, fixed_cost, tax_rate)

    # Calculate optimal threshold
    x_star, psi, phi, C_M = calculate_optimal_threshold(
        remaining_balance, discount_rate, lambda_val, volatility, kappa, tax_rate
    )

    # Calculate approximations for comparison
    x_star_sqrt = calculate_square_root_approximation(
        remaining_balance, discount_rate, lambda_val, volatility, kappa, tax_rate
    )
    x_npv = calculate_npv_threshold(
        remaining_balance, discount_rate, lambda_val, kappa, tax_rate
    )

    # Convert to basis points (x_star is negative, we want positive bps drop)
    x_star_bp = -x_star * 10000 if not np.isnan(x_star) else None
    x_star_sqrt_bp = -x_star_sqrt * 10000
    x_npv_bp = -x_npv * 10000

    # Calculate trigger rate (current rate minus optimal drop)
    trigger_rate = None
    if x_star_bp is not None:
        trigger_rate = current_rate - abs(x_star)

    return {
        'optimal_threshold_bps': x_star_bp,
        'trigger_rate': trigger_rate,
        'trigger_rate_pct': trigger_rate * 100 if trigger_rate else None,
        'x_star': x_star,
        'sqrt_approx_bps': x_star_sqrt_bp,
        'npv_threshold_bps': x_npv_bp,
        'lambda': lambda_val,
        'kappa': kappa,
        'psi': psi,
        'phi': phi,
        'C_M': C_M,
        'current_rate': current_rate,
        'current_rate_pct': current_rate * 100
    }


def is_ready_to_refinance(trigger_rate: float, available_rate: float) -> dict:
    """
    Check if a client is ready to refinance

    Args:
        trigger_rate: The calculated trigger rate (decimal)
        available_rate: The rate available to the client today (decimal)

    Returns:
        Dictionary with:
            - is_ready: Boolean
            - difference: trigger_rate - available_rate
            - difference_bps: Difference in basis points
            - message: Human-readable status
    """
    if trigger_rate is None or available_rate is None:
        return {
            'is_ready': False,
            'difference': None,
            'difference_bps': None,
            'message': 'Missing rate data'
        }

    difference = trigger_rate - available_rate
    difference_bps = difference * 10000

    if difference > 0:
        return {
            'is_ready': True,
            'difference': difference,
            'difference_bps': difference_bps,
            'message': f'Ready to refinance! Available rate is {difference_bps:.0f} bps below trigger.'
        }
    else:
        return {
            'is_ready': False,
            'difference': difference,
            'difference_bps': difference_bps,
            'message': f'Not ready. Need rates to drop {-difference_bps:.0f} more bps.'
        }


# Example usage
if __name__ == "__main__":
    # Example: Client with 6.5% mortgage
    result = calculate_trigger_rate(
        current_rate=0.065,
        remaining_balance=400000,
        remaining_years=25,
        discount_rate=0.05,
        volatility=0.0109,
        tax_rate=0.28,
        fixed_cost=2000,
        points=0.01,
        prob_moving=0.10,
        inflation_rate=0.03
    )

    print(f"Current Rate: {result['current_rate_pct']:.2f}%")
    print(f"Optimal Threshold: {result['optimal_threshold_bps']:.0f} bps")
    print(f"Trigger Rate: {result['trigger_rate_pct']:.2f}%")

    # Check if ready at 5.5%
    check = is_ready_to_refinance(result['trigger_rate'], 0.055)
    print(f"\nAt 5.5% available: {check['message']}")

    # Check if ready at 6.0%
    check = is_ready_to_refinance(result['trigger_rate'], 0.060)
    print(f"At 6.0% available: {check['message']}")
