from scanner_logic import STRATEGIES

class TechnicalAgent:
    def __init__(self):
        self.strategies = STRATEGIES

    def analyze(self, ticker, df, strategy_name, params):
        # Route to the selected mathematical function
        strategy_func = self.strategies.get(strategy_name)
        
        if not strategy_func:
            return {"Ticker": ticker, "Error": f"Strategy {strategy_name} not found"}
            
        return strategy_func(ticker, df, params)