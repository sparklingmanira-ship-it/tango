import yfinance as yf
from yahooquery import Ticker as YQTicker
import feedparser
import urllib.parse
import aiosqlite
import asyncio
import pandas as pd
import random
from datetime import datetime

def get_sector_index(info):
    """Maps dynamic sectors to their respective Nifty sector indices."""
    sector = info.get('sector', '') if isinstance(info, dict) else ''
    sector_map = {
        "Technology": "^CNXIT",
        "Financial Services": "^CNXBANK",
        "Consumer Cyclical": "^CNXAUTO", 
        "Consumer Defensive": "^CNXFMCG",
        "Energy": "^CNXENERGY",
        "Basic Materials": "^CNXMETAL",
        "Healthcare": "^CNXPHARMA",
        "Industrials": "^CNXINFRA", 
        "Real Estate": "^CNXREALTY",
        "Communication Services": "^CNXMEDIA",
        "Utilities": "^CNXENERGY"
    }
    return sector_map.get(sector, "^NSEI")

async def fetch_rss_news(ticker):
    """Fetches unlimited free news via Google News RSS (No API Key Required)."""
    # Clean the ticker (e.g., 'RELIANCE.NS' -> 'RELIANCE') to get better news hits
    clean_ticker = ticker.split('.')[0]
    query = urllib.parse.quote(f"{clean_ticker} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        # Parse the XML RSS feed
        feed = feedparser.parse(url)
        # Extract the top 10 most recent headlines
        titles = [entry.title for entry in feed.entries][:10]
        if titles:
            return titles
    except Exception as e:
        print(f"Google News RSS Error for {ticker}: {e}")
        
    return ["No recent news available."]

async def get_data(ticker):
    """
    Fetches market data, reconstructing the info dictionary using YahooQuery.
    """
    # 1. Fetch News (Unlimited Free RSS)
    news_list = await fetch_rss_news(ticker)
    
    # Defaults
    df = pd.DataFrame()
    vix = 20.0
    info = {}
    pcr = 1.0
    sector_df = pd.DataFrame()
    yield_close = 4.0
    crude_close = 75.0

    # 2. Fetch main price data via yfinance
    for attempt in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3mo", interval="1d")
            if not df.empty:
                break
        except Exception as e:
            print(f"yfinance price attempt {attempt+1} failed for {ticker}: {e}")
            await asyncio.sleep(2)
            
    # 3. Fetch Deep Fundamentals via YahooQuery (Bypasses yfinance info limits)
    try:
        yq_t = YQTicker(ticker)
        
        # YahooQuery splits data into specific endpoints
        yq_summary = yq_t.summary_detail.get(ticker, {})
        yq_fin = yq_t.financial_data.get(ticker, {})
        yq_profile = yq_t.summary_profile.get(ticker, {})
        yq_holders = yq_t.major_holders_breakdown.get(ticker, {})
        
        # Reconstruct the dictionary to perfectly match the old yfinance schema
        if isinstance(yq_summary, dict) and isinstance(yq_fin, dict):
            info = {
                'sector': yq_profile.get('sector', 'Unknown') if isinstance(yq_profile, dict) else 'Unknown',
                'trailingPE': yq_summary.get('trailingPE'),
                'priceToBook': yq_fin.get('priceToBook', yq_summary.get('priceToBook')),
                'returnOnEquity': yq_fin.get('returnOnEquity'),
                'debtToEquity': yq_fin.get('debtToEquity'),
                'heldPercentInstitutions': yq_holders.get('institutionsPercentHeld') if isinstance(yq_holders, dict) else None,
                'shortPercentOfFloat': yq_summary.get('shortPercentOfFloat'),
                'targetMeanPrice': yq_fin.get('targetMeanPrice'),
                'recommendationMean': yq_fin.get('recommendationMean')
            }
    except Exception as e:
        print(f"YahooQuery Error for {ticker}: {e}")

    # Resolve sector index
    sector_symbol = get_sector_index(info)

    # 4. Isolated Macro Data fetches
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