import pandas as pd
import pandas_ta as ta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class TechnicalAgent:
    def analyze(self, df):
        rsi = df.ta.rsi(length=14)
        val = rsi.iloc[-1]
        if val < 30: return "BUY", 0.85, f"RSI {val:.2f} (Oversold)"
        if val > 70: return "SELL", 0.85, f"RSI {val:.2f} (Overbought)"
        return "HOLD", 0.0, f"RSI {val:.2f} (Neutral)"

class SentimentAgent:
    def __init__(self): self.analyzer = SentimentIntensityAnalyzer()
    def analyze(self, news_list):
        if not news_list: return "NEUTRAL", 0.0, "No news"
        scores = [self.analyzer.polarity_scores(n)['compound'] for n in news_list]
        avg = sum(scores) / len(scores)
        if avg >= 0.05: return "BULLISH", avg, f"Score {avg:.2f}"
        if avg <= -0.05: return "BEARISH", avg, f"Score {avg:.2f}"
        return "NEUTRAL", avg, "Neutral news"

class MacroRiskAgent:
    def analyze(self, vix):
        if vix > 30: return "HALT", 1.0, f"VIX {vix} (Risk High)"
        return "ALLOW", 0.0, "Stable"