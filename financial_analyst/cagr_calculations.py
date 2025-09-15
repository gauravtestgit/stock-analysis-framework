import pandas as pd
import numpy as np
from util.debug_printer import debug_print

def check_outlier(values, suspect_outlier) -> bool:
    std_dev = np.std(values)
    mean_val = np.mean(values)
    outlier_threshold = mean_val - 2 * std_dev
    return suspect_outlier < outlier_threshold


def calculate_traditional_cagr_with_outliers(values, max_threshold, default = 0.05):
    """Calculate CAGR but detect and handle outlier periods"""
    cagr_default = default
    if len(values) < 2:
        return cagr_default
        
    # Check for potential COVID impact (2020-2021 outliers)
    # If we have 4+ years of data, try excluding the lowest year
    if len(values) >= 4:
        min_idx = np.argmin(values)

        # If the minimum is not the most recent year, try excluding it
        if min_idx != 0 and check_outlier(values, values[min_idx]):
            adjusted_values = np.delete(values, min_idx)
            adjusted_period = len(adjusted_values) - 1
            if adjusted_period >= 2 and adjusted_values[-1] > 0 and adjusted_values[0] > 0:
                adjusted_cagr = (adjusted_values[0] / adjusted_values[-1]) ** (1/adjusted_period) - 1
                print(f"Outlier detected at index {min_idx}, adjusted CAGR: {adjusted_cagr:.2%}")
                if adjusted_cagr <= max_threshold:
                    return adjusted_cagr
    
    # Standard CAGR calculation
    if values[0] > 0 and values[-1] > 0:
        period = len(values) - 1
        cagr = (values[0] / values[-1]) ** (1/period) - 1
        return min(cagr, max_threshold)
    
    return cagr_default

def calculate_average_growth_rate(values, default = 0.05):
    """Calculate average of year-over-year growth rates"""
    growth_rate_default = default
    if len(values) < 2:
        return growth_rate_default
        
    growth_rates = []
    for i in range(len(values)-1,0,-1):
        if values[i] > 0:
            growth = (values[i-1] / values[i]) - 1
            # Cap extreme values
            growth = max(min(growth, growth_rate_default), -0.3)
            growth_rates.append(growth)
    
    return np.mean(growth_rates) if growth_rates else growth_rate_default

def calculate_median_growth_rate(values, default = 0.05):
    yoy_growth_rates = []
    growth_rate_default = default
    for i in range(len(values)-1,0,-1):
        if values[i] > 0:  # Avoid division by zero
            growth = (values[i-1] / values[i]) - 1
            # Cap extreme growth rates
            growth = max(min(growth, 1.0), -0.5)  # Cap between -50% and 100%
            yoy_growth_rates.append(growth)
        
        median_growth = np.median(yoy_growth_rates) if yoy_growth_rates else growth_rate_default
    return median_growth

def calculate_simple_cagr(values, default = 0.05):
    """Simple CAGR calculation without handling outliers"""
    if len(values) < 2:
        return default

    if values[-1] != 0:
        period = len(values) - 1
        cagr = (values[0] / values[-1]) ** (1/period) - 1
        return cagr

    return default

def get_cagr(values, max_threshold=0.15, default=0.05, simple_cagr:bool = True):
    """Simple CAGR selection logic"""
    if simple_cagr:
        return calculate_simple_cagr(values, default)
    
    debug_print(f"Calculating CAGR with max threshold: {max_threshold:.2%}, default: {default:.2%}")
    traditional_cagr = cagr = calculate_traditional_cagr_with_outliers(values,0.15,0.05)
    avg_cagr = calculate_average_growth_rate(values, 0.05)
    median_cagr = calculate_median_growth_rate(values, 0.05)
    conservative_default = 0.02
    debug_print(f"Traditional CAGR: {traditional_cagr:.2%}, Average CAGR: {avg_cagr:.2%}, Median CAGR: {median_cagr:.2%}")

    valid_positive = [c for c in [traditional_cagr, avg_cagr, median_cagr] 
                     if c is not None and c >= 0]
    
    if valid_positive:
        return min(np.median(valid_positive), max_threshold)  # Use median of valid positive CAGRs
    
    # If no valid positive CAGRs, check if we have any positive ones (even above threshold)
    any_positive = [c for c in [traditional_cagr, avg_cagr, median_cagr] 
                   if c is not None and c >= 0]
    
    if any_positive:
        return min(min(any_positive), max_threshold)  # Cap the minimum positive
    
    # All negative - use conservative default
    return min(default, conservative_default)  # Conservative for declining business