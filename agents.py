import pandas as pd
import pandas_ta as ta
import numpy as np
import streamlit as st
from transformers import pipeline

@st.cache_resource
def load_sentiment_pipeline():
    """Caches the FinBERT model to prevent redundant downloads and rate limits."""
    try:
        return pipeline("sentiment-analysis", model="ProsusAI/finbert")
    except Exception:
        return None

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

class MomentumAgent:
    def analyze(self, df):
        """Evaluates price trend persistence over 1-month and 3-month horizons."""
        if df is None or len(df) < 22:
            return "NEUTRAL", 0.0, "Insufficient history for Momentum"
            
        current_price = df['Close'].iloc[-1]
        price_1m_ago = df['Close'].iloc[-21]
        price_3m_ago = df['Close'].iloc[0]
        
        ret_1m = ((current_price / price_1m_ago) - 1) * 100
        ret_3m = ((current_price / price_3m_ago) - 1) * 100
        
        reasons = []
        score = 0
        
        # 3-Month Trend
        if ret_3m > 8.0:
            score += 1
            reasons.append(f"3M: +{ret_3m:.1f}% (Strong)")
        elif ret_3m < -8.0:
            score -= 1
            reasons.append(f"3M: {ret_3m:.1f}% (Weak)")
        else:
            reasons.append(f"3M: {ret_3m:.1f}% (Flat)")
            
        # 1-Month Trend
        if ret_1m > 4.0:
            score += 1
            reasons.append(f"1M: +{ret_1m:.1f}%")
        elif ret_1m < -4.0:
            score -= 1
            reasons.append(f"1M: {ret_1m:.1f}%")
            
        reason_str = " | ".join(reasons)
        if score > 0: return "BULLISH", 0.8, reason_str
        if score < 0: return "BEARISH", 0.8, reason_str
        return "NEUTRAL", 0.0, reason_str

class FundamentalAgent:
    def analyze(self, info):
        """Strictly evaluates Value (Price/Earnings and Price/Book)."""
        if not info:
            return "NEUTRAL", 0.0, "No fundamental data"
            
        pe = info.get('trailingPE', None)
        pb = info.get('priceToBook', None)
        
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
            
        if pb is not None:
            if pb < 3.0:
                score += 1
                reasons.append(f"P/B {pb:.1f} (Value)")
            elif pb > 6.0:
                score -= 1
                reasons.append(f"P/B {pb:.1f} (Expensive)")
            
        reason_str = " | ".join(reasons)
        if score > 0: return "BULLISH", 0.8, reason_str
        if score < 0: return "BEARISH", 0.8, reason_str
        return "NEUTRAL", 0.0, reason_str

class QualityAgent:
    def analyze(self, info):
        """Evaluates Profitability (ROE) and Balance Sheet Health (Debt/Equity)."""
        if not info:
            return "NEUTRAL", 0.0, "No quality data"
            
        roe = info.get('returnOnEquity', None)
        debt_eq = info.get('debtToEquity', None)
        
        reasons = []
        score = 0
        
        if roe is not None:
            roe_pct = roe * 100
            if roe_pct > 15.0:
                score += 1
                reasons.append(f"ROE {roe_pct:.1f}% (High Margin)")
            elif roe_pct < 5.0:
                score -= 1
                reasons.append(f"ROE {roe_pct:.1f}% (Low Margin)")
            else:
                reasons.append(f"ROE {roe_pct:.1f}% (Fair)")
        else:
            reasons.append("No ROE Data")
            
        if debt_eq is not None:
            if debt_eq < 60.0: 
                score += 1
                reasons.append(f"D/E {debt_eq:.1f}% (Safe)")
            elif debt_eq > 150.0:
                score -= 1
                reasons.append(f"D/E {debt_eq:.1f}% (Risky Leverage)")
                
        reason_str = " | ".join(reasons)
        if score > 0: return "BULLISH", 0.8, reason_str
        if score < 0: return "BEARISH", 0.8, reason_str
        return "NEUTRAL", 0.0, reason_str

class DeepSentimentAgent:
    def __init__(self):
        self.nlp = load_sentiment_pipeline()

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
            
            news_score = np.mean(scores) if scores else 0
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
    def analyze(self, df, sector_df, sector_symbol, yield_val, crude_val, vix, sector_name):
        if vix > 30:
            return "HALT", -1.0, f"VIX {vix:.2f} (Extreme Risk)"
            
        if df.empty or sector_df.empty:
            return "NEUTRAL", 0.0, "Insufficient correlation matrices"
            
        combined = pd.DataFrame({'Stock': df['Close'], 'Sector': sector_df['Close']}).dropna()
        if len(combined) < 20:
            return "NEUTRAL", 0.0, "Short index history"
            
        combined['Ratio'] = combined['Stock'] / combined['Sector']
        ratio_ma = combined['Ratio'].rolling(window=20).mean()
        
        rs_score = ((combined['Ratio'].iloc[-1] / ratio_ma.iloc[-1]) - 1) * 10
        rs_status = "Outperforming" if rs_score > 0 else "Underperforming"
        rs_reason = f"RS vs {sector_symbol}: {rs_score:.2f} ({rs_status})"
        
        macro_reasons = []
        macro_modifier = 0.0
        
        if crude_val > 85.0:
            if sector_name in ["Energy", "Basic Materials"]:
                macro_modifier += 0.2
                macro_reasons.append(f"Crude ${crude_val:.1f} (Revenue Tailwind for {sector_name})")
            elif sector_name in ["Consumer Cyclical", "Consumer Defensive", "Industrials"]:
                macro_modifier -= 0.2
                macro_reasons.append(f"Crude ${crude_val:.1f} (Margin Headwind for {sector_name})")
            else:
                macro_reasons.append(f"Crude ${crude_val:.1f} (Neutral for {sector_name})")
                
        if yield_val > 4.5:
            if sector_name == "Financial Services":
                macro_modifier += 0.2
                macro_reasons.append(f"US10Y {yield_val:.2f}% (NIM Expansion for {sector_name})")
            elif sector_name in ["Technology", "Real Estate", "Consumer Defensive", "Healthcare"]:
                macro_modifier -= 0.2
                macro_reasons.append(f"US10Y {yield_val:.2f}% (Valuation Headwind for {sector_name})")
            else:
                macro_reasons.append(f"US10Y {yield_val:.2f}% (Stable for {sector_name})")
                
        macro_reason_str = f" | Macro: {', '.join(macro_reasons)}" if macro_reasons else " | Macro: Stable"
        
        final_score = np.clip((0.6 if rs_score > 0 else -0.6) + macro_modifier, -1.0, 1.0)
        
        if final_score > 0.2:
            return "BULLISH", final_score, f"{rs_reason}{macro_reason_str}"
        elif final_score < -0.2:
            return "BEARISH", final_score, f"{rs_reason}{macro_reason_str}"
        return "NEUTRAL", 0.0, f"{rs_reason}{macro_reason_str}"

class MicrostructureAgent:
    def analyze(self, df, info):
        """Evaluates Analyst Estimates, Market Crowding, Short Interest, and Volume Liquidity."""
        if df is None or df.empty or not info:
            return "NEUTRAL", 0.0, "Insufficient Microstructure data"
            
        reasons = []
        score = 0
        current_price = df['Close'].iloc[-1]
        
        # 1. Crowding & Positioning (Institutional Ownership)
        inst_own = info.get('heldPercentInstitutions', None)
        if inst_own is not None:
            inst_pct = inst_own * 100
            if inst_pct > 70.0:
                score += 1
                reasons.append(f"Inst Own {inst_pct:.1f}% (High Institutional Backing)")
            elif inst_pct < 20.0:
                score -= 0.5
                reasons.append(f"Inst Own {inst_pct:.1f}% (Low Smart Money Support)")
        
        # 2. Short Interest (Crowding & Squeeze Potential)
        short_float = info.get('shortPercentOfFloat', None)
        if short_float is not None:
            short_pct = short_float * 100
            if short_pct > 10.0:
                score -= 1
                reasons.append(f"Short {short_pct:.1f}% (High Bearish Crowding)")
            elif short_pct < 2.0:
                score += 0.5
                reasons.append(f"Short {short_pct:.1f}% (Healthy/Low Short)")
                
        # 3. Liquidity & Volume Flow (ADV Surge & Illiquidity Checks)
        if len(df) >= 20:
            vol_20d_avg = df['Volume'].rolling(20).mean().iloc[-1]
            vol_today = df['Volume'].iloc[-1]
            
            if vol_20d_avg > 0:
                dollar_volume = vol_20d_avg * current_price
                if dollar_volume < 1000000:  # Less than 1M Dollar/Rupee Volume Risk
                    score -= 1
                    reasons.append("High Illiquidity Risk (<1M ADV)")
                
                vol_ratio = vol_today / vol_20d_avg
                if vol_ratio > 2.0:
                    score += 1
                    reasons.append(f"Vol {vol_ratio:.1f}x (Liquidity Surge)")
                elif vol_ratio < 0.5:
                    score -= 0.5
                    reasons.append("Volume Drying Up")
        
        # 4. Analyst Estimate Revisions (Target Price / Consensus)
        target_price = info.get('targetMeanPrice', None)
        rec_mean = info.get('recommendationMean', None)
        
        if rec_mean is not None:
            if rec_mean < 2.0:  # 1.0 is Strong Buy, 5.0 is Sell
                score += 1
                reasons.append(f"Analyst Consensus {rec_mean:.1f} (Strong Upgrade)")
            elif rec_mean > 3.0:
                score -= 1
                reasons.append(f"Analyst Consensus {rec_mean:.1f} (Downgrade)")
                
        if target_price is not None and current_price > 0:
            upside = ((target_price / current_price) - 1) * 100
            if upside > 15.0:
                score += 1
                reasons.append(f"Target Upside {upside:.1f}%")
            elif upside < -5.0:
                score -= 1
                reasons.append(f"Target Downside {upside:.1f}%")
                
        reason_str = " | ".join(reasons) if reasons else "Standard Flow Metrics"
        
        if score >= 1: return "BULLISH", 0.8, reason_str
        if score <= -1: return "BEARISH", 0.8, reason_str
        return "NEUTRAL", 0.0, reason_str