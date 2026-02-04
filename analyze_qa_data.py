
import pandas as pd
import regex as re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import config

# --- Configuration (Now using config.py) ---
CSV_FILE = 'Jira (11).csv' # Default input file
OUTPUT_HTML = 'qa_analysis_report.html'

def load_and_clean_data(filepath):
    """
    Loads the CSV and performs initial cleaning.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

    # Rename columns for easier access (stripping whitespace and normalizing)
    df.columns = [c.strip() for c in df.columns]
    
    # Convert 'Created' to datetime
    # Format appears to be like "26/Jan/26 2:35 PM" based on view_file output
    # Let's try flexible parsing
    df['Created_Date'] = pd.to_datetime(df['Created'], format='mixed', dayfirst=True, errors='coerce')
    
    # Extract Week Number (ISO)
    df['Week'] = df['Created_Date'].dt.isocalendar().week
    df['Year'] = df['Created_Date'].dt.isocalendar().year
    df['Year-Week'] = df['Created_Date'].dt.strftime('%Y-W%U')

    # Convert numeric fields
    numeric_cols = ['Custom field (Start Quantity)', 'Custom field (Rejected Quantity)']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculate Passed Quantity
    # df[col] is wrong here, fixing it
    df['Passed Quantity'] = df['Custom field (Start Quantity)'] - df['Custom field (Rejected Quantity)']
    
    # Categorize 'In-vitro' vs others
    # Looking at data: "QAG - Wearable Line - In Vitro" is in Summary or Issue Type?
    # View_file showed "QAG - Wearable Line - In Vitro" in Summary.
    # Let's check 'Summary' column.
    
    # Ensure Summary is string
    df['Summary'] = df['Summary'].fillna('')
    
    df['Process_Step'] = df['Summary'].apply(config.get_process_step)
    df['Is_In_Vitro'] = df['Summary'].str.contains('In Vitro|In-vitro', case=False, na=False)

    # --- Data Validation (Phase 5) ---
    if not config.VALIDATION_RULES['allow_negative_quantities']:
        df['Custom field (Start Quantity)'] = df['Custom field (Start Quantity)'].clip(lower=0)
        df['Custom field (Rejected Quantity)'] = df['Custom field (Rejected Quantity)'].clip(lower=0)

    if not config.VALIDATION_RULES['allow_rejected_greater_than_start']:
        # Cap rejections at start quantity
        df['Custom field (Rejected Quantity)'] = df.apply(
            lambda x: min(x['Custom field (Rejected Quantity)'], x['Custom field (Start Quantity)']), axis=1
        )

    # Recalculate passed and yield
    df['Passed Quantity'] = df['Custom field (Start Quantity)'] - df['Custom field (Rejected Quantity)']
    df['Yield %'] = (df['Passed Quantity'] / df['Custom field (Start Quantity)'] * 100).fillna(0)
    
    # Flag Outliers
    if config.OUTLIER_DETECTION_ENABLED:
        df['Is_Outlier'] = detect_outliers(df)

    return df

def detect_outliers(df):
    """Simple Z-score outlier detection based on yield."""
    if len(df) < 5:
        return [False] * len(df)
    
    y = df['Yield %']
    z_scores = (y - y.mean()) / y.std()
    return abs(z_scores) > config.OUTLIER_Z_SCORE_THRESHOLD

# Note: extract_process_step logic moved to config.get_process_step

def parse_failure_tables(df):
    """
    Parses the Jira markup tables in 'Custom field (Conclusion)' or 'Custom field (Rejected Sensors)'
    to extract individual failure entries.
    Returns a new DataFrame with one row per failure.
    """
    failures = []

    for index, row in df.iterrows():
        # Sources for failure data
        sources = [
            row.get('Custom field (Conclusion)', ''),
            row.get('Custom field (Rejected Sensors)', '')
        ]
        
        found_table = False
        for text in sources:
            if not isinstance(text, str):
                continue
            
            # Look for Jira table rows: |Cell1|Cell2|...|
            # We want to find the header to identify which column is 'Failure Mode'
            
            lines = text.split('\n')
            headers = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('||') and line.endswith('||'):
                    # Header row
                    # Remove empty strings from split result caused by leading/trailing ||
                    headers = [h.strip() for h in line.split('||') if h.strip()]
                    headers = [h.replace('*', '').lower() for h in headers] # Clean formatting like *Sensor ID*
                elif line.startswith('|') and line.endswith('|') and headers:
                    # Data row
                    cells = [c.strip() for c in line.split('|') if c.strip() != '']
                    
                    if len(cells) >= 2: # Need at least ID and failure info
                        # Try to map based on headers
                        sensor_id = "Unknown"
                        failure_mode = "Unknown"
                        
                        # Heuristic mapping if headers are known
                        if 'sensor id' in headers or 'sheet id' in headers or 'sensor' in headers:
                            try:
                                id_idx = -1
                                for candidates in ['sensor id', 'sensor', 'sheet id', 'sensor_id']:
                                    if candidates in headers:
                                        id_idx = headers.index(candidates)
                                        break
                                if id_idx != -1 and id_idx < len(cells):
                                    sensor_id = cells[id_idx]
                            except:
                                pass
                        
                        if 'failure mode' in headers or 'failure modes' in headers or 'allocation' in headers:
                             # Note: Allocation sometimes implies failure/status
                             try:
                                fail_idx = -1
                                for candidates in ['failure mode', 'failure modes', 'allocation']:
                                    if candidates in headers:
                                        fail_idx = headers.index(candidates)
                                        break
                                if fail_idx != -1 and fail_idx < len(cells):
                                    failure_mode = cells[fail_idx]
                             except:
                                 pass
                        else:
                            # Fallback: assume 2nd column is failure mode if only 2 columns
                            if len(cells) == 2 and sensor_id != "Unknown":
                                failure_mode = cells[1]

                        # Only add if we found something useful
                        if failure_mode != "Unknown":
                             failures.append({
                                'Issue key': row['Issue key'],
                                'Created_Date': row['Created_Date'],
                                'Week': row['Week'],
                                'Year-Week': row['Year-Week'],
                                'Process_Step': row['Process_Step'],
                                'Assignee': row['Assignee'],
                                'Sensor ID': sensor_id,
                                'Failure Mode': failure_mode
                            })
                            
    return pd.DataFrame(failures)

def generate_report(df, failures_df):
    """
    Generates an HTML report with Plotly visualizations.
    """
    
    # --- 1. Weekly Stats ---
    weekly_stats = df.groupby('Year-Week').agg({
        'Custom field (Start Quantity)': 'sum',
        'Custom field (Rejected Quantity)': 'sum'
    }).reset_index()
    weekly_stats['Failure Rate %'] = (weekly_stats['Custom field (Rejected Quantity)'] / weekly_stats['Custom field (Start Quantity)'] * 100).fillna(0)
    
    fig_weekly = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_weekly.add_trace(
        go.Bar(x=weekly_stats['Year-Week'], y=weekly_stats['Custom field (Start Quantity)'], name='Start Quantity', marker_color='#636EFA'),
        secondary_y=False
    )
    
    fig_weekly.add_trace(
        go.Scatter(x=weekly_stats['Year-Week'], y=weekly_stats['Failure Rate %'], name='Failure Rate %', line=dict(color='#EF553B', width=3)),
        secondary_y=True
    )
    
    fig_weekly.update_layout(title_text="Weekly Volume and Failure Rate")
    fig_weekly.update_yaxes(title_text="Quantity", secondary_y=False)
    fig_weekly.update_yaxes(title_text="Failure Rate (%)", secondary_y=True)

    # --- 2. Failure Category Pareto (Top Failure Modes) ---
    if not failures_df.empty:
        # Clean failure modes (strip whitespace, unify case if needed)
        failures_df['Failure Mode'] = failures_df['Failure Mode'].str.strip()
        
        # Filter out "Pass", "Handover", "Trial" if they appear in failure columns
        filtered_failures = failures_df[~failures_df['Failure Mode'].apply(config.is_failure_mode_excluded)]
        
        fail_counts = filtered_failures['Failure Mode'].value_counts().reset_index()
        fail_counts.columns = ['Failure Mode', 'Count']
        
        fig_pareto = px.bar(fail_counts.head(20), x='Count', y='Failure Mode', orientation='h', 
                            title='Top 20 Failure Modes', color='Count', color_continuous_scale='Reds')
        fig_pareto.update_layout(yaxis={'categoryorder':'total ascending'})
    else:
        fig_pareto = go.Figure()
        fig_pareto.add_annotation(text="No detailed failure data parsed", showarrow=False)

    # --- 3. Yield by Process Step ---
    process_stats = df.groupby('Process_Step').agg({
        'Custom field (Start Quantity)': 'sum',
        'Custom field (Rejected Quantity)': 'sum'
    }).reset_index()
    process_stats['Yield %'] = ((process_stats['Custom field (Start Quantity)'] - process_stats['Custom field (Rejected Quantity)']) / process_stats['Custom field (Start Quantity)'] * 100).fillna(0)
    
    fig_process = px.bar(process_stats, x='Process_Step', y='Yield %', title='Yield by Process Step',
                         color='Yield %', color_continuous_scale='RdYlGn', range_y=[0, 110])
    
    # --- 4. Failures by Assignee ---
    assignee_stats = df.groupby('Assignee')['Custom field (Rejected Quantity)'].sum().reset_index().sort_values('Custom field (Rejected Quantity)', ascending=False)
    fig_assignee = px.bar(assignee_stats, x='Assignee', y='Custom field (Rejected Quantity)', title='Total Rejections by Assignee')

    # --- Output HTML ---
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write("<html><head><title>QA Gate Analysis Report</title></head><body>")
        f.write("<h1>QA Gate Analysis Report</h1>")
        f.write(f"<p>Generated on: {datetime.datetime.now()}</p>")
        
        f.write("<h2>Executive Summary</h2>")
        total_start = df['Custom field (Start Quantity)'].sum()
        total_rej = df['Custom field (Rejected Quantity)'].sum()
        overall_yield = ((total_start - total_rej)/total_start * 100) if total_start > 0 else 0
        
        f.write(f"<ul>")
        f.write(f"<li><b>Total Sensors Processed:</b> {int(total_start)}</li>")
        f.write(f"<li><b>Total Rejected:</b> {int(total_rej)}</li>")
        f.write(f"<li><b>Overall Yield:</b> {overall_yield:.2f}%</li>")
        f.write(f"</ul>")
        
        f.write(fig_weekly.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_process.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_pareto.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_assignee.to_html(full_html=False, include_plotlyjs='cdn'))
        
        f.write("</body></html>")

    print(f"Report generated: {OUTPUT_HTML}")

if __name__ == "__main__":
    df = load_and_clean_data(CSV_FILE)
    if df is not None:
        print("Data loaded successfully.")
        print(f"Rows: {len(df)}")
        
        failures_df = parse_failure_tables(df)
        print(f"Extracted {len(failures_df)} failure records.")
        
        generate_report(df, failures_df)
