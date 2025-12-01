"""
Live Rate Calculator with LLPA Adjustments
Extracted from mortgage_rate_calculator for CRM integration

Calculates the available rate for a client based on their profile
"""

import json
import os

# =============================================================================
# LOAN LIMITS (2025)
# =============================================================================
CONFORMING_LIMIT_2025 = 806500
HIGH_BALANCE_LIMIT_2025 = 1209750

# =============================================================================
# LTV BUCKET FUNCTIONS
# =============================================================================

def get_ltv_bucket(ltv: float) -> str:
    """Determine LTV bucket for lookup"""
    if ltv <= 30:
        return "<=30"
    elif ltv <= 60:
        return "30.01-60"
    elif ltv <= 70:
        return "60.01-70"
    elif ltv <= 75:
        return "70.01-75"
    elif ltv <= 80:
        return "75.01-80"
    elif ltv <= 85:
        return "80.01-85"
    elif ltv <= 90:
        return "85.01-90"
    elif ltv <= 95:
        return "90.01-95"
    else:
        return ">95"


def get_ltv_bucket_cashout(ltv: float) -> str:
    """Determine LTV bucket for cash-out refinance (max 80% LTV)"""
    if ltv <= 30:
        return "<=30"
    elif ltv <= 60:
        return "30.01-60"
    elif ltv <= 70:
        return "60.01-70"
    elif ltv <= 75:
        return "70.01-75"
    else:
        return "75.01-80"


def get_credit_score_bucket(credit_score: int) -> str:
    """Determine credit score bucket for lookup"""
    if credit_score >= 780:
        return ">=780"
    elif credit_score >= 760:
        return "760-779"
    elif credit_score >= 740:
        return "740-759"
    elif credit_score >= 720:
        return "720-739"
    elif credit_score >= 700:
        return "700-719"
    elif credit_score >= 680:
        return "680-699"
    elif credit_score >= 660:
        return "660-679"
    elif credit_score >= 640:
        return "640-659"
    else:
        return "<=639"


# =============================================================================
# LLPA MATRICES (Based on Fannie Mae 11.17.2025)
# =============================================================================

# Purchase Money Loans
PURCHASE_CREDIT_SCORE_LTV = {
    ">=780": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.000, "70.01-75": 0.000,
        "75.01-80": 0.375, "80.01-85": 0.375, "85.01-90": 0.250, "90.01-95": 0.250, ">95": 0.125
    },
    "760-779": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.000, "70.01-75": 0.250,
        "75.01-80": 0.625, "80.01-85": 0.625, "85.01-90": 0.500, "90.01-95": 0.500, ">95": 0.250
    },
    "740-759": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.125, "70.01-75": 0.375,
        "75.01-80": 0.875, "80.01-85": 1.000, "85.01-90": 0.750, "90.01-95": 0.625, ">95": 0.500
    },
    "720-739": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.250, "70.01-75": 0.750,
        "75.01-80": 1.250, "80.01-85": 1.250, "85.01-90": 1.000, "90.01-95": 0.875, ">95": 0.750
    },
    "700-719": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.375, "70.01-75": 0.875,
        "75.01-80": 1.375, "80.01-85": 1.500, "85.01-90": 1.250, "90.01-95": 1.125, ">95": 0.875
    },
    "680-699": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.625, "70.01-75": 1.125,
        "75.01-80": 1.750, "80.01-85": 1.875, "85.01-90": 1.500, "90.01-95": 1.375, ">95": 1.125
    },
    "660-679": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.750, "70.01-75": 1.375,
        "75.01-80": 1.875, "80.01-85": 2.125, "85.01-90": 1.750, "90.01-95": 1.625, ">95": 1.250
    },
    "640-659": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 1.125, "70.01-75": 1.500,
        "75.01-80": 2.250, "80.01-85": 2.500, "85.01-90": 2.000, "90.01-95": 1.875, ">95": 1.500
    },
    "<=639": {
        "<=30": 0.000, "30.01-60": 0.125, "60.01-70": 1.500, "70.01-75": 2.125,
        "75.01-80": 2.750, "80.01-85": 2.875, "85.01-90": 2.625, "90.01-95": 2.250, ">95": 1.750
    }
}

# Limited Cash-out Refinance
LIMITED_CASHOUT_CREDIT_SCORE_LTV = {
    ">=780": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.000, "70.01-75": 0.125,
        "75.01-80": 0.500, "80.01-85": 0.625, "85.01-90": 0.500, "90.01-95": 0.375, ">95": 0.375
    },
    "760-779": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.125, "70.01-75": 0.375,
        "75.01-80": 0.875, "80.01-85": 1.000, "85.01-90": 0.750, "90.01-95": 0.625, ">95": 0.625
    },
    "740-759": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.250, "70.01-75": 0.750,
        "75.01-80": 1.125, "80.01-85": 1.375, "85.01-90": 1.125, "90.01-95": 1.000, ">95": 1.000
    },
    "720-739": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.500, "70.01-75": 1.000,
        "75.01-80": 1.625, "80.01-85": 1.750, "85.01-90": 1.500, "90.01-95": 1.250, ">95": 1.250
    },
    "700-719": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.625, "70.01-75": 1.250,
        "75.01-80": 1.875, "80.01-85": 2.125, "85.01-90": 1.750, "90.01-95": 1.625, ">95": 1.625
    },
    "680-699": {
        "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.875, "70.01-75": 1.625,
        "75.01-80": 2.250, "80.01-85": 2.500, "85.01-90": 2.125, "90.01-95": 1.750, ">95": 1.750
    },
    "660-679": {
        "<=30": 0.000, "30.01-60": 0.125, "60.01-70": 1.125, "70.01-75": 1.875,
        "75.01-80": 2.500, "80.01-85": 3.000, "85.01-90": 2.375, "90.01-95": 2.125, ">95": 2.125
    },
    "640-659": {
        "<=30": 0.000, "30.01-60": 0.250, "60.01-70": 1.375, "70.01-75": 2.125,
        "75.01-80": 2.875, "80.01-85": 3.375, "85.01-90": 2.875, "90.01-95": 2.500, ">95": 2.500
    },
    "<=639": {
        "<=30": 0.000, "30.01-60": 0.375, "60.01-70": 1.750, "70.01-75": 2.500,
        "75.01-80": 3.500, "80.01-85": 3.875, "85.01-90": 3.625, "90.01-95": 2.500, ">95": 2.500
    }
}

# Property Type Adjustments
PURCHASE_CONDO = {
    "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.125, "70.01-75": 0.125,
    "75.01-80": 0.750, "80.01-85": 0.750, "85.01-90": 0.750, "90.01-95": 0.750, ">95": 0.750
}

PURCHASE_INVESTMENT = {
    "<=30": 1.125, "30.01-60": 1.125, "60.01-70": 1.625, "70.01-75": 2.125,
    "75.01-80": 3.375, "80.01-85": 4.125, "85.01-90": 4.125, "90.01-95": 4.125, ">95": 4.125
}

PURCHASE_SECOND_HOME = {
    "<=30": 1.125, "30.01-60": 1.125, "60.01-70": 1.625, "70.01-75": 2.125,
    "75.01-80": 3.375, "80.01-85": 4.125, "85.01-90": 4.125, "90.01-95": 4.125, ">95": 4.125
}

PURCHASE_2_TO_4_UNIT = {
    "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.375, "70.01-75": 0.375,
    "75.01-80": 0.625, "80.01-85": 0.625, "85.01-90": 0.625, "90.01-95": 0.625, ">95": 0.625
}

PURCHASE_HIGH_BALANCE_FIXED = {
    "<=30": 0.500, "30.01-60": 0.500, "60.01-70": 0.750, "70.01-75": 0.750,
    "75.01-80": 1.000, "80.01-85": 1.000, "85.01-90": 1.000, "90.01-95": 1.000, ">95": 1.000
}


def calculate_conventional_llpa(credit_score: int, ltv: float, loan_amount: float,
                                 loan_purpose: str = "Rate/Term Refinance",
                                 property_type: str = "Single Family",
                                 occupancy: str = "Primary Residence") -> dict:
    """
    Calculate conventional LLPA for a loan profile

    Returns:
        Dictionary with LLPA breakdown and total
    """
    adjustments = {}

    # Get buckets
    score_bucket = get_credit_score_bucket(credit_score)

    # Base Credit Score/LTV adjustment
    if loan_purpose == "Purchase":
        ltv_bucket = get_ltv_bucket(ltv)
        adjustments["Credit Score / LTV"] = PURCHASE_CREDIT_SCORE_LTV[score_bucket][ltv_bucket]
    else:  # Rate/Term Refinance
        ltv_bucket = get_ltv_bucket(ltv)
        adjustments["Credit Score / LTV"] = LIMITED_CASHOUT_CREDIT_SCORE_LTV[score_bucket][ltv_bucket]

    # Property Type
    if property_type == "Condo":
        adjustments["Property Type"] = PURCHASE_CONDO[ltv_bucket]
    elif property_type in ["2-Unit", "3-Unit", "4-Unit"]:
        adjustments["Property Type"] = PURCHASE_2_TO_4_UNIT[ltv_bucket]
    else:
        adjustments["Property Type"] = 0.0

    # Occupancy
    if occupancy == "Investment Property":
        adjustments["Occupancy"] = PURCHASE_INVESTMENT[ltv_bucket]
    elif occupancy == "Second Home":
        adjustments["Occupancy"] = PURCHASE_SECOND_HOME[ltv_bucket]
    else:
        adjustments["Occupancy"] = 0.0

    # High Balance
    if loan_amount > CONFORMING_LIMIT_2025:
        adjustments["High Balance"] = PURCHASE_HIGH_BALANCE_FIXED[ltv_bucket]
    else:
        adjustments["High Balance"] = 0.0

    # Calculate total
    total_llpa = sum(adjustments.values())
    adjustments["Total LLPA"] = total_llpa

    return adjustments


def calculate_available_rate(base_rate: float, credit_score: int, ltv: float,
                              loan_amount: float, loan_type: str = "Conventional",
                              property_type: str = "Single Family",
                              occupancy: str = "Primary Residence",
                              state_adjustment: float = 0.0) -> dict:
    """
    Calculate the available rate for a client

    Args:
        base_rate: Today's base rate (as percentage, e.g., 6.5)
        credit_score: Client's credit score
        ltv: Loan-to-value ratio
        loan_amount: Loan amount
        loan_type: "Conventional" or "FHA"
        property_type: Property type
        occupancy: Occupancy type
        state_adjustment: State-specific adjustment

    Returns:
        Dictionary with available rate and breakdown
    """
    if loan_type.upper() == "FHA":
        # FHA has no LLPAs - rate is just base + state
        final_rate = base_rate + state_adjustment
        return {
            'base_rate': base_rate,
            'total_llpa': 0.0,
            'state_adjustment': state_adjustment,
            'final_rate': final_rate,
            'final_rate_decimal': final_rate / 100,
            'adjustments': {},
            'loan_type': 'FHA',
            'note': 'FHA does not have LLPAs'
        }

    # Conventional - calculate LLPAs
    adjustments = calculate_conventional_llpa(
        credit_score=credit_score,
        ltv=ltv,
        loan_amount=loan_amount,
        loan_purpose="Rate/Term Refinance",
        property_type=property_type,
        occupancy=occupancy
    )

    total_llpa = adjustments.get("Total LLPA", 0.0)
    final_rate = base_rate + total_llpa + state_adjustment

    return {
        'base_rate': base_rate,
        'total_llpa': total_llpa,
        'state_adjustment': state_adjustment,
        'final_rate': final_rate,
        'final_rate_decimal': final_rate / 100,
        'adjustments': adjustments,
        'loan_type': 'Conventional'
    }


# =============================================================================
# PRICING GRID FUNCTIONS
# =============================================================================

def get_pricing_grid(loan_type: str = "Conventional") -> dict:
    """
    Get the pricing grid from admin settings

    Returns:
        Dictionary mapping rate (str) to points (float)
        Empty dict if no grid configured
    """
    from database import get_admin_settings
    import json

    settings = get_admin_settings()
    grid_key = f"pricing_grid_{loan_type.lower()}"
    grid_json = settings.get(grid_key, '{}')

    try:
        return json.loads(grid_json)
    except:
        return {}


def get_available_rates_with_points(base_rate: float, credit_score: int, ltv: float,
                                     loan_amount: float, loan_type: str = "Conventional",
                                     property_type: str = "Single Family",
                                     occupancy: str = "Primary Residence") -> list:
    """
    Get all available rates from pricing grid with their adjusted points cost

    The points in the grid are for a "clean" borrower (high credit, low LTV).
    For borrowers with LLPAs, we adjust the points cost accordingly.

    Returns:
        List of dicts with 'rate', 'base_points', 'llpa_points', 'total_points', 'total_cost'
    """
    grid = get_pricing_grid(loan_type)

    if not grid:
        return []

    # Calculate LLPA for this borrower
    if loan_type.upper() == "CONVENTIONAL":
        adjustments = calculate_conventional_llpa(
            credit_score=credit_score,
            ltv=ltv,
            loan_amount=loan_amount,
            loan_purpose="Rate/Term Refinance",
            property_type=property_type,
            occupancy=occupancy
        )
        llpa_points = adjustments.get("Total LLPA", 0.0)
    else:
        llpa_points = 0.0

    results = []
    for rate_str, base_points in sorted(grid.items(), key=lambda x: float(x[0]), reverse=True):
        rate = float(rate_str)
        total_points = base_points + llpa_points
        total_cost = total_points * loan_amount / 100

        results.append({
            'rate': rate,
            'rate_str': f"{rate:.3f}%",
            'base_points': base_points,
            'llpa_points': llpa_points,
            'total_points': total_points,
            'total_cost': total_cost,
            'is_par': abs(base_points) < 0.001,
            'has_credit': total_points < 0,
            'has_cost': total_points > 0
        })

    return results


def get_par_rate_for_borrower(base_rate: float, credit_score: int, ltv: float,
                               loan_amount: float, loan_type: str = "Conventional",
                               property_type: str = "Single Family",
                               occupancy: str = "Primary Residence") -> dict:
    """
    Find the par rate (zero points) for a specific borrower profile

    Since LLPAs add points cost, the "par" rate for a borrower with LLPAs
    will be higher than the market par rate.

    Returns:
        Dict with par rate info or None if no grid configured
    """
    rates = get_available_rates_with_points(
        base_rate=base_rate,
        credit_score=credit_score,
        ltv=ltv,
        loan_amount=loan_amount,
        loan_type=loan_type,
        property_type=property_type,
        occupancy=occupancy
    )

    if not rates:
        return None

    # Find the rate closest to zero total points
    best_rate = min(rates, key=lambda x: abs(x['total_points']))

    # Also find the exact par rate from grid (where base_points = 0)
    grid_par = next((r for r in rates if r['is_par']), None)

    return {
        'borrower_par_rate': best_rate['rate'],
        'borrower_par_points': best_rate['total_points'],
        'grid_par_rate': grid_par['rate'] if grid_par else None,
        'llpa_adjustment': best_rate['llpa_points'],
        'all_rates': rates
    }


def get_best_rate_for_closing_cost(target_cost: float, base_rate: float, credit_score: int,
                                    ltv: float, loan_amount: float,
                                    loan_type: str = "Conventional",
                                    property_type: str = "Single Family",
                                    occupancy: str = "Primary Residence") -> dict:
    """
    Find the best rate achievable for a target closing cost budget

    Args:
        target_cost: Maximum closing cost budget (can be negative for credit)

    Returns:
        Dict with best available rate within budget
    """
    rates = get_available_rates_with_points(
        base_rate=base_rate,
        credit_score=credit_score,
        ltv=ltv,
        loan_amount=loan_amount,
        loan_type=loan_type,
        property_type=property_type,
        occupancy=occupancy
    )

    if not rates:
        return None

    # Filter to rates within budget and find lowest rate
    affordable_rates = [r for r in rates if r['total_cost'] <= target_cost]

    if not affordable_rates:
        # Return highest rate (most credit) if nothing is affordable
        return {
            'rate': rates[0]['rate'],
            'points': rates[0]['total_points'],
            'cost': rates[0]['total_cost'],
            'within_budget': False,
            'message': 'No rates available within budget. Showing highest rate (most credit).'
        }

    # Get lowest rate within budget
    best = min(affordable_rates, key=lambda x: x['rate'])

    return {
        'rate': best['rate'],
        'points': best['total_points'],
        'cost': best['total_cost'],
        'within_budget': True,
        'message': f"Best rate within ${target_cost:,.0f} budget"
    }


# =============================================================================
# FHA MIP INFORMATION
# =============================================================================

def get_fha_mip_info(ltv: float, loan_amount: float, loan_term: int = 30) -> dict:
    """Get FHA MIP information"""
    fha_base_limit = 726200

    # Upfront MIP
    upfront_mip_rate = 1.75
    upfront_mip_amount = loan_amount * 0.0175

    # Annual MIP
    if loan_term > 15:
        if loan_amount <= fha_base_limit:
            annual_mip = 0.50 if ltv <= 90 else 0.55
        else:
            annual_mip = 0.70 if ltv <= 90 else 0.75
    else:
        if loan_amount <= fha_base_limit:
            annual_mip = 0.15 if ltv <= 90 else 0.40
        else:
            annual_mip = 0.40 if ltv <= 90 else 0.65

    monthly_mip = (loan_amount * annual_mip / 100) / 12
    mip_duration = "11 years" if ltv <= 90 else "Life of loan"

    return {
        'upfront_mip_rate': upfront_mip_rate,
        'upfront_mip_amount': upfront_mip_amount,
        'annual_mip_rate': annual_mip,
        'monthly_mip': monthly_mip,
        'mip_duration': mip_duration,
        'total_loan_with_ufmip': loan_amount + upfront_mip_amount
    }
