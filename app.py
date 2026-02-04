import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import analyze_qa_data as analysis
import database as db
import config
import export_utils
import datetime

# --- Page Config ---
st.set_page_config(page_title=config.APP_TITLE, page_icon=config.PAGE_ICON, layout="wide")

st.title(f"{config.PAGE_ICON} {config.APP_TITLE}")

# --- Sidebar: Data Management ---
st.sidebar.header("📊 Data Management")

# Show current record count
record_count = db.get_record_count()
st.sidebar.metric("Stored Records", record_count)

# Upload new data
st.sidebar.subheader("Add New Data")
uploaded_files = st.sidebar.file_uploader(
    "Upload CSV files (new data only)", 
    accept_multiple_files=True, 
    type=['csv'],
    help="Upload new QA gate exports. Duplicates will be automatically skipped."
)

if uploaded_files:
    with st.sidebar:
        with st.spinner("Processing uploads..."):
            total_new = 0
            total_dup = 0
            
            for file in uploaded_files:
                try:
                    # Load and clean the data
                    df = analysis.load_and_clean_data(file)
                    if df is not None:
                        # Insert into database (with deduplication)
                        new_count, dup_count = db.insert_records(df)
                        total_new += new_count
                        total_dup += dup_count
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
            
            if total_new > 0:
                st.success(f"✅ Added {total_new} new records!")
            if total_dup > 0:
                st.info(f"ℹ️ Skipped {total_dup} duplicates.")
            
            # Clear the cache to reload data
            st.cache_data.clear()
            st.rerun()

# Export Data
st.sidebar.divider()
st.sidebar.subheader("📥 Export Data")
if 'df_filtered' in locals() or 'filtered_df' in locals():
    # Note: We'll place actual export buttons lower when filtered_df is defined
    pass
else:
    st.sidebar.info("Upload or load data to enable export.")

# Clear data option (with confirmation)
st.sidebar.divider()
st.sidebar.subheader("⚠️ Danger Zone")
if st.sidebar.button("Clear All Data", type="secondary"):
    st.session_state['confirm_clear'] = True

if st.session_state.get('confirm_clear', False):
    st.sidebar.warning("Are you sure? This cannot be undone!")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Yes, Clear"):
        db.clear_all_data()
        st.session_state['confirm_clear'] = False
        st.cache_data.clear()
        st.rerun()
    if col2.button("Cancel"):
        st.session_state['confirm_clear'] = False
        st.rerun()

# --- Load Data from Database ---
@st.cache_data
def load_stored_data():
    """Load all data from the database and prepare for analysis."""
    raw_df = db.get_all_records()
    if raw_df.empty:
        return None
    
    # Apply the same cleaning/preprocessing as before
    raw_df.columns = [c.strip() for c in raw_df.columns]
    
    # Convert 'Created' to datetime
    raw_df['Created_Date'] = pd.to_datetime(raw_df['Created'], format='mixed', dayfirst=True, errors='coerce')
    
    # Extract Week Number (ISO)
    raw_df['Week'] = raw_df['Created_Date'].dt.isocalendar().week
    raw_df['Year'] = raw_df['Created_Date'].dt.isocalendar().year
    raw_df['Year-Week'] = raw_df['Created_Date'].dt.strftime('%Y-W%U')
    
    # Monthly labels
    raw_df['Month'] = raw_df['Created_Date'].dt.strftime('%Y-%m')
    raw_df['Month_Label'] = raw_df['Created_Date'].dt.strftime('%B %Y')
    
    # Process step extraction using config
    raw_df['Summary'] = raw_df['Summary'].fillna('')
    raw_df['Process_Step'] = raw_df['Summary'].apply(config.get_process_step)
    
    return raw_df

df = load_stored_data()

if df is not None and not df.empty:
    # --- Sidebar: Filters ---
    st.sidebar.header("🔍 Filters")
    
    # Date Preset Filter
    preset = st.sidebar.selectbox("Date Quick Presets", ["Custom"] + list(config.DATE_PRESETS.keys()))
    
    min_date = df['Created_Date'].min().date()
    max_date = df['Created_Date'].max().date()
    
    if preset != "Custom":
        days_back = config.DATE_PRESETS[preset]
        start_date = max_date - datetime.timedelta(days=days_back)
        date_range = (start_date, max_date)
        st.sidebar.caption(f"Range: {date_range[0]} to {date_range[1]}")
    else:
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
    # Process Filter
    unique_processes = sorted(df['Process_Step'].unique().astype(str))
    selected_processes = st.sidebar.multiselect("Select Processes", unique_processes, default=unique_processes)
    
    # Assignee Filter
    unique_assignees = sorted(df['Assignee'].unique().astype(str))
    selected_assignees = st.sidebar.multiselect("Select Assignees", unique_assignees, default=unique_assignees)
    
    # Lot Number Search
    search_query = st.sidebar.text_input("Search Lot / Summary", help="Search by lot number or keywords in summary")
    
    # Yield Filter
    st.sidebar.subheader("Filter by Yield %")
    yield_filter = st.sidebar.slider("Minimum Yield Percentage", 0, 100, 0)
    
    # --- Data Filtering ---
    # Helper to calculate yield for a row for filtering
    def row_yield(row):
        start = row['Custom field (Start Quantity)']
        rej = row['Custom field (Rejected Quantity)']
        return ((start - rej) / start * 100) if start > 0 else 0

    mask = (
        (df['Created_Date'].dt.date >= date_range[0]) &
        (df['Created_Date'].dt.date <= date_range[1]) &
        (df['Process_Step'].isin(selected_processes)) &
        (df['Assignee'].isin(selected_assignees))
    )
    
    if search_query:
        mask = mask & (df['Summary'].str.contains(search_query, case=False) | df['Issue key'].str.contains(search_query, case=False))
        
    filtered_df = df.loc[mask]
    
    # Apply yield filter (calculated on the fly for the filtered subset)
    if yield_filter > 0:
        filtered_df['temp_yield'] = filtered_df.apply(row_yield, axis=1)
        filtered_df = filtered_df[filtered_df['temp_yield'] >= yield_filter].drop(columns=['temp_yield'])
    
    # Parse failures for the filtered data
    failures_df = analysis.parse_failure_tables(filtered_df)
    
    # --- KPI Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    total_start = filtered_df['Custom field (Start Quantity)'].sum()
    total_rej = filtered_df['Custom field (Rejected Quantity)'].sum()
    yield_pct = ((total_start - total_rej) / total_start * 100) if total_start > 0 else 0
    total_failures_count = len(failures_df)
    
    # Calculate Yield Status for metric color
    status = config.get_yield_status(yield_pct)
    status_color = "normal" if status == "normal" else "inverse"
    status_label = "✅ Healthy" if status == "normal" else ("⚠️ Warning" if status == "warning" else "🚨 Critical")
    
    col1.metric("Total Sensors", f"{int(total_start)}")
    col2.metric("Total Rejected", f"{int(total_rej)}")
    col3.metric("Yield", f"{yield_pct:.2f}%", help=f"Status: {status_label}")
    col4.metric("Failure Events", f"{total_failures_count}")
    
    if status != "normal":
        st.warning(f"**Process Status: {status_label}** - Yield is below {config.YIELD_WARNING_THRESHOLD}% threshold.")

    # Sidebar Export Buttons (now that data is loaded)
    with st.sidebar:
        st.download_button(
            label="Excel Export (Full)",
            data=export_utils.to_excel(filtered_df, failures_df),
            file_name=export_utils.generate_filename("Full_Analysis", "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.download_button(
            label="CSV Export (Filtered)",
            data=export_utils.to_csv(filtered_df),
            file_name=export_utils.generate_filename("Raw_Data", "csv"),
            mime="text/csv"
        )
    
    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Trends & Performance", "Failure Analysis", "Raw Data"])
    
    with tab1:
        # --- 1. Interactive Time Series ---
        st.subheader("Trends & Yield (Drill-down)")
        st.info("💡 Click on a **Month** bar below to see the weekly breakdown.")

        # Monthly Stats
        monthly_stats = filtered_df.groupby(['Month', 'Month_Label']).agg({
            'Custom field (Start Quantity)': 'sum',
            'Custom field (Rejected Quantity)': 'sum'
        }).reset_index().sort_values('Month')
        
        monthly_stats['Failure Rate %'] = (monthly_stats['Custom field (Rejected Quantity)'] / monthly_stats['Custom field (Start Quantity)'] * 100).fillna(0)
        
        # Monthly Chart
        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
        fig_monthly.add_trace(go.Bar(x=monthly_stats['Month_Label'], y=monthly_stats['Custom field (Start Quantity)'], name='Start Quantity', marker_color='#636EFA'), secondary_y=False)
        fig_monthly.add_trace(go.Scatter(x=monthly_stats['Month_Label'], y=monthly_stats['Failure Rate %'], name='Failure Rate %', line=dict(color='#EF553B', width=3)), secondary_y=True)
        fig_monthly.update_layout(title_text="Monthly Volume and Failure Rate", hovermode="x unified", clickmode='event+select')
        fig_monthly.update_yaxes(title_text="Quantity", secondary_y=False)
        fig_monthly.update_yaxes(title_text="Failure Rate (%)", secondary_y=True)
        
        # Selection Handling
        monthly_selection = st.plotly_chart(fig_monthly, use_container_width=True, on_select="rerun")
        
        selected_month_label = None
        if monthly_selection and monthly_selection.selection and monthly_selection.selection.get('points'):
             idx = monthly_selection.selection['points'][0].get('point_index')
             if idx is not None and idx < len(monthly_stats):
                selected_month_label = monthly_stats.iloc[idx]['Month_Label']
        
        # Drill-down: Weekly View
        if selected_month_label:
            st.markdown(f"### 📅 Weekly Breakdown: {selected_month_label}")
            month_filtered_df = filtered_df[filtered_df['Month_Label'] == selected_month_label]
            
            weekly_stats = month_filtered_df.groupby('Year-Week').agg({
                'Custom field (Start Quantity)': 'sum',
                'Custom field (Rejected Quantity)': 'sum'
            }).reset_index().sort_values('Year-Week')
            weekly_stats['Failure Rate %'] = (weekly_stats['Custom field (Rejected Quantity)'] / weekly_stats['Custom field (Start Quantity)'] * 100).fillna(0)
            
            fig_weekly = make_subplots(specs=[[{"secondary_y": True}]])
            fig_weekly.add_trace(go.Bar(x=weekly_stats['Year-Week'], y=weekly_stats['Custom field (Start Quantity)'], name='Start Quantity', marker_color='#636EFA'), secondary_y=False)
            fig_weekly.add_trace(go.Scatter(x=weekly_stats['Year-Week'], y=weekly_stats['Failure Rate %'], name='Failure Rate %', line=dict(color='#EF553B', width=3)), secondary_y=True)
            fig_weekly.update_layout(height=400, hovermode="x unified")
            fig_weekly.update_yaxes(title_text="Quantity", secondary_y=False)
            fig_weekly.update_yaxes(title_text="Failure Rate (%)", secondary_y=True)
            st.plotly_chart(fig_weekly, use_container_width=True)
        
        st.divider()

        # --- 2. Interactive Process Analysis ---
        st.subheader("Process Yield Analysis (Drill-down)")
        st.info("💡 Click on a **Process Bar** to see the specific failure modes for that step.")
        
        process_stats = filtered_df.groupby('Process_Step').agg({
            'Custom field (Start Quantity)': 'sum',
            'Custom field (Rejected Quantity)': 'sum'
        }).reset_index()
        process_stats['Yield %'] = ((process_stats['Custom field (Start Quantity)'] - process_stats['Custom field (Rejected Quantity)']) / process_stats['Custom field (Start Quantity)'] * 100).fillna(0)
        
        fig_process = px.bar(process_stats, x='Process_Step', y='Yield %', title='Yield by Process Step',
                             color='Yield %', color_continuous_scale='RdYlGn', range_y=[0, 110], text_auto='.1f')
        fig_process.update_layout(clickmode='event+select')
        
        process_selection = st.plotly_chart(fig_process, use_container_width=True, on_select="rerun")
        
        selected_process = None
        if process_selection and process_selection.selection and process_selection.selection.get('points'):
             selected_process = process_selection.selection['points'][0].get('x')
        
        if selected_process:
            st.markdown(f"### 🔍 Failure Modes: {selected_process}")
            
            # Filter failures for this process
            process_failures = failures_df[failures_df['Process_Step'] == selected_process]
            
            if not process_failures.empty:
                clean_failures = process_failures[~process_failures['Failure Mode'].apply(config.is_failure_mode_excluded)]
                
                fail_counts = clean_failures['Failure Mode'].value_counts().reset_index()
                fail_counts.columns = ['Failure Mode', 'Count']
                
                fig_pie = px.pie(fail_counts.head(10), values='Count', names='Failure Mode', 
                                 title=f"Top Failure Modes in {selected_process}", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                 st.info(f"No detailed failure data found for {selected_process}.")

    with tab2:
        st.subheader("📈 Performance Trends")
        
        # 1. Yield Trend with Moving Average
        daily_stats = filtered_df.groupby(filtered_df['Created_Date'].dt.date).agg({
            'Custom field (Start Quantity)': 'sum',
            'Custom field (Rejected Quantity)': 'sum'
        }).reset_index()
        daily_stats.columns = ['Date', 'Start', 'Rejected']
        daily_stats['Yield %'] = ((daily_stats['Start'] - daily_stats['Rejected']) / daily_stats['Start'] * 100).fillna(0)
        
        # Calculate Moving Average (7-day)
        daily_stats['Yield MA (7d)'] = daily_stats['Yield %'].rolling(window=7, min_periods=1).mean()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=daily_stats['Date'], y=daily_stats['Yield %'], mode='markers', name='Daily Yield', marker=dict(color='rgba(100, 100, 100, 0.3)')))
        fig_trend.add_trace(go.Scatter(x=daily_stats['Date'], y=daily_stats['Yield MA (7d)'], mode='lines', name='7-Day Moving Avg', line=dict(color=config.PRIMARY_COLOR, width=3)))
        
        # Add threshold line
        fig_trend.add_hline(y=config.YIELD_WARNING_THRESHOLD, line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
        
        fig_trend.update_layout(title="Yield Trend over Time", yaxis_title="Yield %", xaxis_title="Date", height=config.CHART_HEIGHT)
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.divider()
        
        # 2. Assignee Performance
        st.subheader("👤 Assignee Throughput & Quality")
        col_c1, col_c2 = st.columns(2)
        
        assignee_metrics = filtered_df.groupby('Assignee').agg({
            'Issue key': 'count',
            'Custom field (Start Quantity)': 'sum',
            'Custom field (Rejected Quantity)': 'sum'
        }).reset_index()
        assignee_metrics.columns = ['Assignee', 'Gates Completed', 'Total Sensors', 'Total Rejected']
        assignee_metrics['Yield %'] = ((assignee_metrics['Total Sensors'] - assignee_metrics['Total Rejected']) / assignee_metrics['Total Sensors'] * 100).fillna(0)
        
        with col_c1:
            fig_vol = px.bar(assignee_metrics.sort_values('Gates Completed', ascending=False).head(config.TOP_N_ASSIGNEES), 
                             x='Assignee', y='Gates Completed', title='Gates Completed by Assignee',
                             color='Gates Completed', color_continuous_scale='Blues')
            st.plotly_chart(fig_vol, use_container_width=True)
            
        with col_c2:
            fig_qual = px.bar(assignee_metrics.sort_values('Yield %', ascending=False).head(config.TOP_N_ASSIGNEES), 
                              x='Assignee', y='Yield %', title='Avg Yield % by Assignee',
                              color='Yield %', color_continuous_scale='RdYlGn', range_y=[0, 110])
            st.plotly_chart(fig_qual, use_container_width=True)

    with tab3:
        st.subheader("Failure Modes Analysis")
        
        if not failures_df.empty:
            col_a, col_b = st.columns([2, 1])
            
            # Top Failures Chart
            fail_counts = failures_df['Failure Mode'].value_counts().reset_index()
            fail_counts.columns = ['Failure Mode', 'Count']
            fail_counts = fail_counts[~fail_counts['Failure Mode'].apply(config.is_failure_mode_excluded)]
            
            with col_a:
                 fig_pareto = px.bar(fail_counts.head(20), x='Count', y='Failure Mode', orientation='h', 
                                 title='Top 20 Failure Modes', color='Count', color_continuous_scale='Reds')
                 fig_pareto.update_layout(yaxis={'categoryorder':'total ascending'})
                 st.plotly_chart(fig_pareto, use_container_width=True)
            
            # Automated Insights
            with col_b:
                st.markdown("### 🤖 Automated Insights")
                
                total_fails = fail_counts['Count'].sum()
                top_3 = fail_counts.head(3)
                
                st.markdown("#### Dominant Drivers")
                for idx, row in top_3.iterrows():
                    pct = (row['Count'] / total_fails * 100) if total_fails > 0 else 0
                    st.write(f"**{idx+1}. {row['Failure Mode']}**: {row['Count']} events ({pct:.1f}%)")
                
                top_3_pct = (top_3['Count'].sum() / total_fails * 100) if total_fails > 0 else 0
                st.info(f"⚠️ The top 3 issues account for **{top_3_pct:.1f}%** of all rejections.")
                
                # Recent Spikes Calculation
                if 'Year-Week' in failures_df.columns and not failures_df.empty:
                    weeks = sorted(failures_df['Year-Week'].unique())
                    if len(weeks) >= 2:
                        last_week = weeks[-1]
                        last_week_data = failures_df[failures_df['Year-Week'] == last_week]
                        last_week_counts = last_week_data['Failure Mode'].value_counts()
                        
                        st.markdown("#### Recent Spikes (Last Week)")
                        found_spike = False
                        for mode in top_3['Failure Mode']:
                            if mode in last_week_counts:
                                count = last_week_counts[mode]
                                st.write(f"- **{mode}**: {count} occurrences in {last_week}")
                                found_spike = True
                        if not found_spike:
                            st.write("No major spikes in top issues this week.")
                            
        else:
            st.info("No detailed failure data found in the current selection.")

    with tab4:
        st.subheader("Raw Data View")
        st.dataframe(filtered_df, use_container_width=True)
        
        st.subheader("Extracted Failures")
        st.dataframe(failures_df, use_container_width=True)

else:
    # No data state
    st.info("📭 No data stored yet. Upload your first CSV file from the sidebar to get started!")
    
    st.markdown("""
    ### Getting Started
    1. **Upload your historical data** from the sidebar (you only need to do this once!)
    2. **Upload new data** as you complete more QA gates - duplicates are automatically skipped.
    3. Your data is **stored permanently** and will persist between sessions.
    
    ### CSV Requirements
    - Files should be CSV exports from Jira.
    - Expected columns: `Issue key`, `Summary`, `Created`, `Custom field (Start Quantity)`, `Custom field (Rejected Quantity)`, `Custom field (Conclusion)`.
    """)
