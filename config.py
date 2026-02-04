"""
Configuration module for QA Gate Analysis Application.
Centralizes all configurable settings for easy customization.
"""
import os
import streamlit as st
from pathlib import Path
from typing import Dict, List

# ==================== DATABASE SETTINGS ====================

# Database directory and file (for local dev)
DATA_DIR = Path('data')
DATABASE_FILE = DATA_DIR / 'qa_gate_data.db'

def get_database_url():
    """
    Get the database connection URL.
    Checks st.secrets for a cloud DB connection string first.
    """
    # 1. Check Streamlit Secrets (Cloud)
    if hasattr(st, 'secrets') and 'database' in st.secrets:
        # Expected format in secrets.toml: 
        # [database]
        # url = "postgresql://user:pass@host:port/db"
        return st.secrets['database']['url']
    
    # 2. Check Environment Variables
    env_url = os.getenv('DATABASE_URL')
    if env_url:
        # Standard Postgres URL or other
        return env_url
        
    # 3. Fallback to local SQLite
    DATA_DIR.mkdir(exist_ok=True)
    return f"sqlite:///{DATABASE_FILE}"

# Backup settings
ENABLE_AUTO_BACKUP = True
BACKUP_FREQUENCY_DAYS = 7
BACKUP_DIR = DATA_DIR / 'backups'
MAX_BACKUPS_TO_KEEP = 10


# ==================== UI CUSTOMIZATION ====================

# Application branding
APP_TITLE = "QA Gate Data Analysis"
COMPANY_NAME = "Sava Health"
PAGE_ICON = "📊"

# Theme colors (for custom styling if needed)
PRIMARY_COLOR = "#636EFA"
SECONDARY_COLOR = "#EF553B"
SUCCESS_COLOR = "#00CC96"
WARNING_COLOR = "#FFA15A"

# Chart color schemes
CHART_COLOR_SCALE_SEQUENTIAL = "RdYlGn"
CHART_COLOR_SCALE_DIVERGING = "Reds"


# ==================== PROCESS STEP MAPPINGS ====================

# Mapping of lot number prefixes to process steps
PROCESS_STEP_MAPPINGS = {
    'LN-C': 'Final Inspection',
    'LN-R': 'Outer Layer',
    'LN-Q': 'Dispensing',
    'LN-P': 'Screen Printing',
}

# Default process step for unrecognized lot numbers
DEFAULT_PROCESS_STEP = 'Others'


# ==================== ALERT THRESHOLDS ====================

# Yield thresholds
YIELD_WARNING_THRESHOLD = 85.0  # Warn if yield falls below this percentage
YIELD_CRITICAL_THRESHOLD = 75.0  # Critical alert if yield falls below this

# Time thresholds
AVG_TIME_PER_GATE_WARNING = 3.0  # Hours - warn if average time exceeds this
MAX_TIME_PER_GATE = 8.0  # Hours - flag gates that took longer than this

# Volume thresholds
MIN_SENSORS_PER_GATE = 10  # Flag gates with fewer sensors as potentially incomplete
MAX_SENSORS_PER_GATE = 1000  # Flag gates with more sensors as potential data errors

# Failure rate thresholds
FAILURE_RATE_WARNING = 15.0  # Percentage
FAILURE_RATE_CRITICAL = 25.0  # Percentage


# ==================== EXPORT SETTINGS ====================

# Default export formats
DEFAULT_EXPORT_FORMAT = 'xlsx'  # Options: 'xlsx', 'csv', 'pdf'

# File naming convention
# Available placeholders: {date}, {time}, {type}, {company}
EXPORT_FILENAME_TEMPLATE = "QA_Gate_Report_{date}_{type}.{ext}"

# Export directory
EXPORT_DIR = Path('exports')

# Excel export settings
EXCEL_SHEET_NAMES = {
    'summary': 'Executive Summary',
    'raw_data': 'Raw Data',
    'failures': 'Failure Analysis',
    'trends': 'Trends',
}


# ==================== DATA VALIDATION ====================

# Validation rules
VALIDATION_RULES = {
    'allow_negative_quantities': False,
    'allow_rejected_greater_than_start': False,
    'require_issue_key': True,
    'require_created_date': True,
    'max_yield_percentage': 100.0,
}

# Outlier detection settings
OUTLIER_DETECTION_ENABLED = True
OUTLIER_Z_SCORE_THRESHOLD = 3.0  # Standard deviations from mean


# ==================== FILTERING DEFAULTS ====================

# Default date range for filters (in days from today)
DEFAULT_DATE_RANGE_DAYS = 90

# Quick filter presets (name: days_back)
DATE_PRESETS = {
    'Last 7 Days': 7,
    'Last 30 Days': 30,
    'Last 90 Days': 90,
    'Last 6 Months': 180,
    'Last Year': 365,
}


# ==================== FAILURE MODE EXCLUSIONS ====================

# Failure modes to exclude from analysis (not actual failures)
EXCLUDED_FAILURE_MODES = [
    'Handover',
    '18.1 Trial',
    'Biodot',
    'Investor',
    'Dry Run',
    'Unknown',
    'Pass',
    ' ',
    '',
]


# ==================== REPORT SETTINGS ====================

# Number of top items to show in charts
TOP_N_FAILURE_MODES = 20
TOP_N_ASSIGNEES = 10

# Chart dimensions
CHART_HEIGHT = 400
CHART_WIDTH = 800


# ==================== EMAIL SETTINGS (Optional) ====================

# Email configuration for automated reports
EMAIL_ENABLED = False
EMAIL_SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS', '').split(',')

# Email report schedule (cron-like format)
EMAIL_REPORT_SCHEDULE = 'weekly'  # Options: 'daily', 'weekly', 'monthly'
EMAIL_REPORT_DAY = 'Monday'  # For weekly reports


# ==================== ADVANCED FEATURES ====================

# Enable/disable advanced features
ENABLE_ML_PREDICTIONS = False
ENABLE_ANOMALY_DETECTION = False
ENABLE_USER_AUTHENTICATION = False


# ==================== HELPER FUNCTIONS ====================

def get_process_step(lot_number: str) -> str:
    """
    Extract process step from lot number based on configured mappings.
    
    Args:
        lot_number: Lot number string (e.g., 'LN-C12345')
    
    Returns:
        Process step name
    """
    if not isinstance(lot_number, str):
        return DEFAULT_PROCESS_STEP
    
    lot_upper = lot_number.upper().strip()
    
    for prefix, step in PROCESS_STEP_MAPPINGS.items():
        if lot_upper.startswith(prefix):
            return step
    
    return DEFAULT_PROCESS_STEP


def is_failure_mode_excluded(failure_mode: str) -> bool:
    """
    Check if a failure mode should be excluded from analysis.
    
    Args:
        failure_mode: Failure mode string
    
    Returns:
        True if should be excluded, False otherwise
    """
    return failure_mode in EXCLUDED_FAILURE_MODES


def get_yield_status(yield_pct: float) -> str:
    """
    Get status level based on yield percentage.
    
    Args:
        yield_pct: Yield percentage (0-100)
    
    Returns:
        Status string: 'critical', 'warning', or 'normal'
    """
    if yield_pct < YIELD_CRITICAL_THRESHOLD:
        return 'critical'
    elif yield_pct < YIELD_WARNING_THRESHOLD:
        return 'warning'
    else:
        return 'normal'


def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [DATA_DIR, EXPORT_DIR]
    
    if ENABLE_AUTO_BACKUP:
        directories.append(BACKUP_DIR)
    
    for directory in directories:
        directory.mkdir(exist_ok=True, parents=True)


# Initialize directories on import
ensure_directories()
