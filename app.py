import streamlit as st
import asyncio
import pandas as pd
import os
from agents import TechnicalAgent, SentimentAgent, MacroRiskAgent
from utils import get_data, log_trade

# Use wider layout for better table viewing
st.set_page_config(layout="wide")
st.title("AI Trading Agent Dashboard")

st.markdown("### Stock Screener")

# --- 1. File Upload & Preloading Logic ---
default_file = "ind_nifty500list.csv"
tickers_list = []

uploaded_file = st.file_uploader("Upload a Custom Stock List (CSV format)", type=['csv'])

if uploaded_file is not None:
    # Load from User Upload
    df_upload = pd.read_csv(uploaded_file)
    # Autodetect column name
    col_name = 'Symbol' if 'Symbol' in df_upload.columns else ('Ticker' if 'Ticker' in df_upload.columns else df_upload.columns[0])
    tickers_list = [str(t).strip() for t in df_upload[col_name].dropna().tolist()]
    st.success(f"Loaded {len(tickers_list)} tickers from uploaded file.")
    
elif os.path.exists(default_file):
    # Load from Preloaded Default
    df_default = pd.read_csv(default_file)
    # The ind_nifty500list.csv has a 'Symbol' column. Yahoo Finance needs '.NS' for Indian stocks.
    if 'Symbol' in df_default.columns:
        tickers_list = [f"{str(t).strip()}.NS" for t in df_default['Symbol'].dropna().tolist()]
    else:
        tickers_list = [str(t).strip() for t in df_default.iloc[:, 0].dropna().tolist()]
    st.info(f"Preloaded Nifty 500 list. Loaded {len(tickers_list)} tickers.")
else:
    tickers_list = ["AAPL", "MSFT", "GOOGL"] # Fallback

# --- 2. Rate Limit Protection ---
st.warning("⚠️ Analyzing a large list of stocks simultaneously may trigger API rate limits. It is recommended to process them in batches.")
# Let the user chunk the execution to avoid YFRateLimitError
batch_size = st.number_input(
    "Number of stocks to analyze in this batch (0 to analyze all):", 
    min_value=0, max_value=len(tickers_list), value=min(20, len(tickers_list))
)

if batch_size > 0:
    tickers_list = tickers_list[:batch_size]

# --- 3. UI Ticker Input ---
# Populate the text area so it can still be manually edited before running
tickers_input = st.text_area(
    "Tickers to analyze (comma-separated):", 
    value=", ".join(tickers_list),
    height=150
)

if st.button("Run Bulk Analysis"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        results = []
        
        tech = TechnicalAgent()
        sent = SentimentAgent()
        risk = MacroRiskAgent()
        
        progress_text = "Analyzing stocks..."
        progress_bar = st.progress(0, text=progress_text)
        
        for i, ticker in enumerate(tickers):
            try:
                # 1. Fetch
                df, vix = asyncio.run(get_data(ticker))
                
                # 2. Analyze
                t_sig, t_conf, t_res, current_price = tech.analyze(df)
                s_sig, s_conf, s_res = sent.analyze(["Market looks good", "Earnings ahead"]) # Mock news
                r_sig, r_conf, r_res = risk.analyze(vix)
                
                # 3. Decision
                if r_sig == "HALT":
                    decision = "DO_NOT_TRADE"
                else:
                    score = (1 if t_sig == "BUY" else -1) * 0.6 + (1 if s_sig == "BULLISH" else -1) * 0.4
                    decision = "BUY" if score > 0.4 else "SELL" if score < -0.4 else "HOLD"
                
                # 4. Explainability Consolidation
                explanation = f"Tech: {t_res} | Sent: {s_res} | Macro: {r_res}"
                
                # 5. Price, SL, and Targets Setup
                buy_price = round(current_price, 2) if current_price else 0.0
                
                if decision == "BUY":
                    sl = round(buy_price * 0.95, 2)
                    t1 = round(buy_price * 1.05, 2)
                    t2 = round(buy_price * 1.10, 2)
                    t3 = round(buy_price * 1.15, 2)
                else:
                    sl, t1, t2, t3 = "-", "-", "-", "-"
                
                # Append to results list
                results.append({
                    "Ticker": ticker,
                    "Decision": decision,
                    "Price": buy_price,
                    "Stop Loss": sl,
                    "Target 1": t1,
                    "Target 2": t2,
                    "Target 3": t3,
                    "Explanation": explanation
                })
                
                # Log trade asynchronously
                asyncio.run(log_trade(ticker, decision, round(score if 'score' in locals() else 0, 2), explanation))
                
            except Exception as e:
                results.append({
                    "Ticker": ticker,
                    "Decision": "ERROR",
                    "Price": "-",
                    "Stop Loss": "-",
                    "Target 1": "-",
                    "Target 2": "-",
                    "Target 3": "-",
                    "Explanation": f"Failed: {str(e)}"
                })
            
            # Update progress bar
            progress_bar.progress((i + 1) / len(tickers), text=f"Analyzed {ticker} ({i+1}/{len(tickers)})")
        
        progress_bar.empty()
        
        # Display Results in a Table
        if results:
            results_df = pd.DataFrame(results)
            
            def color_decision(val):
                if val == 'BUY': return 'background-color: rgba(30, 200, 50, 0.2)'
                if val == 'SELL': return 'background-color: rgba(255, 50, 50, 0.2)'
                if val == 'ERROR': return 'background-color: rgba(255, 150, 0, 0.2)'
                return ''
            
            styled_df = results_df.style.map(color_decision, subset=['Decision'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)