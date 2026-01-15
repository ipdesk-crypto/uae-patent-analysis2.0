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

# --- DATA PROCESSING ---
@st.cache_data
def load_and_refine_data():
    file_path = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df_raw = pd.read_csv(file_path)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Timeline: Earliest Priority Date
    df_raw['Earliest Priority Date'] = pd.to_datetime(df_raw['Earliest Priority Date'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Earliest Priority Date'])
    
    # Store Monthly format for Accurate Moving Average math
    df_raw['Month_TS'] = df_raw['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    df_raw['Year_Int'] = df_raw['Earliest Priority Date'].dt.year.astype(int)
    
    # EXPLODE LOGIC: Ensure every IPC is counted individually
    df_raw['Classification'] = df_raw['Classification'].astype(str).str.split(',')
    df = df_raw.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Filter valid classification strings
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
    st.header("📊 Classification Distribution & Section Trends")
    st.write("Each unique IPC code in an application is counted individually.")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    
    # 1. Volume Bar Chart
    counts = sect_df.groupby('IPC_Section').size().reset_index(name='Apps')
    fig_hist = px.bar(counts, x='IPC_Section', y='Apps', text='Apps', 
                      title="Volume by IPC Section (A-H)",
                      color_discrete_sequence=['#FF6600'],
                      labels={'Apps': 'Number of Applications'})
    fig_hist.update_traces(textposition='outside')
    fig_hist.update_xaxes(showgrid=False) # Remove vertical lines
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    
    # 2. Yearly Growth of Sections
    st.subheader("Section Growth (Yearly Volume)")
    yearly_growth = sect_df.groupby(['Year_Int', 'IPC_Section']).size().reset_index(name='Apps')
    fig_line = px.line(yearly_growth, x='Year_Int', y='Apps', color='IPC_Section', markers=True,
                       labels={'Apps': 'Number of Applications', 'Year_Int': 'Year'})
    fig_line.update_xaxes(showgrid=False) # Remove vertical lines
    st.plotly_chart(fig_line, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (MA ZOOM) ---
elif menu == "Growth Analysis (MA Zoom)":
    st.header("📈 Growth Analysis: 12-Month Moving Average")
    st.info("The Y-axis represents the Number of Applications. The timeline is smoothed using a monthly Moving Average calculation.")

    # Unique IPC Dropdown
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
        # Group by precision month and Application Type
        grouped = analysis_df.groupby(['Month_TS', 'Application Type (ID)']).size().reset_index(name='Daily_Count')
        
        # Pivot for App Types
        pivot_df = grouped.pivot(index='Month_TS', columns='Application Type (ID)', values='Daily_Count').fillna(0)
        
        # Continuous Timeline for Math Accuracy
        full_range = pd.date_range(start=df['Month_TS'].min(), end=df['Month_TS'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # CALCULATE 12-MONTH MOVING AVERAGE
        ma_df = pivot_df.rolling(window=12).mean().reset_index().rename(columns={'index': 'Timeline'})
        
        # Melt for Plotting
        melted = ma_df.melt(id_vars='Timeline', var_name='Type ID', value_name='MA_Value')
        melted = melted.dropna()

        # DYNAMIC RANGE: Remove leading empty years where there is no data for THIS specific selection
        # This fixes the "empty 1950" issue
        actual_starts = melted[melted['MA_Value'] > 0]
        if not actual_starts.empty:
            earliest_point = actual_starts['Timeline'].min() - pd.DateOffset(years=1)
            melted = melted[melted['Timeline'] >= earliest_point]

        # Create Graph
        fig_ma = px.line(melted, x='Timeline', y='MA_Value', color='Type ID',
                         title=f"12-Month MA Trend: {target_ipc}",
                         labels={'MA_Value': 'Number of Applications', 'Timeline': 'Year'},
                         template='plotly_white')

        # CLEAN X-AXIS: Just Years, NO Vertical lines
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y", 
            showgrid=False, # Removed ugly vertical lines
            title="Year"
        )
        
        # Y-AXIS LABEL
        fig_ma.update_yaxes(
            title="Number of Applications",
            showgrid=True,
            gridcolor='whitesmoke'
        )
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)
        
        st.write(f"Displaying accurate smoothed application counts for **{target_ipc}**.")
