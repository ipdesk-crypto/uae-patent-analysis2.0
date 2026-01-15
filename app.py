import streamlit as st
import pandas as pd
import plotly.express as px
import hmac
from PIL import Image

# --- SECURITY ---
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True
    st.markdown("<h1 style='text-align: center; color: #FF6600;'>🏛️ ARCHISTRATEGOS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.text_input("Access Key:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Invalid Key.")
    return False

if not check_password():
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="UAE Patent Analysis 2.0", layout="wide", page_icon="🏛️")

# Custom Styling
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE (EXPLODING CLASSIFICATIONS) ---
@st.cache_data
def load_and_refine_data():
    raw_df = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - All available types.csv")
    raw_df.columns = raw_df.columns.str.strip()
    
    # 1. Clean Dates
    raw_df['Application Date'] = pd.to_datetime(raw_df['Application Date'], errors='coerce')
    raw_df = raw_df.dropna(subset=['Application Date'])
    raw_df['Year'] = raw_df['Application Date'].dt.year.astype(int)
    raw_df['Month_Start'] = raw_df['Application Date'].dt.to_period('M').dt.to_timestamp()
    
    # 2. Explode Classifications (Treatment of multiple IPCs as separate entities)
    # Split by comma and explode into separate rows
    raw_df['Classification'] = raw_df['Classification'].astype(str).str.split(',')
    df = raw_df.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Filter out rows with no valid classification
    df = df[~df['Classification'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification'] != 'nan']
    
    # Extract Section (A-H)
    df['IPC_Section'] = df['Classification'].str[:1].str.upper()
    
    return df

df = load_and_refine_data()

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Go to:", ["Classification Overview", "Growth Analysis (12-Month MA)"])

# --- MODULE 1: CLASSIFICATION OVERVIEW ---
if menu == "Classification Overview":
    st.header("📊 Classification Distribution (Individual IPC Counts)")
    st.write("Each classification code in a row is counted as a separate instance.")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    # Section Distribution
    section_counts = sect_df.groupby('IPC_Section').size().reset_index(name='Total Occurrences')
    fig_sect = px.bar(section_counts, x='IPC_Section', y='Total Occurrences', text='Total Occurrences',
                      title="Total Occurrences per IPC Section",
                      color_discrete_sequence=['#FF6600'])
    fig_sect.update_traces(textposition='outside')
    st.plotly_chart(fig_sect, use_container_width=True)

    # Yearly Growth of Sections
    st.markdown("---")
    st.subheader("Yearly IPC Section Trends")
    yearly_sect = sect_df.groupby(['Year', 'IPC_Section']).size().reset_index(name='Occurrences')
    fig_line = px.line(yearly_sect, x='Year', y='Occurrences', color='IPC_Section', markers=True,
                       title="Growth of IPC Sections Over Time")
    st.plotly_chart(fig_line, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MOVING AVERAGE) ---
elif menu == "Growth Analysis (12-Month MA)":
    st.header("📈 Growth Analysis: 12-Month Moving Average")
    st.info("Note: If a patent contains multiple codes, it is counted once for each code it possesses.")

    # Unique IPC List for Dropdown
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select IPC Code to Zoom (or analyze total volume):", ["Total (All IPC Occurrences)"] + all_codes)

    # Filtering
    if target_ipc == "Total (All IPC Occurrences)":
        analysis_df = df.copy()
    else:
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.warning("No data found for the selection.")
    else:
        # Group by Month and Application Type
        grouped = analysis_df.groupby(['Month_Start', 'Application Type (ID)']).size().reset_index(name='Count')
        
        # Pivot for Moving Average
        pivot_df = grouped.pivot(index='Month_Start', columns='Application Type (ID)', values='Count').fillna(0)
        
        # Ensure a continuous timeline (no gaps in months)
        full_idx = pd.date_range(start=pivot_df.index.min(), end=pivot_df.index.max(), freq='MS')
        pivot_df = pivot_df.reindex(full_idx, fill_value=0)
        
        # Calculate 12-Month Moving Average
        ma_result = pivot_df.rolling(window=12).mean().reset_index()
        ma_result = ma_result.rename(columns={'index': 'Month'})
        
        # Melt for visualization
        melted = ma_result.melt(id_vars='Month', var_name='App Type ID', value_name='12-Month MA')
        
        # Remove NaN values from the beginning of the rolling window
        melted = melted.dropna()

        # Plot
        fig_ma = px.line(melted, x='Month', y='12-Month MA', color='App Type ID',
                         title=f"12-Month Moving Average Trend: {target_ipc}",
                         labels={'12-Month MA': '12-Month MA', 'Month': 'Timeline (Yearly)'},
                         template='plotly_white')
        
        fig_ma.update_layout(
            hovermode='x unified',
            yaxis_title="12-Month MA",
            xaxis_title="Year"
        )
        st.plotly_chart(fig_ma, use_container_width=True)
        
        st.write(f"This graph shows the smoothed growth of **{target_ipc}** across Application Types 1-5.")
