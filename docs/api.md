# Tradenza API & Route Specification

## 1. Overview

Tradenza is a server-rendered Flask web application with modular Blueprints. All private routes enforce user session authentication using Flask-Login (`@login_required`).

---

## 2. Route Directory & Endpoint Contracts

### A. Authentication Blueprint (`routes/auth.py` — prefix: none)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /register` | `GET` | No | Renders user registration form (`auth/register.html`). |
| `POST /register` | `POST` | No | Validates form and registers new user. Redirects to `/login` upon success. |
| `GET /login` | `GET` | No | Renders user login form (`auth/login.html`). |
| `POST /login` | `POST` | No | Authenticates user credentials with password hash. Logs user in and redirects to `/dashboard`. |
| `GET /logout` | `GET` | Yes | Terminates current session via `logout_user()` and redirects to `/login`. |

---

### B. Dashboard Blueprint (`routes/dashboard.py` — prefix: none)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /dashboard` | `GET` | Yes | Renders primary command center (`dashboard/dashboard.html`). Aggregates data from `StatisticsService`, `PortfolioService`, `TradeService`, `ChartService`, `AnalyticsService` (Behavior, Genome, Insights, Aura), and `DigitalTwinService`. |

---

### C. Trade Management Blueprint (`routes/trades.py` — prefix: `/trades`)

| Endpoint | Method | Auth Required | Parameters / Query Params | Description |
|---|---|---|---|---|
| `GET /trades/` | `GET` | Yes | `page` (int, default: 1)<br/>`query` (string)<br/>`market` (string)<br/>`trade_type` (string)<br/>`status` (string) | Paginated trade history view (`trade/history.html`). Supports text search and multi-facet filtering. |
| `GET /trades/new` | `GET` | Yes | `symbol`, `price`, `market`, `trade_type` (optional pre-fills) | Renders trade entry cockpit (`trade/new_trade.html`) with live institutional blueprint card and cooldown alert. |
| `POST /trades/new` | `POST` | Yes | Form fields (`TradeForm`) | Creates a new trade, updates portfolio cash balance, generates daily equity snapshot, and refreshes trader genome. |
| `GET /trades/<id>` | `GET` | Yes | `id` (int) | Renders trade details (`trade/details.html`). For open trades: renders Active Trade Pilot HUD and Target Ladder. For closed trades: renders Forensic AI Post-Mortem Audit Card. |
| `GET /trades/<id>/edit` | `GET` | Yes | `id` (int) | Renders trade editing form (`trade/edit_trade.html`). |
| `POST /trades/<id>/edit` | `POST` | Yes | `id` (int) + Form fields | Updates trade fields and recalculates portfolio balance. |
| `POST /trades/<id>/delete` | `POST` | Yes | `id` (int) | Deletes trade record and recalculates portfolio metrics. |
| `GET /trades/<id>/close` | `GET` | Yes | `id` (int) | Renders trade exit form (`trade/close_trade.html`). |
| `POST /trades/<id>/close` | `POST` | Yes | `id` (int) + `CloseTradeForm` | Records exit price, emotion, exit notes, calculates realized PnL and $R$-multiple, checks TradeBuddy cooldown trigger. |
| `GET /trades/export` | `GET` | Yes | None | Generates and streams `trades.csv` attachment containing user's trades. |
| `GET /trades/import` | `GET` | Yes | None | Renders broker CSV import page (`trade/import_trades.html`). |
| `POST /trades/import` | `POST` | Yes | `csv_file` (multipart file) | Parses CSV from Zerodha, Groww, Angel One, IBKR, or standard format and bulk imports trades. |
| `GET /trades/evidence_board` | `GET` | Yes | `symbol`, `strategy`, `price`, `stop_loss`, `target` | Returns JSON evidence board with $K$-NN historical analogues, dual scoring (Market Opportunity & Personal Fit), and company graph drivers. |
| `GET /trades/institutional_blueprint` | `GET` | Yes | `symbol`, `price`, `stop_loss`, `target`, `trade_type`, `strategy` | Returns JSON institutional blueprint: 5-Pillar Confluence Score, Mathematical Expected Value ($EV$), Volatility-Adjusted Half-Kelly sizing, 3-tier target ladder, and DeepSeek Pre-Mortem Red-Teaming. |
| `GET /trades/<id>/pilot_telemetry` | `GET` | Yes | `price` (optional), `consult_ai` (bool) | Computes real-time $R$-multiple, lifecycle stage (Danger/Noise/De-Risk/Core/Runner), dynamic trailing stop directive, and optional DeepSeek tactical advice. |

---

### D. Settings Blueprint (`routes/settings.py` — prefix: `/settings`)

| Endpoint | Method | Auth Required | Form Action / Params | Description |
|---|---|---|---|---|
| `GET /settings/` | `GET` | Yes | None | Renders settings page (`settings/settings.html`). |
| `POST /settings/` | `POST` | Yes | `action=preferences`<br/>`name`, `currency`, `max_risk_percent`, `daily_max_loss`, `starting_balance` | Updates account risk guardrails and portfolio baseline. |
| `POST /settings/` | `POST` | Yes | `action=password`<br/>`current_password`, `new_password`, `confirm_password` | Updates user password securely. |
| `POST /settings/` | `POST` | Yes | `action=ai`<br/>`ai_provider`, `ai_model`, `nvidia_api_key`, `gemini_api_key`, `openai_api_key`, `ai_coaching_style` | Saves AI provider, model, keys, and coaching persona. |

---

### E. Portfolio Blueprint (`routes/portfolio.py` — prefix: `/portfolio`)

| Endpoint | Method | Auth Required | Form Action / Params | Description |
|---|---|---|---|---|
| `GET /portfolio/` | `GET` | Yes | None | Renders portfolio ledger (`portfolio/portfolio.html`), summary metrics, and equity snapshots. |
| `POST /portfolio/transaction` | `POST` | Yes | `tx_type` (`deposit` or `withdrawal`), `amount` (float) | Processes cash balance deposit or withdrawal and updates ledger. |

---

### F. Analytics Blueprint (`routes/analytics_routes.py` — prefix: `/analytics`)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /analytics/` | `GET` | Yes | Renders detailed analytics dashboard (`analytics/analytics.html`) with Strategy Performance Breakdown, Market Breakdown, Long vs Short ratio, and Equity Curve. |

---

### G. AI Coach Blueprint (`routes/coach.py` — prefix: none)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /coach` | `GET` | Yes | Renders Aura conversational interface (`coach/aura.html`) with Trader Genome stats, reflective question, daily mission, and chat history. |
| `POST /coach/chat` | `POST` | Yes | Accepts JSON `{"message": "..."}` and returns Aura AI response with tool-augmented trading data. |
| `POST /coach/clear` | `POST` | Yes | Clears active conversation history for the current user. |

---

### H. Digital Twin Blueprint (`routes/digital_twin.py` — prefix: `/digital-twin`)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /digital-twin/` | `GET` | Yes | Renders behavioral twin interface (`digital_twin/digital_twin.html`) showing archetype, decision habits, emotional distribution, and "what-if" counterfactual simulation results. |

---

### I. Learning & Playbook Blueprint (`routes/learn.py` — prefix: `/learn`)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /learn/` | `GET` | Yes | Renders institutional trading playbook and academy (`learn/learn.html`). |

---

### J. Market Data Blueprint (`routes/market.py` — prefix: `/market`)

| Endpoint | Method | Auth Required | Parameters | Description |
|---|---|---|---|---|
| `GET /market/price` | `GET` | No | `symbol` (string, required) | Returns live market price for any instrument via Twelve Data API with offline benchmark fallback. |
| `GET /market/quote` | `GET` | No | `symbol` (string, required) | Returns complete real-time quote snapshot (open, high, low, close, volume, change, %, 52w range). |
| `GET /market/search` | `GET` | No | `query` (string, required) | Symbol autocomplete search across global exchanges. |
| `GET /market/history`| `GET` | No | `symbol` (string), `interval` (string), `outputsize` (int) | Historical candlestick OHLCV data for charting. |
| `GET /market/scanner`| `GET` | Yes | None | Renders interactive real-time Market Scanner (`market/scanner.html`) tracking multi-asset watchlists and top movers. |

---

### K. Application Root (`app.py`)

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `GET /` | `GET` | No | Welcome landing page indicating Tradenza service health and version. |
