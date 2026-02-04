"""
Export utilities for QA Gate Analysis App.
Handles Excel and CSV data exports.
"""

import pandas as pd
import io
import datetime
from pathlib import Path
import config

def to_excel(df: pd.DataFrame, failures_df: pd.DataFrame = None) -> bytes:
    """
    Export data to Excel format with multiple sheets.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Summary Sheet
        summary_stats = {
            'Metric': ['Total Sensors', 'Total Rejected', 'Overall Yield %'],
            'Value': [
                df['Custom field (Start Quantity)'].sum(),
                df['Custom field (Rejected Quantity)'].sum(),
                ((df['Custom field (Start Quantity)'].sum() - df['Custom field (Rejected Quantity)'].sum()) / 
                 df['Custom field (Start Quantity)'].sum() * 100) if df['Custom field (Start Quantity)'].sum() > 0 else 0
            ]
        }
        pd.DataFrame(summary_stats).to_excel(writer, sheet_name=config.EXCEL_SHEET_NAMES['summary'], index=False)
        
        # 2. Raw Data Sheet
        df.to_excel(writer, sheet_name=config.EXCEL_SHEET_NAMES['raw_data'], index=False)
        
        # 3. Failures Sheet
        if failures_df is not None and not failures_df.empty:
            failures_df.to_excel(writer, sheet_name=config.EXCEL_SHEET_NAMES['failures'], index=False)
        
        # Formatting
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            # Set columns width (heuristic)
            worksheet.set_column('A:Z', 20)
            
    return output.getvalue()

def to_csv(df: pd.DataFrame) -> str:
    """
    Export data to CSV format.
    """
    return df.to_csv(index=False).encode('utf-8')

def generate_filename(report_type: str, extension: str) -> str:
    """
    Generate a filename based on the template in config.
    """
    now = datetime.datetime.now()
    return config.EXPORT_FILENAME_TEMPLATE.format(
        date=now.strftime('%Y-%m-%d'),
        type=report_type,
        ext=extension
    )
