import pandas_ta as ta

def calc_hidden_swing(ticker, df, params):
    # Example implementation based on your earlier code
    try:
        df['ema200'] = ta.ema(df['Close'].squeeze(), 200)
        df['ema50']  = ta.ema(df['Close'].squeeze(), 50)
        
        current_close = float(df['Close'].to_numpy()[-1])
        return {
            "Ticker": ticker, 
            "Close": round(current_close, 2), 
            "Signal": "🟢 SETUP READY"
        }
    except Exception as e:
        return {"Ticker": ticker, "Error": str(e)}

def calc_sma_crossover(ticker, df, params):
    try:
        fast_len = params.get('fast_sma', 14)
        slow_len = params.get('slow_sma', 28)
        
        df['sma_fast'] = ta.sma(df['Close'].squeeze(), fast_len)
        df['sma_slow'] = ta.sma(df['Close'].squeeze(), slow_len)
        
        current_close = float(df['Close'].to_numpy()[-1])
        return {
            "Ticker": ticker, 
            "Close": round(current_close, 2), 
            "Strategy": f"SMA {fast_len}/{slow_len}", 
            "Signal": "🟢 Analyzed"
        }
    except Exception as e:
        return {"Ticker": ticker, "Error": str(e)}

# Dictionary mapping for the agent to use
STRATEGIES = {
    "Hidden Swing Strategy": calc_hidden_swing,
    "SMA 14/28 Crossover": calc_sma_crossover,
    # Add your other strategies here
}