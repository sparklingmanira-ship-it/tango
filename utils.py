import yfinance as yf
import aiosqlite
import random
from datetime import datetime

# Simple mapping function for Nifty sectors. 
# You can expand this dictionary for your full stock list.
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
    return sector_map.get(ticker, "^NSEI") # Default to Nifty 50 if sector not explicitly mapped

async def get_data(ticker):
    t = yf.Ticker(ticker)
    
    # 1. Price Data (3 months to properly calculate Relative Strength vs Index)
    df = t.history(period="3mo", interval="1d")
    info = t.info
    
    # 2. Sector Index Data
    sector_symbol = get_sector_index(ticker)
    sector_df = yf.Ticker(sector_symbol).history(period="3mo", interval="1d")
    
    # 3. Macro Benchmarks (VIX, 10Y Yields, Crude Oil)
    vix_df = yf.Ticker("^VIX").history(period="1d")
    vix = 20.0 if vix_df.empty else vix_df['Close'].iloc[-1]
    
    macro_yield = yf.Ticker("^TNX").history(period="1mo") # US 10Y Yield
    macro_crude = yf.Ticker("BZ=F").history(period="1mo") # Brent Crude
    
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