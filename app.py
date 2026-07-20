import streamlit as st
import asyncio
import pandas as pd
import os
import io
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from agents import TechnicalAgent, FundamentalAgent, DeepSentimentAgent, MacroSectorAgent
from utils import get_data, log_trade

# --- UI Configuration ---
st.set_page_config(page_title="Tango Pro-Screener", layout="wide")

# Dark Theme CSS
st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background-color: #0F172A;
    }
    
    /* Titles and Subtitles */
    h1 { 
        color: #38BDF8 !important; 
        font-family: 'Helvetica', sans-serif; 
    }
    h3 {
        color: #94A3B8 !important;
    }
    
    /* Customizing the Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #1E293B; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #334155;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Ensure Metric Values and Labels are readable */
    div[data-testid="metric-container"] label {
        color: #94A3B8 !important;
    }
    div[data-testid="metric-container"] div {
        color: #F8FAFC !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Tango Pro-Screener")
st.markdown("### Institutional Quantitative Cluster Framework")

def export_to_excel(df):
    """Converts the results DataFrame to a styled Excel buffer."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Recommendation"
    header_fill = PatternFill(start_color="2B3A42", end_color="2B3A42", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    # Write header and data
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if r_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
    
    ws.column_dimensions['H'].width = 100
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# --- Ticker Loading ---
col1, col2 = st.columns([1, 2])
with col1:
    uploaded_file = st.file_uploader("Upload Ticker CSV", type=['csv'])
    append_ns = st.checkbox("Append '.NS' (NSE Stocks)", value=True)
    
    tickers_list = ["AAPL", "MSFT", "GOOGL"]
    
    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        # Target Symbol Column specifically
        col_name = 'Symbol' if 'Symbol' in df_upload.columns else df_upload.columns[0]
        raw = [str(t).strip().upper() for t in df_upload[col_name].dropna().tolist()]
        tickers_list = [f"{t}.NS" if append_ns and not t.endswith('.NS') else t for t in raw]
    
    elif os.path.exists("ind_nifty500list.csv"):
        df_default = pd.read_csv("ind_nifty500list.csv")
        tickers_list = [f"{str(t).strip().upper()}.NS" for t in df_default['Symbol'].dropna().tolist()]
    
    selected_ticker = st.selectbox("Select Asset:", options=tickers_list)
    analyze_btn = st.button("Run Quantitative Deep-Scan", type="primary")

# --- Analysis Pipeline ---
with col2:
    if analyze_btn:
        with st.spinner(f"Evaluating multi-dimensional parameters for {selected_ticker}..."):
            try:
                df, vix, info, news_list, pcr, social_score, sector_df, sector_symbol, yield_val, crude_val = asyncio.run(get_data(selected_ticker))
                
                # Agents
                t_sig, t_conf, t_res, current_price, current_atr = TechnicalAgent().analyze(df)
                f_sig, f_conf, f_res = FundamentalAgent().analyze(info)
                s_sig, s_conf, s_res = DeepSentimentAgent().analyze(news_list, pcr, social_score)
                m_sig, m_conf, m_res = MacroSectorAgent().analyze(df, sector_df, sector_symbol, yield_val, crude_val, vix)
                
                # --- FIXED DECISION RESOLUTION ---
                def map_signal(sig):
                    if sig in ["BUY", "BULLISH"]: return 1
                    if sig in ["SELL", "BEARISH"]: return -1
                    return 0 # Converts HOLD or NEUTRAL to a flat 0 modifier
                
                score = (map_signal(t_sig) * 0.35 + 
                         map_signal(m_sig) * 0.35 + 
                         map_signal(f_sig) * 0.20 + 
                         map_signal(s_sig) * 0.10)
                         
                decision = "BUY" if score > 0.2 else "SELL" if score < -0.2 else "HOLD"
                
                explanation = f"Tech: {t_res} | Correlation: {m_res} | Fund: {f_res} | Sent: {s_res}"
                
                # UI Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Ticker", selected_ticker)
                m2.metric("Decision", decision)
                m3.metric("Entry Price", f"₹{round(current_price, 2)}")
                
                res = [{"Ticker": selected_ticker, "Decision": decision, "Price": round(current_price, 2), 
                        "Stop Loss": round(current_price - (2*current_atr), 2) if current_atr > 0 else "-", 
                        "Explanation": explanation}]
                results_df = pd.DataFrame(res)
                
                st.dataframe(
                    results_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Explanation": st.column_config.TextColumn("Explanation", width="large")}
                )
                
                st.download_button("📥 Export Report", data=export_to_excel(results_df), file_name=f"{selected_ticker}_report.xlsx")
                
            except Exception as e:
                st.error(f"Analysis failed: {e}")