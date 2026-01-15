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

# --- DATA PROCESSING ENGINE ---
@st.cache_data
def load_data():
    file_name = "Data Structure - Patents in UAE (Archistrategos) - All available types.csv"
    df = pd.read_csv(file_name)
    df.columns = df.columns.str.strip()
    
    # Timeline: Use Earliest Priority Date
    df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df = df.dropna(subset=['Earliest Priority Date'])
    
    # Create a monthly timestamp for grouping
    df['Month_TS'] = df['Earliest Priority Date'].dt.to_period('M').dt.to_timestamp()
    
    # EXPLODE LOGIC: Treat multiple classifications as separate instances
    df['Classification'] = df['Classification'].astype(str).str.split(',')
    df = df.explode('Classification')
    df['Classification'] = df['Classification'].str.strip()
    
    # Filter out empty entries
    df = df[~df['Classification'].str.contains("no classification", case=False, na=False)]
    df = df[df['Classification'] != 'nan']
    
    # IPC Section for the Overview module
    df['IPC_Section'] = df['Classification'].str[:1].str.upper()
    
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
    menu = st.radio("Navigation", ["Classification Overview", "Growth Analysis (12-Month MA)"])

# --- MODULE 1: CLASSIFICATION OVERVIEW ---
if menu == "Classification Overview":
    st.header("📊 Individual IPC Section Strength")
    st.write("Counts every classification code individually, even if they share the same application.")
    
    valid_sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    sect_df = df[df['IPC_Section'].isin(valid_sections)]
    section_counts = sect_df.groupby('IPC_Section').size().reset_index(name='Total Counts')
    
    fig_sect = px.bar(section_counts, x='IPC_Section', y='Total Counts', text='Total Counts',
                      color_discrete_sequence=['#FF6600'], title="Volume of Classifications per Section")
    fig_sect.update_traces(textposition='outside')
    st.plotly_chart(fig_sect, use_container_width=True)

# --- MODULE 2: GROWTH ANALYSIS (12-MONTH MA) ---
elif menu == "Growth Analysis (12-Month MA)":
    st.header("📈 Growth Analysis (12-Month Moving Average)")
    st.markdown("Smoothing application volume using a 12-month window based on **Earliest Priority Date**.")

    # Unique IPC List for Zooming
    all_codes = sorted(df['Classification'].unique())
    target_ipc = st.selectbox("Select Individual IPC Code to Zoom:", ["TOTAL (All Classifications)"] + all_codes)

    # Filter for selected IPC
    if target_ipc == "TOTAL (All Classifications)":
        analysis_df = df.copy()
    else:
        analysis_df = df[df['Classification'] == target_ipc]

    if analysis_df.empty:
        st.error("No data found for the selected IPC.")
    else:
        # Group by Month and Application Type
        # This counts the total number of applications per type per month
        grouped = analysis_df.groupby(['Month_TS', 'Application Type (ID)']).size().reset_index(name='Monthly_Count')
        
        # Pivot to align the Application Types (1, 2, 3, 4, 5)
        pivot_df = grouped.pivot(index='Month_TS', columns='Application Type (ID)', values='Monthly_Count').fillna(0)
        
        # Consistent X-Axis: Fill gaps in the timeline from earliest to latest date in the dataset
        full_range = pd.date_range(start=df['Month_TS'].min(), end=df['Month_TS'].max(), freq='MS')
        pivot_df = pivot_df.reindex(full_range, fill_value=0)
        
        # CALCULATION: Accurate 12-Month Moving Average
        # We use mean() to show the 'average monthly volume' over the last year
        ma_df = pivot_df.rolling(window=12).mean().reset_index().rename(columns={'index': 'Month'})
        
        # Melt for plotting (converting columns back to rows)
        melted = ma_df.melt(id_vars='Month', var_name='App Type', value_name='Moving Average')
        melted = melted.dropna() # Drop the first 11 months of NaNs

        # Graph Creation
        fig_ma = px.line(melted, x='Month', y='Moving Average', color='App Type',
                         title=f"12-Month MA Growth Analysis: {target_ipc}",
                         labels={'Moving Average': '12-Month MA (Total Applications)', 'Month': 'Timeline (YYYY-MM)'},
                         template='plotly_white')

        # X-AXIS SETTINGS: Consistent ticks every 12 months, formatted YYYY-MM
        fig_ma.update_xaxes(
            dtick="M12", 
            tickformat="%Y-%m",
            showgrid=True,
            title="Year (YYYY-MM)"
        )
        
        # Y-AXIS SETTINGS
        fig_ma.update_yaxes(title="Total Applications (12-Month MA)")
        
        fig_ma.update_layout(hovermode='x unified')
        st.plotly_chart(fig_ma, use_container_width=True)
        
        st.write(f"The graph displays the smoothed growth trend for **{target_ipc}**. Ticks on the X-axis represent the start of each year.")
