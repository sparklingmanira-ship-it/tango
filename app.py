import streamlit as st
import asyncio
from agents import TechnicalAgent, SentimentAgent, MacroRiskAgent
from utils import get_data, log_trade

st.title("AI Trading Agent Dashboard")

ticker = st.text_input("Enter Ticker Symbol (e.g., AAPL):", "AAPL")

if st.button("Analyze"):
    # 1. Fetch
    df, vix = asyncio.run(get_data(ticker))
    
    # 2. Analyze
    tech = TechnicalAgent()
    sent = SentimentAgent()
    risk = MacroRiskAgent()
    
    t_sig, t_conf, t_res = tech.analyze(df)
    s_sig, s_conf, s_res = sent.analyze(["Market looks good", "Earnings ahead"]) # Mock news
    r_sig, r_conf, r_res = risk.analyze(vix)
    
    # 3. Decision
    if r_sig == "HALT":
        decision = "DO_NOT_TRADE"
    else:
        score = (1 if t_sig == "BUY" else -1) * 0.6 + (1 if s_sig == "BULLISH" else -1) * 0.4
        decision = "BUY" if score > 0.4 else "SELL" if score < -0.4 else "HOLD"
    
    # 4. Display & Log
    st.write(f"### Decision: {decision}")
    st.write(f"**Technical:** {t_sig} | **Sentiment:** {s_sig} | **Macro:** {r_sig}")
    asyncio.run(log_trade(ticker, decision, 0.0, t_res))