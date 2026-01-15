import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

# --- DATA REFINEMENT ENGINE ---
def refine_data(df):
    df.columns = df.columns.str.strip()
    if 'Application Date' in df.columns:
        df['Application Date'] = pd.to_datetime(df['Application Date'], errors='coerce')
        df['Year'] = df['Application Date'].dt.year.fillna(0).astype(int)
        df['Month'] = df['Application Date'].dt.month_name()
        df['Period'] = df['Application Date'].dt.to_period('M').astype(str)
        df['Date_Month'] = df['Application Date'].dt.to_period('M').dt.to_timestamp()
    if 'Earliest Priority Date' in df.columns:
        df['Earliest Priority Date'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
        df['Priority_Year'] = df['Earliest Priority Date'].dt.year.fillna(0).astype(int)
        df['Priority_Month'] = df['Earliest Priority Date'].dt.month_name()
        df['Priority_Period'] = df['Earliest Priority Date'].dt.to_period('M').astype(str)
    if 'Classification' in df.columns:
        df['Primary_IPC'] = df['Classification'].astype(str).str.split(',').str[0].str.strip().str[:4]
        df['IPC_Section'] = df['Primary_IPC'].str[:1].str.upper()
    return df

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo = Image.open("logo.jpeg")
        st.image(logo, use_container_width=True)
    except:
        st.title("🏛️ ARCHISTRATEGOS")
    st.markdown("---")
    data_source = st.radio("Select Data Source:", ["Default UAE Dataset", "Upload Custom CSV"])

try:
    if data_source == "Upload Custom CSV":
        uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
        df = refine_data(pd.read_csv(uploaded_file)) if uploaded_file else None
    else:
        # POINTING TO THE NEW FILENAME
        df = refine_data(pd.read_csv("Data Structure - Patents in UAE (Archistrategos) - All available types.csv"))
except:
    st.error("Data Source Error.")
    st.stop()

if df is not None:
    menu = st.sidebar.radio("Go to:", ["Time-Series Growth", "Classification & Country Strength", "Global Priority & Comparisons", "Growth Analysis (MA)", "Expert Search"])
    selected_country = st.sidebar.multiselect("Filter by Country", sorted(df['Country Name (Priority)'].dropna().unique()))
    filtered_df = df.copy()
    if selected_country:
        filtered_df = filtered_df[filtered_df['Country Name (Priority)'].isin(selected_country)]

    # --- MODULE 1: TIME-SERIES ---
    if menu == "Time-Series Growth":
        st.header("📈 Growth Trends & Temporal Analysis")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Total Applications per Year")
            yearly_counts = filtered_df[filtered_df['Year'] >= 1990].groupby('Year').size().reset_index(name='Count')
            fig_bar = px.bar(yearly_counts, x='Year', y='Count', text='Count', color_discrete_sequence=['#3498db'])
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            st.subheader("Yearly Registry")
            st.dataframe(yearly_counts.sort_values('Year', ascending=False), use_container_width=True, hide_index=True)

        st.subheader("📉 Yearly Application Trend (Line View)")
        fig_app_line = px.line(yearly_counts, x='Year', y='Count', markers=True)
        st.plotly_chart(fig_app_line, use_container_width=True)

    # --- MODULE 2: CLASSIFICATION ---
    elif menu == "Classification & Country Strength":
        st.header("🌍 IPC Strength & Country Activity")
        ipc_sections = filtered_df[(filtered_df['IPC_Section'].str.isalpha()) & (filtered_df['IPC_Section'].str.len() == 1) & (filtered_df['IPC_Section'] != 'T')]
        section_counts = ipc_sections.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
        fig_ipc_hist = px.bar(section_counts, x='IPC_Section', y='Count', text='Count', color_discrete_sequence=['#f39c12'])
        st.plotly_chart(fig_ipc_hist, use_container_width=True)
        
        all_ipcs = [x for x in sorted(filtered_df['Primary_IPC'].dropna().unique()) if x != "Ther"]
        target_ipc = st.selectbox("Detailed IPC Sector Analysis:", all_ipcs)
        leader_counts = filtered_df[filtered_df['Primary_IPC'] == target_ipc].groupby('Country Name (Priority)').size().reset_index(name='Count').sort_values('Count', ascending=False)
        st.plotly_chart(px.bar(leader_counts, x='Country Name (Priority)', y='Count', color_discrete_sequence=['#e74c3c']), use_container_width=True)

    # --- MODULE 3: GLOBAL PRIORITY ---
    elif menu == "Global Priority & Comparisons":
        st.header("🏁 Global Priority Analysis")
        valid_p = df[df['Priority_Year'] > 1900]['Priority_Year']
        p_range = st.sidebar.slider("Select Priority Year Range", int(valid_p.min()), int(valid_p.max()), (int(valid_p.max()-5), int(valid_p.max())))
        p_df = filtered_df[(filtered_df['Priority_Year'] >= p_range[0]) & (filtered_df['Priority_Year'] <= p_range[1])]
        
        actual = p_df.groupby(['Priority_Year', 'Priority_Month']).size().reset_index(name='Apps')
        actual['Priority_Year'] = actual['Priority_Year'].astype(str)
        st.plotly_chart(px.bar(actual, x='Priority_Month', y='Apps', color='Priority_Year', barmode='group'), use_container_width=True)

    # --- MODULE 4: GROWTH ANALYSIS (MA) ---
    elif menu == "Growth Analysis (MA)":
        st.header("📈 12-Month Moving Average (Application Type Growth)")
        
        # All unique codes for zooming
        all_codes = sorted(filtered_df['Classification'].str.split(',').explode().str.strip().unique())
        ipc_zoom = st.selectbox("Zoom into specific IPC Code:", ["Total for all IPC"] + all_codes)
        
        ma_df = filtered_df.copy()
        if ipc_zoom != "Total for all IPC":
            ma_df = ma_df[ma_df['Classification'].str.contains(ipc_zoom, na=False, regex=False)]
        
        ma_df = ma_df[ma_df['Year'] > 0]
        # Grouping by month and type
        grouped = ma_df.groupby(['Date_Month', 'Application Type (ID)']).size().reset_index(name='Counts')
        pivot_ma = grouped.pivot(index='Date_Month', columns='Application Type (ID)', values='Counts').fillna(0)
        
        # Ensure timeline is continuous for the Moving Average
        full_idx = pd.date_range(start=pivot_ma.index.min(), end=pivot_ma.index.max(), freq='MS')
        pivot_ma = pivot_ma.reindex(full_idx, fill_value=0)
        
        # Apply 12-month Rolling Mean
        rolling_df = pivot_ma.rolling(window=12).mean().reset_index().rename(columns={'index': 'Month'})
        melted = rolling_df.melt(id_vars='Month', var_name='App Type', value_name='Moving Average')
        
        fig_ma = px.line(melted, x='Month', y='Moving Average', color='App Type', 
                         title=f"Trend for: {ipc_zoom}", template="plotly_white")
        st.plotly_chart(fig_ma, use_container_width=True)

    # --- MODULE 5: EXPERT SEARCH ---
    elif menu == "Expert Search":
        st.header("🔍 Identify Experts")
        search = st.text_input("Search Registry:")
        if search:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            st.dataframe(filtered_df[mask][['Application Number', 'Classification', 'Country Name (Priority)', 'Application Date']], use_container_width=True, hide_index=True)
