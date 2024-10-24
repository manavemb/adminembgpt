import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
from streamlit import cache_data

# Page config
st.set_page_config(
    page_title="EMB-AI BRD Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #ffffff;
    }
    
    .stMetric {
        background-color: #f4f4f5;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    
    .st-emotion-cache-1r6slb0 {
        background-color: #f4f4f5;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    
    .stat-card {
        background-color: #f4f4f5;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: left;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #18181b;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #71717a;
    }
    
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #18181b;
        margin-bottom: 1rem;
    }
    
    /* Custom button style */
    .stButton > button {
        background-color: #f4f4f5;
        color: #18181b;
        border: 1px solid #e4e4e7;
        border-radius: 0.375rem;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    
    .stButton > button:hover {
        background-color: #e4e4e7;
    }
    
    /* Custom selectbox style */
    .stSelectbox > div > div {
        background-color: #f4f4f5;
        border: 1px solid #e4e4e7;
        border-radius: 0.375rem;
    }
    
    /* Custom text input style */
    .stTextInput > div > div > input {
        background-color: #f4f4f5;
        border: 1px solid #e4e4e7;
        border-radius: 0.375rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 EMB-AI BRD Dashboard")

# Setup Google Sheets connection
@st.cache_resource()
def setup_google_sheets():
    """Initialize Google Sheets connection"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = {
        "type": "service_account",
        "project_id": st.secrets["GOOGLE_SHEETS"]["project_id"],
        "private_key_id": st.secrets["GOOGLE_SHEETS"]["private_key_id"],
        "private_key": st.secrets["GOOGLE_SHEETS"]["private_key"],
        "client_email": st.secrets["GOOGLE_SHEETS"]["client_email"],
        "client_id": st.secrets["GOOGLE_SHEETS"]["client_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": st.secrets["GOOGLE_SHEETS"]["client_x509_cert_url"]
    }
    
    creds = Credentials.from_service_account_info(credentials, scopes=scope)
    client = gspread.authorize(creds)
    return client

# Function to load BRD data
@st.cache_data(ttl=3600)
def load_brd_data():
    try:
        client = setup_google_sheets()
        
        # Load form data
        form_sheet = client.open("EMBGPT").worksheet("Sheet1")
        form_data = form_sheet.get_all_records()
        form_df = pd.DataFrame(form_data)
        
        # Load content data
        content_sheet = client.open("EMBGPT").worksheet("BRD_Content")
        content_data = content_sheet.get_all_records()
        content_df = pd.DataFrame(content_data)
        
        return form_df, content_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

# Load data
form_df, content_df = load_brd_data()
if form_df is not None and content_df is not None:
    # Sidebar Filters
    st.sidebar.header("🔍 Filters")
    client_filter = st.sidebar.multiselect(
        "Filter by Client",
        options=['All'] + sorted(form_df['Client_Name'].unique().tolist()),
        default=['All']
    )
    
    date_range = st.sidebar.date_input(
        "Filter by Date Range",
        value=(
            pd.to_datetime(form_df['Timestamp']).min().date(),
            pd.to_datetime(form_df['Timestamp']).max().date()
        )
    )

    # Apply filters
    filtered_df = form_df.copy()
    if 'All' not in client_filter:
        filtered_df = filtered_df[filtered_df['Client_Name'].isin(client_filter)]
    
    filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'])
    filtered_df = filtered_df[
        (filtered_df['Timestamp'].dt.date >= date_range[0]) &
        (filtered_df['Timestamp'].dt.date <= date_range[1])
    ]

    # Tabs for navigation
    tab1, tab2 = st.tabs(["📈 Dashboard Overview", "📋 BRD List"])
    
    # Tab 1: Dashboard Overview
    with tab1:
        st.header("Dashboard Metrics")

        def create_metric_card(label, value, icon):
            return f"""
            <div class="stat-card">
                <div class="stat-label">{label}</div>
                <div class="stat-value">{icon} {value}</div>
            </div>
            """

        col1, col2, col3, col4 = st.columns(4)
        
        total_brds = len(filtered_df)
        total_clients = filtered_df['Client_Name'].nunique()
        total_downloads = (
            filtered_df['Download_Count_MD'].sum() +
            filtered_df['Download_Count_PDF'].sum() +
            filtered_df['Download_Count_DOCX'].sum()
        )
        avg_downloads = round(total_downloads / total_brds, 2) if total_brds > 0 else 0
        
        with col1:
            st.markdown(create_metric_card("Total BRDs Generated", total_brds, "📄"), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card("Unique Clients", total_clients, "👥"), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card("Total Downloads", total_downloads, "⬇️"), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_metric_card("Avg Downloads per BRD", avg_downloads, "📊"), unsafe_allow_html=True)

        # Trend Chart
        st.header("BRD Generation Trend")
        trend_data = filtered_df.groupby(filtered_df['Timestamp'].dt.date).size().reset_index(name='Count')
        fig_trend = px.line(trend_data, x='Timestamp', y='Count', title='BRDs Generated Over Time')
        fig_trend.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of BRDs",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
            ),
            xaxis=dict(
                showgrid=False,
            ),
            font=dict(
                family="Inter, sans-serif",
            )
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Download statistics
        st.header("Download Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Downloads by Type")
            download_stats = {
                'Markdown': filtered_df['Download_Count_MD'].sum(),
                'PDF': filtered_df['Download_Count_PDF'].sum(),
                'DOCX': filtered_df['Download_Count_DOCX'].sum()
            }
            fig = px.pie(
                names=list(download_stats.keys()),
                values=list(download_stats.values()),
                title="Downloads by Type",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(
                    family="Inter, sans-serif",
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Top Clients by Downloads")
            top_clients = filtered_df.groupby('Client_Name').agg({
                'Download_Count_MD': 'sum',
                'Download_Count_PDF': 'sum',
                'Download_Count_DOCX': 'sum'
            })
            top_clients['Total_Downloads'] = (
                top_clients['Download_Count_MD'] +
                top_clients['Download_Count_PDF'] +
                top_clients['Download_Count_DOCX']
            )
            top_clients = top_clients.sort_values(by='Total_Downloads', ascending=False).head(5)
            fig = px.bar(
                top_clients,
                x=top_clients.index,
                y='Total_Downloads',
                title="Top Clients by Downloads",
                labels={'x': 'Client Name', 'Total_Downloads': 'Total Downloads'},
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.1)',
                ),
                xaxis=dict(
                    showgrid=False,
                ),
                font=dict(
                    family="Inter, sans-serif",
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            # Tab 2: BRD List
    with tab2:
        st.header("BRD List")
        
        # Format the dataframe for display
        display_df = filtered_df[[
            'Timestamp', 'Client_Name', 'Version_Number', 'Prepared_By',
            'Download_Count_MD', 'Download_Count_PDF', 'Download_Count_DOCX'
        ]].copy()
        
        display_df['Total_Downloads'] = (
            display_df['Download_Count_MD'] +
            display_df['Download_Count_PDF'] +
            display_df['Download_Count_DOCX']
        )
        
        display_df = display_df.rename(columns={
            'Client_Name': 'Client',
            'Version_Number': 'Version',
            'Prepared_By': 'Generated By',
            'Download_Count_MD': 'MD Downloads',
            'Download_Count_PDF': 'PDF Downloads',
            'Download_Count_DOCX': 'DOCX Downloads',
            'Total_Downloads': 'Total Downloads'
        })

        # Search functionality
        search_term = st.text_input("🔍 Search BRDs", "")
        if search_term:
            display_df = display_df[display_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        
        if not display_df.empty:
            st.dataframe(
                display_df.style.format({
                    'Timestamp': lambda x: x.strftime('%Y-%m-%d %H:%M:%S')
                }),
                use_container_width=True
            )
            
            # Download CSV
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download BRD data as CSV",
                data=csv,
                file_name="brd_data.csv",
                mime="text/csv",
            )
            
            # Select a BRD to view its content
            st.subheader("BRD Content Viewer")
            selected_index = st.selectbox("Select a BRD to View Content", options=display_df.index, format_func=lambda x: f"{display_df.loc[x, 'Client']} - Version {display_df.loc[x, 'Version']}")
            
            if selected_index is not None:
                selected_row = display_df.loc[selected_index]
                brd_content = content_df[
                    (content_df['Client_Name'] == selected_row['Client']) &
                    (content_df['Version'] == selected_row['Version'])
                ]
                
                if not brd_content.empty:
                    view_option = st.radio("View Options", ("View Full Content", "View Part by Part"))
                    
                    if view_option == "View Full Content":
                        st.markdown(
                            f" {brd_content.iloc[0]['Part_1_Content']}\n\n"
                            f" {brd_content.iloc[0]['Part_2_Content']}\n\n"
                            f" {brd_content.iloc[0]['Part_3_Content']}\n\n"
                            f" {brd_content.iloc[0]['Part_4_Content']}"
                        )
                    else:
                        tabs = st.tabs(["Part 1", "Part 2", "Part 3", "Part 4"])
                        
                        for i, tab in enumerate(tabs):
                            with tab:
                                st.markdown(f"**Part {i+1}**: {brd_content.iloc[0][f'Part_{i+1}_Content']}")
                else:
                    st.warning("⚠️ Content not found for this BRD")
        else:
            st.info("ℹ️ No BRDs found matching the selected filters")

else:
    st.error("⚠️ Unable to load data. Please check your Google Sheets connection.")

# Additional features
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Additional Options")

# Refresh data button
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# About section
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ About")
st.sidebar.info(
    "This dashboard provides an overview of EMB-AI BRD (Business Requirements Document) "
    "generation and usage statistics. It allows you to filter and analyze BRD data, "
    "view trends, and access individual BRD contents."
)

# Version info
st.sidebar.markdown("---")
st.sidebar.markdown("🔖 Version 1.0.0")

# Optional: Add a data last updated timestamp
last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.sidebar.markdown(f"🕒 Data last updated: {last_updated}")

# Optional: Add a help section
if st.sidebar.checkbox("❓ Show Help"):
    st.sidebar.markdown("""
    ### How to use this dashboard:
    1. Use the filters in the sidebar to select specific clients and date ranges.
    2. The 'Dashboard Overview' tab shows key metrics and trends.
    3. The 'BRD List' tab allows you to view and search individual BRDs.
    4. You can download the filtered BRD data as a CSV file.
    5. Use the refresh button to update the data.
    """)

# Optional: Add a legend or key metrics explanation
if st.sidebar.checkbox("🔑 Show Metrics Explanation"):
    st.sidebar.markdown("""
    ### Key Metrics Explained:
    - **Total BRDs Generated**: The number of BRDs created in the selected period.
    - **Unique Clients**: The number of distinct clients for whom BRDs were generated.
    - **Total Downloads**: The sum of all downloads across all file types.
    - **Avg Downloads per BRD**: The average number of times each BRD was downloaded.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center;'>
    <p>© 2024 EMB-AI. All rights reserved.</p>
    <p style='font-size: 0.8em;'>🏢 Plot No. 17, Phase-4, Maruti Udyog, Sector 18, Gurugram, HR</p>
    <p style='font-size: 0.8em;'>📞 +91-8882102246 | 📧 contact@exmyb.com | 🌐 www.emb.global</p>
</div>
""", unsafe_allow_html=True)
