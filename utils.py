import yfinance as yf
from tvDatafeed import TvDatafeed, Interval
import aiosqlite
import random
import pandas as pd
from datetime import datetime

# Initialize TradingView datafeed (Guest Mode)
tv = TvDatafeed()

def get_sector_index(ticker):
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

# Helper function to fetch price data using TradingView as a fallback
def fetch_price_data(ticker, period_days=90):
    # Tier 1: Try yfinance
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="3mo", interval="1d")
        if not df.empty:
            return df
    except Exception as e:
        print(f"yfinance failed for {ticker}: {e}")

    # Tier 2: Try TradingView tvdatafeed Fallback
    try:
        print(f"Attempting TradingView fallback for {ticker}...")
        
        # Strip '.NS' for TradingView, and set exchange to NSE
        tv_symbol = ticker.replace('.NS', '')
        
        # tvdatafeed uses n_bars instead of period strings. 90 trading days ~= 3 months
        df_tv = tv.get_hist(symbol=tv_symbol, exchange='NSE', interval=Interval.in_daily, n_bars=period_days)
        
        if df_tv is not None and not df_tv.empty:
            # Standardize columns to match yfinance output (Capitalized headers)
            df_tv.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            return df_tv
            
    except Exception as tv_e:
        print(f"TradingView fallback failed for {ticker}: {tv_e}")

    # Return empty DataFrame if both fail
    return pd.DataFrame()

async def get_data(ticker):
    # 1. Price Data using the Fallback Engine
    df = fetch_price_data(ticker)
    
    t = yf.Ticker(ticker)
    info = t.info
    
    # 2. Sector Index Data
    sector_symbol = get_sector_index(ticker)
    sector_df = fetch_price_data(sector_symbol)
    
    # 3. Macro Benchmarks (VIX, 10Y Yields, Crude Oil)
    vix_df = fetch_price_data("^VIX", period_days=2) # Short period for VIX
    vix = 20.0 if vix_df.empty else vix_df['Close'].iloc[-1]
    
    macro_yield = fetch_price_data("^TNX", period_days=20)
    macro_crude = fetch_price_data("BZ=F", period_days=20)
    
    yield_close = macro_yield['Close'].iloc[-1] if not macro_yield.empty else 4.0
    crude_close = macro_crude['Close'].iloc[-1] if not macro_crude.empty else 75.0
        
    # 4. News Headlines
    news_items = t.news
    news_list = [n['title'] for n in news_items[:5]] if news_items else ["Trading volume remains steady."]
    
    # 5. Options Chain (PCR)
    try:
        expirations = t.options
        if expirations:
            opt = t.option_chain(expirations[0])
            calls_vol = opt.calls['volume'].sum()
            puts_vol = opt.puts['volume'].sum()
            pcr = puts_vol / calls_vol if calls_vol > 0 else 1.0
        else:
            pcr = 1.0
    except Exception:
        pcr = 1.0
        
    # 6. Social Sentiment Placeholder
    social_score = random.uniform(-0.5, 0.5) 
        
    return df, float(vix), info, news_list, pcr, social_score, sector_df, sector_symbol, yield_close, crude_close

async def log_trade(ticker, decision, score, reason):
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()