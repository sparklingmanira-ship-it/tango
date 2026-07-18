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

st.set_page_config(layout="wide")
st.title("AI Trading Agent Dashboard")

st.markdown("### Institutional Quantitative Cluster Framework")

def export_to_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "Recommendation"

    header_fill = PatternFill(start_color="2B3A42", end_color="2B3A42", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    thin_border = Border(left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'), 
                         top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0'))
    
    buy_fill = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
    sell_fill = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid")
    error_fill = PatternFill(start_color="FEF7E0", end_color="FEF7E0", fill_type="solid")

    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if r_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = align_center
            else:
                cell.border = thin_border
                if c_idx in [1, 2]: cell.alignment = align_center
                elif c_idx == 8: cell.alignment = align_left
                else: cell.alignment = align_right
                
                decision_val = ws.cell(row=r_idx, column=2).value
                if decision_val == "BUY": cell.fill = buy_fill
                elif decision_val == "SELL": cell.fill = sell_fill
                elif decision_val == "ERROR": cell.fill = error_fill

    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 12
    for col in ['C', 'D', 'E', 'F', 'G']: ws.column_dimensions[col].width = 12
    ws.column_dimensions['H'].width = 130
    
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

default_file = "ind_nifty500list.csv"
tickers_list = []

uploaded_file = st.file_uploader("Upload a Custom Stock List (CSV format)", type=['csv'])

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)
    col_name = 'Symbol' if 'Symbol' in df_upload.columns else ('Ticker' if 'Ticker' in df_upload.columns else df_upload.columns[0])
    tickers_list = [str(t).strip().upper() for t in df_upload[col_name].dropna().tolist()]
    st.success(f"Loaded {len(tickers_list)} tickers from uploaded file.")
elif os.path.exists(default_file):
    df_default = pd.read_csv(default_file)
    if 'Symbol' in df_default.columns:
        tickers_list = [f"{str(t).strip().upper()}.NS" for t in df_default['Symbol'].dropna().tolist()]
    else:
        tickers_list = [str(t).strip().upper() for t in df_default.iloc[:, 0].dropna().tolist()]
    st.info(f"Loaded Nifty 500 options from context.")
else:
    tickers_list = ["AAPL", "MSFT", "GOOGL"]

selected_ticker = st.selectbox("Select a Ticker Symbol to Analyze:", options=tickers_list)

if st.button("Run Comprehensive Engine Analysis"):
    if not selected_ticker:
        st.warning("Please select a ticker.")
    else:
        results = []
        tech = TechnicalAgent()
        fund = FundamentalAgent()
        
        with st.spinner("Synchronizing FinBERT Weights..."):
            sent = DeepSentimentAgent()
            
        macro_sector = MacroSectorAgent()
        
        with st.spinner(f"Processing structural index matrices and alternative data sets for {selected_ticker}..."):
            try:
                # 1. Pull comprehensive data block
                df, vix, info, news_list, pcr, social_score, sector_df, sector_symbol, yield_val, crude_val = asyncio.run(get_data(selected_ticker))
                
                # 2. Extract Agent Assessment Profiles
                t_sig, t_conf, t_res, current_price, current_atr = tech.analyze(df)
                f_sig, f_conf, f_res = fund.analyze(info)
                s_sig, s_conf, s_res = sent.analyze(news_list, pcr, social_score)
                m_sig, m_conf, m_res = macro_sector.analyze(df, sector_df, sector_symbol, yield_val, crude_val, vix)
                
                # 3. Decision Resolution Node
                if m_sig == "HALT":
                    decision = "DO_NOT_TRADE"
                    score = -1.0
                else:
                    score = (
                        (1 if t_sig == "BUY" else -1 if t_sig == "SELL" else 0) * 0.35 + 
                        (1 if m_sig == "BULLISH" else -1 if m_sig == "BEARISH" else 0) * 0.35 + 
                        (1 if f_sig == "BULLISH" else -1 if f_sig == "BEARISH" else 0) * 0.20 + 
                        (1 if s_sig == "BULLISH" else -1 if s_sig == "BEARISH" else 0) * 0.10
                    )
                    decision = "BUY" if score > 0.25 else "SELL" if score < -0.25 else "HOLD"
                
                # 4. Comprehensive Explainability Output
                explanation = f"Tech: {t_res} (ATR: {current_atr:.2f}) | Correlation: {m_res} | Fund: {f_res} | Sent: {s_res}"
                
                # 5. Volatility Risk Execution
                buy_price = round(current_price, 2) if current_price else 0.0
                
                if decision == "BUY" and current_atr > 0:
                    sl = round(buy_price - (2 * current_atr), 2)
                    t1 = round(buy_price + (2 * current_atr), 2)
                    t2 = round(buy_price + (3 * current_atr), 2)
                    t3 = round(buy_price + (4 * current_atr), 2)
                else:
                    sl, t1, t2, t3 = "-", "-", "-", "-"
                
                results.append({
                    "Ticker": selected_ticker,
                    "Decision": decision,
                    "Price": buy_price,
                    "Stop Loss": sl,
                    "Target 1": t1,
                    "Target 2": t2,
                    "Target 3": t3,
                    "Explanation": explanation
                })
                
                asyncio.run(log_trade(selected_ticker, decision, round(score, 2), explanation))
                
            except Exception as e:
                results.append({
                    "Ticker": selected_ticker,
                    "Decision": "ERROR",
                    "Price": "-",
                    "Stop Loss": "-",
                    "Target 1": "-",
                    "Target 2": "-",
                    "Target 3": "-",
                    "Explanation": f"Matrix Compilation Failure: {str(e)}"
                })
        
        if results:
            results_df = pd.DataFrame(results)
            row = results[0]
            
            st.write("### Analysis Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Ticker", row["Ticker"])
            c2.metric("Systemic Decision Profile", row["Decision"])
            c3.metric("Current Entry Price", row["Price"])
            
            def color_decision(val):
                if val == 'BUY': return 'background-color: rgba(30, 200, 50, 0.2)'
                if val == 'SELL': return 'background-color: rgba(255, 50, 50, 0.2)'
                if val == 'ERROR': return 'background-color: rgba(255, 150, 0, 0.2)'
                return ''
            
            styled_df = results_df.style.map(color_decision, subset=['Decision'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            excel_buffer = export_to_excel(results_df)
            st.download_button(
                label=f"📥 Download Full {selected_ticker} Institutional Analysis",
                data=excel_buffer,
                file_name=f"{selected_ticker}_institutional_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )