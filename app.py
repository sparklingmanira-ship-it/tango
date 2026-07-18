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

# Custom CSS for Professional FinTech Aesthetic
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1 { color: #1e3a42; font-family: 'Helvetica', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Tango Pro-Screener")
st.markdown("### Institutional Quantitative Cluster Framework")

def export_to_excel(df):
    """Converts results DataFrame to a styled Excel buffer."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Recommendation"
    header_fill = PatternFill(start_color="2B3A42", end_color="2B3A42", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
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

# --- Config & Inputs ---
col1, col2 = st.columns([1, 2])
with col1:
    uploaded_file = st.file_uploader("Upload Ticker CSV", type=['csv'])
    append_ns = st.checkbox("Append '.NS' (NSE Stocks)", value=True)
    
    tickers_list = ["AAPL", "MSFT", "GOOGL"]
    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file)
        raw = [str(t).strip().upper() for t in df_upload.iloc[:,0].dropna().tolist()]
        tickers_list = [f"{t}.NS" if append_ns and not t.endswith('.NS') else t for t in raw]
    
    selected_ticker = st.selectbox("Select Asset:", options=tickers_list)
    analyze_btn = st.button("Run Quantitative Deep-Scan", type="primary")

# --- Analysis Logic ---
with col2:
    if analyze_btn:
        with st.spinner(f"Analyzing {selected_ticker}..."):
            try:
                # Agents
                tech = TechnicalAgent()
                fund = FundamentalAgent()
                sent = DeepSentimentAgent()
                macro_sector = MacroSectorAgent()
                
                # Data
                df, vix, info, news_list, pcr, social_score, sector_df, sector_symbol, yield_val, crude_val = asyncio.run(get_data(selected_ticker))
                
                # Analysis
                t_sig, t_conf, t_res, current_price, current_atr = tech.analyze(df)
                f_sig, f_conf, f_res = fund.analyze(info)
                s_sig, s_conf, s_res = sent.analyze(news_list, pcr, social_score)
                m_sig, m_conf, m_res = macro_sector.analyze(df, sector_df, sector_symbol, yield_val, crude_val, vix)
                
                # Scoring
                score = ( (1 if t_sig == "BUY" else -1) * 0.35 + (1 if m_sig == "BULLISH" else -1) * 0.35 + (1 if f_sig == "BULLISH" else -1) * 0.20 + (1 if s_sig == "BULLISH" else -1) * 0.10 )
                decision = "BUY" if score > 0.2 else "SELL" if score < -0.2 else "HOLD"
                
                explanation = f"Tech: {t_res} | Correlation: {m_res} | Fund: {f_res} | Sent: {s_res}"
                
                # Risk Brackets
                buy_price = round(current_price, 2)
                sl = round(buy_price - (2 * current_atr), 2) if current_atr > 0 else "-"
                
                res = [{"Ticker": selected_ticker, "Decision": decision, "Price": buy_price, "Stop Loss": sl, "Explanation": explanation}]
                results_df = pd.DataFrame(res)
                
                # UI Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Ticker", selected_ticker)
                m2.metric("Decision", decision)
                m3.metric("Entry Price", f"₹{buy_price}")
                
                st.dataframe(results_df, use_container_width=True, hide_index=True, column_config={"Explanation": st.column_config.TextColumn("Explanation", width="large")})
                
                st.download_button("📥 Export Report", data=export_to_excel(results_df), file_name=f"{selected_ticker}_report.xlsx")
                
            except Exception as e:
                st.error(f"Analysis failed: {e}")