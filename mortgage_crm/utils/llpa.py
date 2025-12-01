"""
Loan-Level Price Adjustments (LLPA) Module
Based on Fannie Mae LLPA Matrix dated 11.17.2025

This module provides comprehensive LLPA calculations for conventional loans.
FHA loans do not have LLPAs - they use Mortgage Insurance Premiums (MIP) instead.
"""

# =============================================================================
# LOAN LIMITS (2025)
# =============================================================================
CONFORMING_LIMIT_2025 = 806500
HIGH_BALANCE_LIMIT_2025 = 1209750

# FHA Limits
FHA_FLOOR_2025 = 498257
FHA_CEILING_2025 = 1149825


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
# CREDIT SCORE / LTV MATRICES
# =============================================================================

# Purchase Money Loans (Page 2)
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

# Limited Cash-out Refinance (Page 3)
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

# Cash-Out Refinance (Page 4) - Max LTV is 80%
CASHOUT_CREDIT_SCORE_LTV = {
    ">=780": {
        "<=30": 0.375, "30.01-60": 0.375, "60.01-70": 0.625, "70.01-75": 0.875, "75.01-80": 1.375
    },
    "760-779": {
        "<=30": 0.375, "30.01-60": 0.375, "60.01-70": 0.875, "70.01-75": 1.250, "75.01-80": 1.875
    },
    "740-759": {
        "<=30": 0.375, "30.01-60": 0.375, "60.01-70": 1.000, "70.01-75": 1.625, "75.01-80": 2.375
    },
    "720-739": {
        "<=30": 0.375, "30.01-60": 0.500, "60.01-70": 1.375, "70.01-75": 2.000, "75.01-80": 2.750
    },
    "700-719": {
        "<=30": 0.375, "30.01-60": 0.500, "60.01-70": 1.625, "70.01-75": 2.625, "75.01-80": 3.250
    },
    "680-699": {
        "<=30": 0.375, "30.01-60": 0.625, "60.01-70": 2.000, "70.01-75": 2.875, "75.01-80": 3.750
    },
    "660-679": {
        "<=30": 0.375, "30.01-60": 0.875, "60.01-70": 2.750, "70.01-75": 4.000, "75.01-80": 4.750
    },
    "640-659": {
        "<=30": 0.375, "30.01-60": 1.375, "60.01-70": 3.125, "70.01-75": 4.625, "75.01-80": 5.125
    },
    "<=639": {
        "<=30": 0.375, "30.01-60": 1.375, "60.01-70": 3.375, "70.01-75": 4.875, "75.01-80": 5.125
    }
}


# =============================================================================
# PROPERTY TYPE ADJUSTMENTS
# =============================================================================

CONDO_ADJUSTMENT = {
    "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.125, "70.01-75": 0.125,
    "75.01-80": 0.750, "80.01-85": 0.750, "85.01-90": 0.750, "90.01-95": 0.750, ">95": 0.750
}

MULTI_UNIT_ADJUSTMENT = {
    "<=30": 0.000, "30.01-60": 0.000, "60.01-70": 0.375, "70.01-75": 0.375,
    "75.01-80": 0.625, "80.01-85": 0.625, "85.01-90": 0.625, "90.01-95": 0.625, ">95": 0.625
}

MANUFACTURED_ADJUSTMENT = {
    "<=30": 0.500, "30.01-60": 0.500, "60.01-70": 0.500, "70.01-75": 0.500,
    "75.01-80": 0.500, "80.01-85": 0.500, "85.01-90": 0.500, "90.01-95": 0.500, ">95": 0.500
}


# =============================================================================
# OCCUPANCY ADJUSTMENTS
# =============================================================================

INVESTMENT_PROPERTY_ADJUSTMENT = {
    "<=30": 1.125, "30.01-60": 1.125, "60.01-70": 1.625, "70.01-75": 2.125,
    "75.01-80": 3.375, "80.01-85": 4.125, "85.01-90": 4.125, "90.01-95": 4.125, ">95": 4.125
}

SECOND_HOME_ADJUSTMENT = {
    "<=30": 1.125, "30.01-60": 1.125, "60.01-70": 1.625, "70.01-75": 2.125,
    "75.01-80": 3.375, "80.01-85": 4.125, "85.01-90": 4.125, "90.01-95": 4.125, ">95": 4.125
}


# =============================================================================
# HIGH BALANCE ADJUSTMENTS
# =============================================================================

HIGH_BALANCE_FIXED = {
    "<=30": 0.500, "30.01-60": 0.500, "60.01-70": 0.750, "70.01-75": 0.750,
    "75.01-80": 1.000, "80.01-85": 1.000, "85.01-90": 1.000, "90.01-95": 1.000, ">95": 1.000
}

HIGH_BALANCE_ARM = {
    "<=30": 1.250, "30.01-60": 1.250, "60.01-70": 1.500, "70.01-75": 1.500,
    "75.01-80": 2.500, "80.01-85": 2.500, "85.01-90": 2.500, "90.01-95": 2.750, ">95": 2.750
}


# =============================================================================
# SUBORDINATE FINANCING
# =============================================================================

SUBORDINATE_FINANCING_ADJUSTMENT = {
    "<=30": 0.625, "30.01-60": 0.625, "60.01-70": 0.625, "70.01-75": 0.875,
    "75.01-80": 1.125, "80.01-85": 1.125, "85.01-90": 1.125, "90.01-95": 1.875, ">95": 1.875
}


# =============================================================================
# MAIN CALCULATION FUNCTIONS
# =============================================================================

def get_credit_score_ltv_adjustment(credit_score: int, ltv: float, loan_purpose: str) -> float:
    """Get the base Credit Score / LTV adjustment based on loan purpose"""
    score_bucket = get_credit_score_bucket(credit_score)

    if loan_purpose == "Purchase":
        ltv_bucket = get_ltv_bucket(ltv)
        return PURCHASE_CREDIT_SCORE_LTV[score_bucket][ltv_bucket]
    elif loan_purpose == "Rate/Term Refinance":
        ltv_bucket = get_ltv_bucket(ltv)
        return LIMITED_CASHOUT_CREDIT_SCORE_LTV[score_bucket][ltv_bucket]
    elif loan_purpose == "Cash-Out Refinance":
        ltv_bucket = get_ltv_bucket_cashout(ltv)
        return CASHOUT_CREDIT_SCORE_LTV[score_bucket][ltv_bucket]

    return 0.0


def get_property_type_adjustment(property_type: str, ltv: float, loan_purpose: str) -> float:
    """Get property type adjustment"""
    if loan_purpose == "Cash-Out Refinance":
        ltv_bucket = get_ltv_bucket_cashout(ltv)
    else:
        ltv_bucket = get_ltv_bucket(ltv)

    if property_type == "Condo":
        return CONDO_ADJUSTMENT.get(ltv_bucket, 0.0)
    elif property_type in ["2-Unit", "3-Unit", "4-Unit"]:
        return MULTI_UNIT_ADJUSTMENT.get(ltv_bucket, 0.0)
    elif property_type == "Manufactured Home":
        return MANUFACTURED_ADJUSTMENT.get(ltv_bucket, 0.0)

    return 0.0


def get_occupancy_adjustment(occupancy: str, ltv: float, loan_purpose: str) -> float:
    """Get occupancy type adjustment"""
    if loan_purpose == "Cash-Out Refinance":
        ltv_bucket = get_ltv_bucket_cashout(ltv)
    else:
        ltv_bucket = get_ltv_bucket(ltv)

    if occupancy == "Investment Property":
        return INVESTMENT_PROPERTY_ADJUSTMENT.get(ltv_bucket, 0.0)
    elif occupancy == "Second Home":
        return SECOND_HOME_ADJUSTMENT.get(ltv_bucket, 0.0)

    return 0.0


def get_high_balance_adjustment(loan_amount: float, ltv: float, is_arm: bool = False) -> float:
    """Get high balance loan adjustment"""
    if loan_amount <= CONFORMING_LIMIT_2025:
        return 0.0

    ltv_bucket = get_ltv_bucket(ltv)

    if is_arm:
        return HIGH_BALANCE_ARM.get(ltv_bucket, 0.0)
    else:
        return HIGH_BALANCE_FIXED.get(ltv_bucket, 0.0)


def get_subordinate_financing_adjustment(ltv: float, cltv: float) -> float:
    """Get subordinate financing adjustment (when CLTV > LTV)"""
    if cltv <= ltv:
        return 0.0

    ltv_bucket = get_ltv_bucket(ltv)
    return SUBORDINATE_FINANCING_ADJUSTMENT.get(ltv_bucket, 0.0)


def calculate_total_llpa(credit_score: int, ltv: float, loan_amount: float,
                         loan_purpose: str = "Rate/Term Refinance",
                         property_type: str = "Single Family",
                         occupancy: str = "Primary Residence",
                         is_arm: bool = False,
                         cltv: float = None,
                         is_homeready: bool = False,
                         is_first_time_buyer_low_income: bool = False) -> dict:
    """
    Calculate total LLPA for a conventional loan

    Args:
        credit_score: Borrower's credit score
        ltv: Loan-to-value ratio
        loan_amount: Loan amount
        loan_purpose: "Purchase", "Rate/Term Refinance", or "Cash-Out Refinance"
        property_type: "Single Family", "Condo", "2-Unit", etc.
        occupancy: "Primary Residence", "Second Home", "Investment Property"
        is_arm: Is this an adjustable rate mortgage?
        cltv: Combined LTV (if subordinate financing exists)
        is_homeready: Is this a HomeReady loan?
        is_first_time_buyer_low_income: First-time buyer at <=100% AMI?

    Returns:
        Dictionary with LLPA breakdown and total
    """
    # Check for LLPA waivers
    if is_homeready or is_first_time_buyer_low_income:
        return {
            "Credit Score / LTV": 0.0,
            "Property Type": 0.0,
            "Occupancy": 0.0,
            "High Balance": 0.0,
            "Subordinate Financing": 0.0,
            "Total LLPA": 0.0,
            "LLPA Waiver Applied": True,
            "waiver_reason": "HomeReady" if is_homeready else "First-Time Buyer Low Income"
        }

    if cltv is None:
        cltv = ltv

    adjustments = {}

    # 1. Base Credit Score / LTV adjustment
    adjustments["Credit Score / LTV"] = get_credit_score_ltv_adjustment(
        credit_score, ltv, loan_purpose
    )

    # 2. Property Type adjustment
    adjustments["Property Type"] = get_property_type_adjustment(
        property_type, ltv, loan_purpose
    )

    # 3. Occupancy adjustment
    adjustments["Occupancy"] = get_occupancy_adjustment(
        occupancy, ltv, loan_purpose
    )

    # 4. High Balance adjustment
    adjustments["High Balance"] = get_high_balance_adjustment(
        loan_amount, ltv, is_arm
    )

    # 5. Subordinate Financing adjustment
    adjustments["Subordinate Financing"] = get_subordinate_financing_adjustment(
        ltv, cltv
    )

    # Calculate total
    total = sum(v for v in adjustments.values() if isinstance(v, (int, float)))
    adjustments["Total LLPA"] = total
    adjustments["LLPA Waiver Applied"] = False

    return adjustments


# =============================================================================
# FHA MIP CALCULATIONS
# =============================================================================

def get_fha_mip(ltv: float, loan_amount: float, loan_term_years: int = 30) -> dict:
    """
    Get FHA Mortgage Insurance Premium information

    FHA does NOT have LLPAs - they use MIP instead.
    """
    fha_base_limit = 726200

    # Upfront MIP (UFMIP) - always 1.75%
    upfront_mip_rate = 1.75
    upfront_mip_amount = loan_amount * 0.0175

    # Annual MIP based on loan term and amount
    if loan_term_years > 15:
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


# FHA minimum credit score requirements
FHA_MIN_CREDIT_SCORES = {
    "3.5_percent_down": 580,
    "10_percent_down": 500
}
