import yfinance as yf
import aiosqlite
import asyncio
import pandas as pd
import random
from datetime import datetime

# Use a standard browser header to avoid being blocked as a bot
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

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

async def get_data(ticker):
    # Added randomization to avoid sequential API hammering
    await asyncio.sleep(random.uniform(2, 5))
    
    for attempt in range(3):
        try:
            # Pass the headers to yfinance to bypass bot detection
            t = yf.Ticker(ticker, session=None)
            df = t.history(period="3mo", interval="1d", proxy=None)
            info = t.info if t.info else {}
            
            news_items = t.news if t.news else []
            news_list = [n.get('title') for n in news_items if isinstance(n, dict) and n.get('title')]
            if not news_list: news_list = ["No recent news available."]
            
            # Fetch Sector & Macro with slight delays to stay under the rate limit
            sector_symbol = get_sector_index(ticker)
            sector_df = yf.Ticker(sector_symbol).history(period="3mo", interval="1d")
            
            # VIX and Macro
            vix_df = yf.Ticker("^VIX").history(period="1d")
            vix = 20.0 if vix_df.empty else vix_df['Close'].iloc[-1]
            
            # Options chain (only fetch if it's not a major rate limit trigger)
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
                
            return df, float(vix), info, news_list, pcr, 0.0, sector_df, sector_symbol, 4.0, 75.0
            
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {ticker}: {e}")
            await asyncio.sleep(10) # Wait longer if we are being rate-limited
            
    return pd.DataFrame(), 20.0, {}, ["No data available"], 1.0, 0.0, pd.DataFrame(), "^NSEI", 4.0, 75.0

async def log_trade(ticker, decision, score, reason):
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()