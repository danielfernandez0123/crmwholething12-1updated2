"""
Utility modules for Mortgage CRM
"""

from .rate_calculator import calculate_available_rate, calculate_conventional_llpa, get_fha_mip_info
from .optimal_threshold import calculate_trigger_rate, is_ready_to_refinance
