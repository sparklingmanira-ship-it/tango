import yfinance as yf
import aiosqlite
from datetime import datetime

async def get_data(ticker):
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    vix = yf.download("^VIX", period="1d", progress=False)['Close'].iloc[-1]
    return df, float(vix)

async def log_trade(ticker, decision, score, reason):
    async with aiosqlite.connect("trading.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
        await db.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                         (ticker, decision, score, reason, datetime.now().isoformat()))
        await db.commit()