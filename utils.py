import yfinance as yf
import aiosqlite
from datetime import datetime

async def get_data(ticker):
    # yf.Ticker().history() returns a flat DataFrame, avoiding MultiIndex issues
    df = yf.Ticker(ticker).history(period="1mo", interval="1d")
    
    vix_df = yf.Ticker("^VIX").history(period="1d")
    if vix_df.empty:
        vix = 20.0  # Fallback risk value if the API rate limits the VIX request
    else:
        vix = vix_df['Close'].iloc[-1]
        
    return df, float(vix)

async def log_trade(ticker, decision, score, reason):
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()