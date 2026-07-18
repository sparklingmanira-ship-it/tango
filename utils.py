import yfinance as yf
import sqlite3
import pandas as pd
from datetime import datetime

def get_data(ticker):
    # Fetch historical data
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    # Fetch VIX and forcefully extract the raw float value
    vix_data = yf.download("^VIX", period="1d", progress=False)
    
    try:
        # Safely extract the last close price regardless of yfinance multi-index changes
        vix_val = float(vix_data['Close'].to_numpy()[-1])
    except Exception:
        # Fallback in case of API failure
        vix_val = 15.0 
        
    return df, vix_val

def log_trade(ticker, decision, score, reason):
    # Standard synchronous SQLite connection
    conn = sqlite3.connect("trading.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS logs (ticker, decision, score, reason, time)")
    
    # Convert dict/objects to string for safe database storage
    safe_reason = str(reason)
    
    cursor.execute("INSERT INTO logs VALUES (?,?,?,?,?)", 
                   (ticker, decision, score, safe_reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()