# Tradenza Product Requirements Document (PRD)

## 1. Product Summary & Vision
- **Product Name**: Tradenza
- **Tagline**: The Operating System for Traders — Intelligent Trading Companion.
- **Core Vision**: Most traders fail not because they lack technical market information, but because they lack self-awareness, emotional control, and disciplined execution. Tradenza exists to understand the trader, not to predict the market.
- **Target Audience**: Retail traders, prop-firm challenge participants, and systematic day/swing traders seeking consistency through behavioral accountability.

---

## 2. Core Value Proposition & Principles
1. **Behavior Over Prediction**: Sustainable trading success comes from managing one's own psychology, risk, and discipline.
2. **Deterministic Evidence Grounding**: The system never hallucinates advice. All insights, scores, and coaching prompts are mathematically tied to real logged execution data.
3. **Data → Insight → Action → Improvement**: Every insight must provide an immediate actionable behavioral step.
4. **Capital Protection First**: Enforce strict risk limits, position sizing guardrails, and loss-prevention interventions.

---

## 3. User Personas

### Persona A: Alex — The Frustrated Retail Trader
- **Profile**: 2 years experience trading forex and crypto. Consistently wins for several days, then wipes out profits in a single afternoon of emotional revenge trading.
- **Pain Point**: Struggles with emotional triggers and sizing up after losses.
- **Tradenza Solution**: Detects revenge trading patterns, flags escalating lot sizes within minutes of a loss, and prompts cooling-off periods via Aura Coach.

### Persona B: Priya — The Prop Firm Aspirant
- **Profile**: Working to pass evaluation challenges with strict daily drawdown limits (e.g., 4%) and max drawdown (8-10%).
- **Pain Point**: Tendency to overtrade on sluggish market days, triggering drawdown breaches.
- **Tradenza Solution**: Digital Twin monitors daily trade frequency, calculates Risk Control scores, and warns before overtrading causes rule violations.

---

## 4. Key Functional Modules

### Module 1: Comprehensive Trade Journal
- **Capability**: Rapid, frictionless logging of trades across all asset classes (Forex, Crypto, Stocks, Commodities, Indices).
- **Attributes Captured**: Symbol, Market, Side (BUY/SELL), Entry Price, Exit Price, Quantity, Strategy, Timeframe, Stop Loss, Target Price, Pre-Trade Emotion, Confidence (1-10), Trade Notes, and Chart Screenshots (pre/post).
- **Automation**: Automatic calculation of dollar and percentage P&L, Risk-to-Reward ratio, and trade status (`OPEN` / `CLOSED`).
- **Data Export & Search**: Full pagination, keyword search, strategy filtering, and one-click CSV export.

### Module 2: Deterministic Behavior Engine
- **Capability**: Evaluates trade logs against deterministic rule sets to detect cognitive biases and psychological leaks.
- **Pattern Detectors**:
  - **Revenge Trading**: Flags positions opened within 20 minutes of an exit loss with increased position sizing.
  - **Premature Exits (Early Exits)**: Flags winning trades exited before achieving 50% of the planned target move.
  - **Overtrading**: Flags days exceeding user trade volume limits (e.g., > 5 trades/day).
  - **High Risk Violations**: Flags trades risking > 2.5% of account balance or setups with R:R < 1:1.
  - **Holding Time Asymmetry**: Detects when losing trades are held significantly longer (> 2x) than winning trades ("hope trading").
  - **Weekend / Off-Hours Trading**: Identifies trades opened during low-liquidity weekend sessions.

### Module 3: Trader Genome & Archetype Classifier
- **Capability**: Scores traders across 9 continuous behavioral dimensions (0-100) and maps them into dynamic trader archetypes.
- **Dimensions**: Discipline, Patience, Consistency, Aggression, Risk Control, Decision Speed, Adaptability, Confidence, Learning Rate.
- **Archetypes**: Disciplined Master Trader, Patient Swing Strategist, Aggressive Momentum Scalper, High-Risk Speculator, Impulsive Revenge Trader, Developing Systematic Trader.

### Module 4: Digital Twin Behavioral Representation
- **Capability**: High-level synthetic representation of trader personality, decision profile, risk appetite, emotional distribution, and evolution trend (improving, stable, declining).
- **Visual Presentation**: Interactive radar and progress metrics helping traders view their execution profile objectively.

### Module 5: Aura Explanatory AI Coach
- **Capability**: Empathetic, supportive, evidence-based AI coaching layer that converts complex analytics into daily conversational advice.
- **Outputs**:
  - Contextual Coaching Narrative (grounded strictly in engine evidence).
  - Socratic Reflective Questions (prompting self-awareness).
  - Concrete Daily Mission (e.g., "Take a 20-minute break after any losing trade today").
  - Recommended Academy Lesson.

### Module 6: Portfolio & Equity Tracking
- **Capability**: Financial ledger tracking deposits, withdrawals, starting capital, current equity, realized P&L, high-water mark, and maximum drawdown.
- **Snapshots**: Daily automated equity snapshots powering interactive Chart.js equity curves and profit distribution charts.

---

## 5. Non-Functional Requirements & Security
- **Performance**: Dashboard and analytics computations must execute in under 300ms for user histories up to 1,000 trades.
- **Data Privacy**: Trader financial information and journal entries are strictly private to each authenticated account. Passwords stored using industry-standard salted hashing.
- **Offline / Isolated Execution**: Algorithmic calculations run locally within the application runtime without dependency on paid external LLM APIs for core scoring.
