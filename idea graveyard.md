# Idea Graveyard

This document records ideas, architectural concepts, and features that were intentionally evaluated and discarded (or parked indefinitely) for Tradenza.

Documenting discarded ideas preserves institutional knowledge, prevents re-inventing anti-patterns, and reinforces Tradenza's core design principles.

---

## 1. Predictive Price Modeling / AI Market Forecasts
- **Concept**: Using deep learning (LSTMs / Transformers) to predict short-term stock or crypto price directions and generate buy/sell signals.
- **Why It Was Killed**:
  - Direct contradiction of Tradenza's foundational principle: *"Behavior Over Prediction"*.
  - Financial markets are non-stationary and noisy; retail algorithmic price predictors often lead to false confidence and severe drawdown.
  - Tradenza's competitive advantage is helping the *trader understand themselves*, not competing with multi-billion-dollar quantitative hedge funds.

---

## 2. Unconstrained LLM Chatbot Without Engine Grounding
- **Concept**: Embedding a generic OpenAI/Anthropic/Gemini chatbot to freely chat with users about their trades without structured deterministic payloads.
- **Why It Was Killed**:
  - LLMs hallucinate numbers, miscalculate risk-to-reward ratios, and offer contradictory financial advice.
  - Risk of liability and dangerous advice (e.g., advising a trader to double down on a losing position).
  - Replaced by **Aura Coach**, which strictly interprets deterministic engine payloads and adheres to a zero-hallucination constraint.

---

## 3. High-Frequency Real-Time WebSocket Tick Screener
- **Concept**: Streaming millisecond tick data into the Flask web server to show real-time market order books.
- **Why It Was Killed**:
  - Tradenza is an analytical journal and behavioral accountability platform, not an execution terminal.
  - Massive infrastructure complexity and hosting costs with minimal value to post-trade behavioral analysis.
  - Pushes traders toward hyperactive overtrading rather than deliberate, structured execution.

---

## 4. Public Social Trading Leaderboard Ranked Purely by P&L
- **Concept**: A global leaderboard showcasing traders sorted by dollar profit or raw percentage return.
- **Why It Was Killed**:
  - Raw P&L leaderboards incentivize reckless gambling, excessive leverage, and survivor-bias behavior.
  - Undermines trader mental health and discipline.
  - Future social features will focus on **Discipline Scores**, **Genome Evolution**, and **Risk Control adherence** rather than raw speculative profit.
