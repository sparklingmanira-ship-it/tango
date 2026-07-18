import pandas as pd
import pandas_ta as ta
import numpy as np
from transformers import pipeline

class TechnicalAgent:
    def analyze(self, df):
        if df is None or df.empty:
            return "HOLD", 0.0, "No price data", 0.0, 0.0
            
        rsi = df.ta.rsi(length=14)
        atr = df.ta.atr(length=14)
        
        if rsi is None or rsi.dropna().empty or atr is None or atr.dropna().empty:
            return "HOLD", 0.0, "Insufficient technical data", 0.0, 0.0
            
        val = rsi.iloc[-1]
        current_price = df['Close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        if val < 30: return "BUY", 0.85, f"RSI {val:.2f} (Oversold)", current_price, current_atr
        if val > 70: return "SELL", 0.85, f"RSI {val:.2f} (Overbought)", current_price, current_atr
        return "HOLD", 0.0, f"RSI {val:.2f} (Neutral)", current_price, current_atr

class FundamentalAgent:
    def analyze(self, info):
        if not info:
            return "NEUTRAL", 0.0, "No fundamental data"
            
        pe = info.get('trailingPE', None)
        margins = info.get('profitMargins', None)
        
        reasons = []
        score = 0
        
        if pe is not None:
            if pe < 20:
                score += 1
                reasons.append(f"P/E {pe:.1f} (Value)")
            elif pe > 40:
                score -= 1
                reasons.append(f"P/E {pe:.1f} (Expensive)")
            else:
                reasons.append(f"P/E {pe:.1f} (Fair)")
        else:
            reasons.append("No P/E Data")
            
        if margins is not None:
            margins_pct = margins * 100
            if margins_pct > 15:
                score += 1
                reasons.append(f"Margins {margins_pct:.1f}%")
            elif margins_pct < 5:
                score -= 1
                reasons.append(f"Margins {margins_pct:.1f}%")
            
        reason_str = " | ".join(reasons)
        if score > 0: return "BULLISH", 0.8, reason_str
        if score < 0: return "BEARISH", 0.8, reason_str
        return "NEUTRAL", 0.0, reason_str

class DeepSentimentAgent:
    def __init__(self):
        try:
            self.nlp = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        except Exception:
            self.nlp = None

    def analyze(self, news_list, pcr, social_score):
        news_score = 0
        news_reason = "No news"
        
        if news_list and self.nlp:
            results = self.nlp(news_list)
            scores = []
            for r in results:
                if r['label'] == 'positive': scores.append(r['score'])
                elif r['label'] == 'negative': scores.append(-r['score'])
                else: scores.append(0)
            
            news_score = np.mean(scores)
            news_reason = f"FinBERT: {news_score:.2f}"

        pcr_score = 0
        pcr_reason = f"PCR: {pcr:.2f}"
        if pcr > 1.2:
            pcr_score = -0.5 
            pcr_reason += " (Fear)"
        elif pcr < 0.7:
            pcr_score = 0.5 
            pcr_reason += " (Greed)"
        else:
            pcr_reason += " (Neutral)"

        total_sentiment = (news_score * 0.5) + (pcr_score * 0.3) + (social_score * 0.2)
        reason_str = f"{news_reason} | {pcr_reason}"
        
        if total_sentiment > 0.15: return "BULLISH", total_sentiment, reason_str
        if total_sentiment < -0.15: return "BEARISH", total_sentiment, reason_str
        return "NEUTRAL", total_sentiment, reason_str

class MacroSectorAgent:
    def analyze(self, df, sector_df, sector_symbol, yield_val, crude_val, vix):
        # 1. Systemic Execution Block (VIX Threshold Check)
        if vix > 30:
            return "HALT", -1.0, f"VIX {vix:.2f} (Extreme Risk)"
            
        # 2. Relative Strength Calculation vs Sector Index
        if df.empty or sector_df.empty:
            return "NEUTRAL", 0.0, "Insufficient correlation matrices"
            
        # Align timelines
        combined = pd.DataFrame({'Stock': df['Close'], 'Sector': sector_df['Close']}).dropna()
        if len(combined) < 20:
            return "NEUTRAL", 0.0, "Short index history"
            
        # Calculate Relative Strength ratio trend
        combined['Ratio'] = combined['Stock'] / combined['Sector']
        ratio_ma = combined['Ratio'].rolling(window=20).mean()
        
        # Mansfield Relative Strength calculation formula
        rs_score = ((combined['Ratio'].iloc[-1] / ratio_ma.iloc[-1]) - 1) * 10
        
        rs_status = "Outperforming" if rs_score > 0 else "Underperforming"
        rs_reason = f"RS vs {sector_symbol}: {rs_score:.2f} ({rs_status})"
        
        # 3. Inter-market Macro Filter
        macro_reasons = []
        macro_modifier = 0.0
        
        if crude_val > 85.0:
            macro_modifier -= 0.2
            macro_reasons.append(f"Crude ${crude_val:.1f} (High Inflation Headwind)")
        if yield_val > 4.5:
            macro_modifier -= 0.1
            macro_reasons.append(f"US10Y Yield {yield_val:.2f}% (Capital Outflow Pressure)")
            
        macro_reason_str = f" | Macro: {', '.join(macro_reasons)}" if macro_reasons else " | Macro: Stable"
        
        final_score = np.clip((0.6 if rs_score > 0 else -0.6) + macro_modifier, -1.0, 1.0)
        
        if final_score > 0.2:
            return "BULLISH", final_score, f"{rs_reason}{macro_reason_str}"
        elif final_score < -0.2:
            return "BEARISH", final_score, f"{rs_reason}{macro_reason_str}"
        return "NEUTRAL", 0.0, f"{rs_reason}{macro_reason_str}"