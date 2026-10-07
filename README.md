# Tradenza 🚀

### The Institutional Trading Companion & Behavioral Intelligence Platform

Tradenza is an institutional-grade, AI-assisted trading journal, pre-trade risk cockpit, and behavioral analytics platform. It helps traders achieve consistent profitability through mathematical expected value, volatility-adjusted position sizing, empirical analogue retrieval, active in-trade piloting, and forensic execution audits.

> *"Trade Less. Think Better. Improve Consistently."*

---

## 📖 Documentation
- 📘 **[Complete End-User Manual & Workflow Guide](docs/USER_GUIDE.md)**: Comprehensive step-by-step guide for using all platform features.
- 🏛️ **[System Architecture](docs/architecture.md)**: Deep dive into the Case-Based Intelligence Layer, Quant Feature Engine, and Memory subsystems.
- 📡 **[API & Endpoint Reference](docs/api.md)**: Blueprint endpoints, query parameters, and data models.
- 🗄️ **[Database Schema](docs/database.md)**: Complete schema models, relationships, and migrations.

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Virtual Environment

### 2. Installation & Running
```bash
# Clone the repository
git clone <repo_url>
cd Tradenza

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the Flask application
python app.py
```

Open your browser at:  
👉 **`http://127.0.0.1:5000`**

### 3. Demo Credentials
- **Email**: `atul@gmail.com`
- **Password**: `password123`
*(Or register a new account at `http://127.0.0.1:5000/register`)*

---

## 🌟 Key Features

### 1. 🏛️ Institutional Pre-Flight Trade Cockpit (`/trades/new`)
- **5-Pillar Confluence Score (0–100)**: Trend alignment, volume confirmation, ATR volatility health, news sentiment, and asymmetric R:R.
- **Mathematical Expected Value ($EV$)**: Real-time validation of setup expectancy before entering.
- **Volatility-Adjusted Half-Kelly Position Sizing**: Automatic share quantity sizing bounded by your account risk cap.
- **3-Tier Target Ladder**: TP1 (1.1R - De-risk 40% & Breakeven), TP2 (2.2R - Core swing 40%), and TP3 (3.5R+ - 20% Runner).
- **DeepSeek Devil's Advocate Pre-Mortem**: Real-time counter-thesis red-teaming powered by NVIDIA NIM (`deepseek-ai/deepseek-v4.1-flash`).
- **$K$-NN Similar Case Retrieval**: Weighted continuous vector similarity against curated empirical historical setups.

### 2. 🛩️ Active In-Trade Pilot (`/trades/<id>`)
- Real-time $R$-multiple telemetry HUD for open positions.
- **5 Lifecycle Stages**: Invalidation Danger, Noise Variance, De-Risking, Core Expansion, and Runner Phase.
- Dynamic Breakeven and ATR Trailing Stop directives.
- One-click **"Consult DeepSeek Trade Pilot"** for on-demand tactical market orders.

### 3. 🔬 Forensic Post-Mortem AI Audit (`/trades/<id>`)
- Audits closed trades with **Execution Alpha Score (0–100)** to separate luck from disciplined process.
- Planned vs Realized R:R comparison.
- Behavioral Root Cause discovery (FOMO, Revenge, Premature Profit Taking).
- Concrete Institutional Golden Rule for future execution.

### 4. 🧠 Trader Genome & Aura AI Coach (`/coach`)
- Algorithmic profiling into Trader Archetypes (e.g. *Disciplined Trend Follower*, *Premature Scalper*).
- Interactive conversational AI coach equipped with direct tool access to your trade logs and portfolio statistics.
- Automated **TradeBuddy Cooldown** emotional firebreak (30-minute lock upon revenge/overtrading trigger).

### 5. 🔮 Digital Twin Counterfactual Simulator (`/digital-twin`)
- "What-If" behavioral simulations (e.g., *What if I never cut winners early?* *What if I honored strict 2 loss daily limits?*).

### 6. 📊 Analytics, Market Scanner & CSV Bulk Operations
- **Market Scanner (`/market/scanner`)**: Live quotes for Indian stocks, US stocks, and Crypto.
- **Analytics (`/analytics`)**: Strategy win rates, profit factors, equity curves, and drawdown charts.
- **Broker CSV Import (`/trades/import`)**: Compatible with Zerodha, Groww, Angel One, Interactive Brokers, and standard CSV format.

---

## 🧪 Automated Testing
Tradenza comes with an automated unit test suite covering 100% of routes, calculations, AI gateways, and offline heuristics:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```text
Ran 81 tests in 6.570s
OK (81 / 81 Tests Passing)
```

---

## 🛠️ Tech Stack
- **Backend**: Flask 3.x, SQLAlchemy, SQLite
- **AI Intelligence**: NVIDIA NIM (DeepSeek V4.1 Flash), Google Gemini, OpenAI, Ollama Local (with zero-dependency pure Python HTTP clients and offline heuristic fallbacks)
- **Market Data**: Twelve Data, Finnhub Financial News & Sentiment
- **Frontend**: Bootstrap 5, Jinja2, Chart.js, HTML5/CSS3