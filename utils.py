import yfinance as yf
import aiosqlite
import asyncio
import pandas as pd
import random
from datetime import datetime

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

async def get_data(ticker):
    """
    Fetches comprehensive market data with built-in retry logic.
    """
    # Randomize delay to avoid API hammering
    await asyncio.sleep(random.uniform(2, 5))
    
    for attempt in range(3):
        try:
            t = yf.Ticker(ticker)
            # Fetch Price Data
            df = t.history(period="3mo", interval="1d")
            info = t.info if t.info else {}
            
            # Defensive news loading
            news_items = t.news if t.news else []
            news_list = [n.get('title') for n in news_items if isinstance(n, dict) and n.get('title')]
            if not news_list:
                news_list = ["No recent news available."]
            
            # Fetch Sector Index
            sector_symbol = get_sector_index(ticker)
            sector_df = yf.Ticker(sector_symbol).history(period="3mo", interval="1d")
            
            # Fetch Macro Benchmarks
            vix_df = yf.Ticker("^VIX").history(period="1d")
            vix = 20.0 if vix_df.empty else vix_df['Close'].iloc[-1]
            
            macro_yield = yf.Ticker("^TNX").history(period="1mo") 
            macro_crude = yf.Ticker("BZ=F").history(period="1mo") 
            
            yield_close = macro_yield['Close'].iloc[-1] if not macro_yield.empty else 4.0
            crude_close = macro_crude['Close'].iloc[-1] if not macro_crude.empty else 75.0
            
            # Options chain
            pcr = 1.0
            try:
                expirations = t.options
                if expirations:
                    opt = t.option_chain(expirations[0])
                    calls_vol = opt.calls['volume'].sum()
                    puts_vol = opt.puts['volume'].sum()
                    pcr = puts_vol / calls_vol if calls_vol > 0 else 1.0
            except:
                pcr = 1.0
                
            return df, float(vix), info, news_list, pcr, 0.0, sector_df, sector_symbol, yield_close, crude_close
            
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {ticker}: {e}")
            await asyncio.sleep(10)
            
    return pd.DataFrame(), 20.0, {}, ["No data available"], 1.0, 0.0, pd.DataFrame(), "^NSEI", 4.0, 75.0

async def log_trade(ticker, decision, score, reason):
    """Logs trading decisions to a local SQLite database."""
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()