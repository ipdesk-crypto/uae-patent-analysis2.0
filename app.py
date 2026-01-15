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

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002147; color: white; }
    h1, h2, h3 { color: #002147; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def load_and_refine_data():
    # Load data
    df_raw = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - All available types.csv")
    df_raw.columns = df_raw.columns.str.strip()
    
    # Use Earliest Priority Date as the primary timeline
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date'])
    
    # Format dates to YYYY-MM for the analysis
    df_raw['YYYY_MM'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    
    # Explode Classifications so each IPC code is treated as a unique record
    df_raw['Classification'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Filter out empty or placeholder classifications
    df = df[~df['Classification'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification'] != 'nan']
    
    # Extract IPC Section (First letter)
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
    menu = st.radio("Navigation", ["Classification Overview", "Growth Analysis (12-Month MA)"])

# --- MODULE 1: CLASSIFICATION OVERVIEW ---
if menu == "Classification Overview":
    st.header("📊 Classification Distribution (Individual IPC Counts)")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    section_counts = sect_df.groupby('IPC_Section').size().reset_index(name='Total Counts')
    fig_sect = px.bar(section_counts, x='IPC_Section', y='Total Counts', text='Total Counts',
                      color_discrete_sequence=['#FF6600'], title="Volume per IPC Section")
    st.plotly_chart(fig_sect, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (12-MONTH MA) ---
elif menu == "Growth Analysis (12-Month MA)":
    st.header("📈 Growth Analysis: 12-Month Moving Average")
    st.info("Analysis based on Earliest Priority Date. Individual IPC codes are isolated for precision.")

    # Unique IPC List
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select IPC Code to Zoom:", ["Total (All Classifications)"] + all_codes)

    # Filtering logic
    if target_ipc == "Total (All Classifications)":
        analysis_df = df.copy()
    else:
        # STRICT FILTERING for the selected IPC
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.error("No data available for the selected IPC.")
    else:
        # Group by Month and App Type
        grouped = analysis_df.groupby(['YYYY_MM', 'Application Type (ID)']).size().reset_index(name='Count')
        
        # Pivot to align types
        pivot_df = grouped.pivot(index='YYYY_MM', columns='Application Type (ID)', values='Count').fillna(0)
        
        # Consistent X-Axis: Create a continuous range of months for all years available
        full_range = pd.date_range(start=df['YYYY_MM'].min(), end=df['YYYY_MM'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # 12-Month Moving Average
        ma_df = pivot_df.rolling(window=12).mean().reset_index().rename(columns={'index': 'Month'})
        
        # Melt for plotting
        melted = ma_df.melt(id_vars='Month', var_name='App Type', value_name='12-Month MA')
        melted = melted.dropna() # Remove initial NaN months

        # Plotting
        fig_ma = px.line(melted, x='Month', y='12-Month MA', color='App Type',
                         title=f"12-Month MA Growth for: {target_ipc}",
                         labels={'12-Month MA': '12-Month MA (Volume)', 'Month': 'Year (YYYY-MM)'},
                         template='plotly_white')

        # FORCE X-AXIS CONSISTENCY: Tick every 12 months (Every Year)
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y-%m",
            ticklabelmode="period",
            showgrid=True
        )
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)

        st.subheader("Data Summary for this selection")
        st.write(f"This graph represents the smoothed growth trend for **{target_ipc}**.")
