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
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Timeline: Use Earliest Priority Date
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date'])
    
    # Standardize Month Column for Time Series
    df_raw['Month_TS'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Only'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # EXPLODE LOGIC: Count each IPC individually as requested
    df_raw['Classification'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Filter valid entries
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
    menu = st.radio("Navigation", ["Classification & Growth", "Growth Analysis (MA Zoom)"])

# --- MODULE 1: CLASSIFICATION & GROWTH ---
if menu == "Classification & Growth":
    st.header("🌍 Classification Strength & Yearly Growth")
    st.write("Each classification within a single application is counted individually.")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    # Histogram
    section_counts = sect_df.groupby('IPC_Section').size().reset_index(name='Count')
    fig_hist = px.bar(section_counts, x='IPC_Section', y='Count', text='Count',
                      title="Total Counts per IPC Section (A-H)",
                      color_discrete_sequence=['#f39c12'], labels={'Count': 'Number of Applications'})
    fig_hist.update_traces(textposition='outside')
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    
    # Temporal Line Chart
    st.subheader("Section Growth over Time")
    yearly_sect = sect_df.groupby(['Year_Only', 'IPC_Section']).size().reset_index(name='Count')
    fig_growth = px.line(yearly_sect, x='Year_Only', y='Count', color='IPC_Section', markers=True,
                         labels={'Count': 'Number of Applications', 'Year_Only': 'Year'})
    st.plotly_chart(fig_growth, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MA ZOOM) ---
elif menu == "Growth Analysis (MA Zoom)":
    st.header("📈 Growth Analysis: 12-Month Moving Average")
    st.info("The Y-axis shows the Number of Applications smoothed over a 12-month period based on Earliest Priority Date.")

    # Unique IPC Dropdown
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select Individual IPC Code to Zoom:", ["Total (All Classifications)"] + all_codes)

    # Filtering
    if target_ipc == "Total (All Classifications)":
        analysis_df = df.copy()
    else:
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.error("No data found for this selection.")
    else:
        # Grouping by Month and Type
        grouped = analysis_df.groupby(['Month_TS', 'Application Type (ID)']).size().reset_index(name='Monthly_Total')
        
        # Pivot to ensure we have columns for types 1-5
        pivot_df = grouped.pivot(index='Month_TS', columns='Application Type (ID)', values='Monthly_Total').fillna(0)
        
        # CONTINUOUS TIMELINE: Create a date range for all months in the dataset
        full_range = pd.date_range(start=df['Month_TS'].min(), end=df['Month_TS'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # CALCULATE 12-MONTH MOVING AVERAGE
        ma_df = pivot_df.rolling(window=12).mean().reset_index().rename(columns={'index': 'Month'})
        
        # Prepare for Plotly
        melted = ma_df.melt(id_vars='Month', var_name='App Type', value_name='MA_Value')
        melted = melted.dropna() # Remove initial window buffer

        # Create Plot
        fig_ma = px.line(melted, x='Month', y='MA_Value', color='App Type',
                         title=f"12-Month Moving Average: {target_ipc}",
                         labels={'MA_Value': 'Number of Applications', 'Month': 'Year (YYYY-MM)'},
                         template='plotly_white')

        # CONSISTENT X-AXIS: Ticks every 12 months, formatted YYYY-MM
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y-%m",
            showgrid=True,
            title="Year (YYYY-MM)"
        )
        
        # CONSISTENT Y-AXIS LABEL
        fig_ma.update_yaxes(title="Number of Applications", showgrid=True)
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)
        
        st.write(f"Showing accurate application growth for **{target_ipc}** across Application Types.")
