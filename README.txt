README.md
Markdown
# AI Trading Agent Dashboard

A comprehensive, multi-agent algorithmic trading dashboard built with Streamlit. This application performs deep, multi-dimensional analysis on individual stocks by synthesizing Technical momentum, Quantitative fundamentals, NLP-driven sentiment, and Macroeconomic correlation into a unified trading recommendation.

## Features

* **Multi-Agent Architecture:** Utilizes specialized agents to independently evaluate distinct market dimensions.
* **Volatility-Adjusted Risk:** Automatically calculates dynamic Stop Loss and Profit Targets based on a 14-period Average True Range (ATR) rather than static percentages.
* **Deep Sentiment Processing:** Leverages the FinBERT small language model (LLM) to parse financial news and calculates institutional fear/greed via options chain Put/Call Ratios (PCR).
* **Macro & Sector Correlation:** Evaluates Mansfield Relative Strength against parent indices and monitors systemic headwinds like Crude Oil spikes and US 10-Year Bond Yields.
* **Quantitative Health Checks:** Validates trade setups against underlying company fundamentals (P/E ratios and profit margins).
* **Excel Export:** Generates styled, color-coded, and formatted `.xlsx` reports for individual stock analyses.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-directory>
Install dependencies:
Ensure you have Python 3.10+ installed. Install the required packages using uv or pip:

Bash
pip install -r requirements.txt
Note: The first time the application runs, the HuggingFace transformers library will download the FinBERT model weights (~400MB).

Run the application:

Bash
streamlit run app.py
File Structure
app.py: The Streamlit frontend, user interface, decision synthesis engine, and Excel export logic.

agents.py: Contains the logic for the four core analytical agents (TechnicalAgent, FundamentalAgent, DeepSentimentAgent, MacroSectorAgent).

utils.py: Data fetching pipelines utilizing yfinance and asynchronous SQLite logging.

requirements.txt: Package dependencies.

ind_nifty500list.csv: (Optional) Preloaded list of ticker symbols for the dashboard dropdown.