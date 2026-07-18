AI Trading Agent Scanner
A modular, high-performance professional stock scanner built for retail traders. This application uses a multi-strategy architecture to scan equity markets in real-time, allowing users to toggle between sophisticated technical strategies like EMA Pullbacks, SMA Crossovers, and Macro-Trend analysis.

🚀 Key Features
Modular Strategy Engine: Isolate strategy math from UI logic, making it trivial to add new trading setups.

Multi-Strategy Support: Toggle between Swing, Institutional, and Macro strategies seamlessly.

Dynamic Watchlist: Add, remove, and manage custom stock lists via CSV.

Asynchronous Processing: Built for speed with batch processing capabilities.

Deployment Ready: Architected specifically for hosting on Streamlit Cloud.

📂 Project Structure
Plaintext
/
├── app.py              # Streamlit UI, Orchestrator, & Execution Loop
├── agents.py           # Technical Agent (Routing & Strategy Logic Interface)
├── scanner_logic.py    # Strategy Library (The math/indicator engine)
├── requirements.txt    # Project dependencies
└── saved_watchlist.csv # Local watchlist storage
🛠️ Installation
Clone the repository:

Bash
git clone https://github.com/yourusername/trading-scanner.git
cd trading-scanner
Install dependencies:

Bash
pip install -r requirements.txt
Run locally:

Bash
streamlit run app.py
⚙️ How to Add a New Strategy
We designed this for scalability. To add a new trading strategy:

Open scanner_logic.py.

Define your function (e.g., def calc_my_strategy(df, params): ...).

Add the function mapping to the STRATEGIES dictionary within scanner_logic.py.

Your new strategy will automatically appear in the Streamlit "Select Strategy" dropdown menu.

⚠️ Disclaimer
This tool is for educational purposes only. It is not financial advice. Automated trading and scanning carry significant risk. Always backtest your strategies thoroughly and manage your risk accordingly. The authors are not responsible for any financial losses incurred through the use of this software.

📈 Deployment
This project is optimized for Streamlit Cloud.

Push your code to a GitHub repository.

Connect your repository to Streamlit Cloud.

Your app will automatically build and deploy.

Pro-Tip for your GitHub Repo
When you push this to GitHub, make sure to add a .gitignore file so you don't accidentally push your local data files or cache folders:

Plaintext
# .gitignore
__pycache__/
*.db
*.csv
.DS_Store
.env