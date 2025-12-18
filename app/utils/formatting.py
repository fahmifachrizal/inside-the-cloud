import re
from datetime import datetime

def format_pretty_date(date_str, hour_str="00"):
    """Transforms '20251218' -> '18 Dec 2025 - 00:00 UTC'"""
    try:
        dt = datetime.strptime(f"{date_str} {hour_str}", "%Y%m%d %H")
        return dt.strftime("%d %b %Y - %H:00 UTC")
    except:
        return f"{date_str} {hour_str}z"

def parse_gpm_filename(filename):
    """Extracts date from GPM filename"""
    try:
        match = re.search(r'\.(\d{8})-S(\d{4})', filename)
        if match:
            dt = datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M")
            return dt.strftime("%d %b %Y - %H:%M UTC")
    except:
        pass
    return filename[:25] + "..."