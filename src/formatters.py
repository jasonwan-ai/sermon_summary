#!/usr/bin/env python3
"""
Formatting utility functions.
"""

from pathlib import Path
from datetime import datetime


def format_duration(start_time: datetime, end_time: datetime) -> str:
    """
    Format duration between two datetime objects.
    
    Args:
        start_time: Start datetime
        end_time: End datetime
    
    Returns:
        Formatted duration string (without microseconds)
    """
    duration = end_time - start_time
    return str(duration).split('.')[0]  # Remove microseconds for cleaner output


def extract_date_from_filename(filename: str) -> str:
    """
    Extract and format date from filename.
    
    Expected format: {YYMMDD}_{time}_{description}.mkv
    Example: 260104_12-27_Afternoon.mkv -> "January 4, 2026"
    
    Args:
        filename: The filename (with or without extension)
    
    Returns:
        Formatted date string (e.g., "January 4, 2026")
    """
    base_name = Path(filename).stem
    parts = base_name.split("_")
    
    if not parts:
        return "Unknown Date"
    
    date_str = parts[0]
    
    # Parse YYMMDD format
    if len(date_str) == 6 and date_str.isdigit():
        try:
            year = 2000 + int(date_str[:2])  # Assume 20XX
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            date_obj = datetime(year, month, day)
            return date_obj.strftime("%B %d, %Y")
        except (ValueError, IndexError):
            pass
    
    return "Unknown Date"
