import streamlit as st
import pandas as pd
import os
from agents import TechnicalAgent
from utils import get_data, log_trade

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Stock Scanner", layout="wide")
st.title("🚀 Professional Multi-Strategy Scanner")

# --- INITIALIZATION ---
agent = TechnicalAgent()
WATCHLIST_FILE = "saved_watchlist.csv"

# --- WATCHLIST LOGIC ---
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            df = pd.read_csv(WATCHLIST_FILE)
            if 'Symbol' in df.columns:
                return df['Symbol'].dropna().tolist()
        except: pass
    
    # Default list
    default_tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
    pd.DataFrame({"Symbol": default_tickers}).to_csv(WATCHLIST_FILE, index=False)
    return default_tickers

scan_list = load_watchlist()

# --- SIDEBAR UI ---
st.sidebar.header("1. Select Strategy")
selected_strategy = st.sidebar.selectbox(
    "Which strategy do you want to run?",
    ["Hidden Swing Strategy", "SMA 14/28 Crossover"] 
)

st.sidebar.header("2. Strategy Parameters")
params = {}
if selected_strategy == "Hidden Swing Strategy":
    params['req_trend'] = st.sidebar.checkbox("Require Stage 2 Trend", value=True)
elif selected_strategy == "SMA 14/28 Crossover":
    params['fast_sma'] = st.sidebar.number_input("Fast SMA Length", value=14)
    params['slow_sma'] = st.sidebar.number_input("Slow SMA Length", value=28)

st.sidebar.markdown("---")
st.sidebar.info(f"📁 {len(scan_list)} stocks currently loaded.")

# --- MAIN EXECUTION ---
if st.button("▶️ Scan Watchlist", type="primary"):
    st.write(f"Scanning {len(scan_list)} stocks...")
    
    progress_bar = st.progress(0)
    results = []
    
    # Fully synchronous loop
    for i, ticker in enumerate(scan_list):
        try:
            # 1. Fetch Data (Synchronously)
            df, vix = get_data(ticker)
            
            # 2. Analyze
            if df is not None and not df.empty:
                signal = agent.analyze(ticker, df, selected_strategy, params)
                
                if signal:
                    results.append(signal)
                    # 3. Log to SQLite database
                    decision = signal.get("Signal", "Scanned")
                    log_trade(ticker, decision, vix, str(signal))
                    
        except Exception as e:
            st.error(f"Failed to scan {ticker}: {e}")
            
        progress_bar.progress((i + 1) / len(scan_list))
        
    st.success("Scan Complete!")
    
    # Display Results
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("No setups found for the selected criteria.")