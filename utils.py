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
        "Financial Services": "^NSEBANK",
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
    clean_ticker = ticker.split('.')[0]
    query = urllib.parse.quote(f"{clean_ticker} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(url)
        titles = [entry.title for entry in feed.entries][:10]
        if titles:
            return titles
    except Exception as e:
        print(f"Google News RSS Error for {ticker}: {e}")
        
    return ["No recent news available."]

async def fetch_price_history(ticker, period="3mo", interval="1d"):
    """
    Dual-Engine Price Fetcher: Attempts yfinance first. 
    If rate-limited or empty, falls back to yahooquery.
    """
    for attempt in range(3):
        # Engine 1: Try yfinance
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"yfinance price error for {ticker} (Attempt {attempt+1}): {e}")

        # Engine 2: Fallback to yahooquery
        try:
            yq_t = YQTicker(ticker)
            yq_df = yq_t.history(period=period, interval=interval)
            
            # Ensure the response is a valid dataframe and not a string error code
            if isinstance(yq_df, pd.DataFrame) and not yq_df.empty:
                # Reformat YahooQuery's multi-index to match yfinance exactly
                if 'symbol' in yq_df.index.names:
                    yq_df = yq_df.reset_index(level='symbol', drop=True)
                
                # Standardize column headers for the pandas-ta TechnicalAgent
                yq_df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                return yq_df
        except Exception as e:
            print(f"yahooquery price error for {ticker} (Attempt {attempt+1}): {e}")

        await asyncio.sleep(2)
        
    return pd.DataFrame()

async def get_data(ticker):
    """
    Fetches market data, reconstructing the info dictionary safely using YahooQuery.
    """
    news_list = await fetch_rss_news(ticker)
    
    # Defaults
    vix = 20.0
    info = {}
    pcr = 1.0
    yield_close = 4.0
    crude_close = 75.0

    # 1. Fetch main price data using the new Dual-Engine helper
    df = await fetch_price_history(ticker, period="3mo", interval="1d")
            
    # 2. Fetch Deep Fundamentals via YahooQuery (Bulletproof Extraction)
    try:
        yq_t = YQTicker(ticker)
        
        yq_summary = {}
        yq_fin = {}
        yq_profile = {}
        yq_key_stats = {}
        yq_holders = {}

        try:
            if hasattr(yq_t, 'summary_detail') and isinstance(yq_t.summary_detail, dict):
                yq_summary = yq_t.summary_detail.get(ticker, {})
        except Exception: pass

        try:
            if hasattr(yq_t, 'financial_data') and isinstance(yq_t.financial_data, dict):
                yq_fin = yq_t.financial_data.get(ticker, {})
        except Exception: pass

        try:
            if hasattr(yq_t, 'summary_profile') and isinstance(yq_t.summary_profile, dict):
                yq_profile = yq_t.summary_profile.get(ticker, {})
        except Exception: pass

        try:
            if hasattr(yq_t, 'key_stats') and isinstance(yq_t.key_stats, dict):
                yq_key_stats = yq_t.key_stats.get(ticker, {})
        except Exception: pass
        
        try:
            if hasattr(yq_t, 'institution_ownership') and isinstance(yq_t.institution_ownership, dict):
                yq_holders = yq_t.institution_ownership.get(ticker, {})
            elif hasattr(yq_t, 'major_holders_breakdown') and isinstance(yq_t.major_holders_breakdown, dict):
                 yq_holders = yq_t.major_holders_breakdown.get(ticker, {})
        except Exception: pass

        info = {
            'sector': yq_profile.get('sector', 'Unknown'),
            'trailingPE': yq_summary.get('trailingPE', yq_key_stats.get('trailingPE')),
            'priceToBook': yq_fin.get('priceToBook', yq_key_stats.get('priceToBook')),
            'returnOnEquity': yq_fin.get('returnOnEquity', yq_key_stats.get('returnOnEquity')),
            'debtToEquity': yq_fin.get('debtToEquity', yq_key_stats.get('debtToEquity')),
            'heldPercentInstitutions': yq_holders.get('institutionsPercentHeld', yq_key_stats.get('heldPercentInstitutions')),
            'shortPercentOfFloat': yq_key_stats.get('shortPercentOfFloat', yq_summary.get('shortPercentOfFloat')),
            'targetMeanPrice': yq_fin.get('targetMeanPrice'),
            'recommendationMean': yq_fin.get('recommendationMean')
        }
    except Exception as e:
        print(f"Total YahooQuery Failure for {ticker}: {e}")

    sector_symbol = get_sector_index(info)

    # 3. Isolated Macro Data fetches (Also secured via Dual-Engine)
    vix_df = await fetch_price_history("^VIX", period="1d")
    if not vix_df.empty: vix = float(vix_df['Close'].iloc[-1])

    sector_df = await fetch_price_history(sector_symbol, period="3mo")

    macro_yield = await fetch_price_history("^TNX", period="1mo")
    if not macro_yield.empty: yield_close = float(macro_yield['Close'].iloc[-1])

    macro_crude = await fetch_price_history("BZ=F", period="1mo")
    if not macro_crude.empty: crude_close = float(macro_crude['Close'].iloc[-1])

    return df, vix, info, news_list, pcr, 0.0, sector_df, sector_symbol, yield_close, crude_close

async def log_trade(ticker, decision, score, reason):
    """Logs trading decisions to a local SQLite database."""
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()