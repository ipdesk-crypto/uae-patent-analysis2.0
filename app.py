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
def load_data():
    df_raw = pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - All available types.csv")
    df_raw.columns = df_raw.columns.str.strip()
    
    # Timeline: Extract Year-Month for accurate MA calculation
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date'])
    
    # Store the Monthly format YYYY-MM for the precision of the calculation
    df_raw['YYYY_MM'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    
    # EXPLODE LOGIC: Count each IPC as an individual instance
    df_raw['Classification'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Remove rows with no specific data
    df = df[~df['Classification'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification'] != 'nan']
    
    # Section Extraction for the Overview
    df['IPC_Section'] = df['Classification'].str[:1].str.upper()
    df['Year_Int'] = df['Earliest Priority Date'].dt.year.astype(int)
    
    return df

df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    menu = st.radio("Navigation", ["Classification & Growth", "Growth Analysis (MA Zoom)"])

# --- MODULE 1: CLASSIFICATION & GROWTH ---
if menu == "Classification & Growth":
    st.header("📊 Classification Distribution & Section Growth")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    # 1. Volume Bar Chart
    counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_hist = px.bar(counts, x='IPC_Section', y='Apps', text='Apps', 
                      title="Total Counts by IPC Section",
                      color_discrete_sequence=['#FF6600'], 
                      labels={'Apps': 'Number of Applications'})
    fig_hist.update_traces(textposition='outside')
    st.plotly_chart(fig_hist, use_container_width=True)

    # 2. Yearly Growth of Sections
    st.markdown("---")
    st.subheader("Section Growth (Yearly Volume)")
    yearly_growth = sect_df.groupby(['Year_Int', 'IPC_Section']).size().reset_index(name='Apps')
    fig_line = px.line(yearly_growth, x='Year_Int', y='Apps', color='IPC_Section', markers=True,
                       labels={'Apps': 'Number of Applications', 'Year_Int': 'Year'})
    st.plotly_chart(fig_line, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MA ZOOM) ---
elif menu == "Growth Analysis (MA Zoom)":
    st.header("📈 Yearly Growth Analysis (12-Month Moving Average)")
    st.info("The Y-axis reflects the Number of Applications. The timeline shows Yearly increments based on a monthly calculated Moving Average.")

    # IPC Zoom Selection
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select Individual IPC Code to Zoom:", ["Total (All Classifications)"] + all_codes)

    # Accurate Filter
    if target_ipc == "Total (All Classifications)":
        analysis_df = df.copy()
    else:
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.error("No data found for the selected IPC.")
    else:
        # Group by the precision month (YYYY-MM) and Application Type
        grouped = analysis_df.groupby(['YYYY_MM', 'Application Type (ID)']).size().reset_index(name='Counts')
        
        # Pivot so App Types are distinct lines
        pivot_df = grouped.pivot(index='YYYY_MM', columns='Application Type (ID)', values='Counts').fillna(0)
        
        # Continuous Monthly Timeline to ensure calculation accuracy (filling 0 for missing months)
        full_range = pd.date_range(start=df['YYYY_MM'].min(), end=df['YYYY_MM'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # Calculate the 12-Month Moving Average (The "Yearly" average at any month)
        ma_df = pivot_df.rolling(window=12).mean().reset_index().rename(columns={'index': 'Timeline'})
        
        # Melt for Plotting
        melted = ma_df.melt(id_vars='Timeline', var_name='Type ID', value_name='MA_Value').dropna()

        # Create Graph
        fig_ma = px.line(melted, x='Timeline', y='MA_Value', color='Type ID',
                         title=f"Growth Trend (12-Month MA): {target_ipc}",
                         labels={'MA_Value': 'Number of Applications', 'Timeline': 'Year'},
                         template='plotly_white')

        # CLEAN X-AXIS: Just Years, no months, ticks every 12 months
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y", 
            showgrid=True,
            gridcolor='lightgrey',
            title="Year"
        )
        
        # Y-AXIS LABEL
        fig_ma.update_yaxes(
            title="Number of Applications",
            showgrid=True
        )
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)
        
        st.markdown(f"**Selected:** {target_ipc}. Each data point represents the 12-month smoothed volume of applications.")
