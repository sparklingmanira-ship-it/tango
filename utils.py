import yfinance as yf
import aiosqlite
import asyncio
import pandas as pd
from datetime import datetime

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
    for attempt in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3mo", interval="1d")
            
            # --- DEFENSIVE DATA LOADING ---
            # info can sometimes be empty, use .get() safely
            info = t.info if t.info else {}
            
            # News can be an empty list or missing keys, handle safely
            news_items = t.news if t.news else []
            news_list = []
            for n in news_items:
                # Use .get() to avoid 'title' KeyError
                if isinstance(n, dict) and n.get('title'):
                    news_list.append(n.get('title'))
            
            if not news_list:
                news_list = ["No recent news available."]
            
            # --- REMAINING DATA FETCH ---
            sector_symbol = get_sector_index(ticker)
            sector_df = yf.Ticker(sector_symbol).history(period="3mo", interval="1d")
            
            vix_df = yf.Ticker("^VIX").history(period="1d")
            vix = 20.0 if vix_df.empty else vix_df['Close'].iloc[-1]
            
            macro_yield = yf.Ticker("^TNX").history(period="1mo") 
            macro_crude = yf.Ticker("BZ=F").history(period="1mo") 
            
            yield_close = macro_yield['Close'].iloc[-1] if not macro_yield.empty else 4.0
            crude_close = macro_crude['Close'].iloc[-1] if not macro_crude.empty else 75.0
            
            # Options chain (handle failure gracefully)
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
            await asyncio.sleep(3) 
            
    # Return empty structures if all attempts fail
    return pd.DataFrame(), 20.0, {}, ["No data available"], 1.0, 0.0, pd.DataFrame(), "^NSEI", 4.0, 75.0