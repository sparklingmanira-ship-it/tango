import yfinance as yf
import aiosqlite
import asyncio
import pandas as pd
import random
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
EODHD_API_KEY = "6a5e561b47f852.19359616" 

def get_sector_index(ticker):
    """Maps tickers to their respective Nifty sector indices."""
    sector_map = {
        "RELIANCE.NS": "^CNXENERGY",
        "TCS.NS": "^CNXIT",
        "INFY.NS": "^CNXIT",
        "HDFCBANK.NS": "^CNXBANK",
        "ICICIBANK.NS": "^CNXBANK",
        "MARUTI.NS": "^CNXAUTO",
        "TATAMOTORS.NS": "^CNXAUTO"
    }
    return sector_map.get(ticker, "^NSEI")

async def fetch_eodhd_news(ticker):
    """Fetches news independently so yfinance errors do not block news sentiment."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    news_url = (
        f"https://eodhd.com/api/news?"
        f"s={ticker}&"
        f"from={start_date}&"
        f"to={end_date}&"
        f"limit=10&"
        f"api_token={EODHD_API_KEY}&"
        f"fmt=json"
    )
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        news_response = requests.get(news_url, headers=headers, timeout=5).json()
        if isinstance(news_response, list) and len(news_response) > 0:
            titles = [article.get('title') for article in news_response if article.get('title')]
            if titles:
                return titles
    except Exception as e:
        print(f"EODHD News API Error for {ticker}: {e}")
        
    return ["No recent news available."]

async def get_data(ticker):
    """
    Fetches market data and news with isolated error handling.
    """
    # 1. ALWAYS fetch news independently first
    news_list = await fetch_eodhd_news(ticker)
    
    # Defaults
    df = pd.DataFrame()
    vix = 20.0
    info = {}
    pcr = 1.0
    sector_symbol = get_sector_index(ticker)
    sector_df = pd.DataFrame()
    yield_close = 4.0
    crude_close = 75.0

    # 2. Fetch main price data with retries
    for attempt in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3mo", interval="1d")
            if not df.empty:
                info = t.info if t.info else {}
                break
        except Exception as e:
            print(f"yfinance price attempt {attempt+1} failed for {ticker}: {e}")
            await asyncio.sleep(2)
            
    # 3. Isolated Macro Data fetches (failures won't break the whole app)
    try:
        vix_df = yf.Ticker("^VIX").history(period="1d")
        if not vix_df.empty: vix = float(vix_df['Close'].iloc[-1])
    except Exception: pass

    try:
        sector_df = yf.Ticker(sector_symbol).history(period="3mo", interval="1d")
    except Exception: pass

    try:
        macro_yield = yf.Ticker("^TNX").history(period="1mo") 
        if not macro_yield.empty: yield_close = float(macro_yield['Close'].iloc[-1])
    except Exception: pass

    try:
        macro_crude = yf.Ticker("BZ=F").history(period="1mo") 
        if not macro_crude.empty: crude_close = float(macro_crude['Close'].iloc[-1])
    except Exception: pass

    return df, vix, info, news_list, pcr, 0.0, sector_df, sector_symbol, yield_close, crude_close

async def log_trade(ticker, decision, score, reason):
    """Logs trading decisions to a local SQLite database."""
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()