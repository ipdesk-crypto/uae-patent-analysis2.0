import streamlit as st
import pandas as pd
import plotly.express as px
import hmac
from PIL import Image

# --- ARCHISTRATEGOS SECURITY ---
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
    
    # 1. Timeline Setup (Earliest Priority Date)
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date'])
    df_raw['Month_TS'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Int'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # 2. Explode IPCs (Every code counted separately)
    df_raw['Classification'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Clean up empty rows
    df = df[~df['Classification'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification'] != 'nan']
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
    st.header("📊 Individual IPC Distribution & Trends")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    # Histogram
    counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_hist = px.bar(counts, x='IPC_Section', y='Apps', text='Apps', 
                      title="Total Counts by IPC Section",
                      color_discrete_sequence=['#FF6600'], 
                      labels={'Apps': 'Number of Applications'})
    fig_hist.update_traces(textposition='outside')
    fig_hist.update_xaxes(showgrid=False) # No vertical lines
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    
    # Yearly Growth
    st.subheader("Section Growth (Total Annual Volume)")
    yearly_growth = sect_df.groupby(['Year_Int', 'IPC_Section']).size().reset_index(name='Apps')
    fig_line = px.line(yearly_growth, x='Year_Int', y='Apps', color='IPC_Section', markers=True,
                       labels={'Apps': 'Number of Applications', 'Year_Int': 'Year'})
    fig_line.update_xaxes(showgrid=False) # No vertical lines
    st.plotly_chart(fig_line, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MA ZOOM) ---
elif menu == "Growth Analysis (MA Zoom)":
    st.header("📈 Growth Analysis: 12-Month Rolling Total")
    st.info("The Y-axis shows the total number of applications filed in the 12 months preceding that point. This provides a smoothed, integer-based growth trend.")

    # IPC Zoom Dropdown
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select Individual IPC Code to Zoom:", ["Total (All Classifications)"] + all_codes)

    # Filter
    if target_ipc == "Total (All Classifications)":
        analysis_df = df.copy()
    else:
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.error("No data found for this selection.")
    else:
        # Group by precision month
        grouped = analysis_df.groupby(['Month_TS', 'Application Type (ID)']).size().reset_index(name='Monthly_Count')
        pivot_df = grouped.pivot(index='Month_TS', columns='Application Type (ID)', values='Monthly_Count').fillna(0)
        
        # Fill Timeline Gaps
        full_range = pd.date_range(start=df['Month_TS'].min(), end=df['Month_TS'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # CALCULATE ROLLING TOTAL (Smoothes like an MA but uses Whole Numbers)
        # This replaces the .mean() calculation to avoid 0.25 values
        ma_df = pivot_df.rolling(window=12).sum().reset_index().rename(columns={'index': 'Timeline'})
        
        # Melt and Clean
        melted = ma_df.melt(id_vars='Timeline', var_name='App Type', value_name='Total_Apps')
        melted = melted.dropna()

        # DYNAMIC START: Don't show empty years before the technology existed
        active_data = melted[melted['Total_Apps'] > 0]
        if not active_data.empty:
            start_visible = active_data['Timeline'].min() - pd.DateOffset(years=1)
            melted = melted[melted['Timeline'] >= start_visible]

        # Create Plot
        fig_ma = px.line(melted, x='Timeline', y='Total_Apps', color='App Type',
                         title=f"12-Month Growth Volume: {target_ipc}",
                         labels={'Total_Apps': 'Number of Applications', 'Timeline': 'Year'},
                         template='plotly_white')

        # FINAL AXIS CUSTOMIZATION
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y", 
            showgrid=False, # No vertical lines
            title="Year"
        )
        
        fig_ma.update_yaxes(
            title="Number of Applications (Rolling 12-Month Total)",
            showgrid=True,
            gridcolor='whitesmoke' # Faint horizontal lines only
        )
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)
