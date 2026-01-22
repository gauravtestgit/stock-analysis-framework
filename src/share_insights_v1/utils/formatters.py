def format_currency(value):
    """Format currency value with appropriate scale (B/M/K)"""
    if abs(value) >= 1e9:
        return f"${value/1e9:.1f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.1f}M"
    elif abs(value) >= 1e3:
        return f"${value/1e3:.1f}K"
    else:
        return f"${value:.0f}"

def get_scale_and_label(value):
    """Get scale divisor and label for a value"""
    if abs(value) >= 1e9:
        return 1e9, "B"
    elif abs(value) >= 1e6:
        return 1e6, "M"
    elif abs(value) >= 1e3:
        return 1e3, "K"
    else:
        return 1, ""
