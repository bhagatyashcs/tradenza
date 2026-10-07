"""
Prompt Builder Service - Tradenza
Constructs context-grounded, Socratic prompts for Aura AI Coach,
injecting verified database facts (trades, risk rules, leaks, and genome).
"""

from typing import Any, Dict, List, Optional
from models.trade import Trade
from services.analytics import AnalyticsService
from services.statistics_service import StatisticsService
from services.tradebuddy import TradeBuddyService
from services.portfolio_service import PortfolioService


class PromptBuilder:
    """
    Builds structured system instructions and context payloads for LLMs.
    Guarantees that Aura is strictly grounded in the trader's verified facts.
    """

    @staticmethod
    def build_system_prompt(user) -> str:
        curr = getattr(user, "currency", "$") or "$"
        name = getattr(user, "name", "Trader") or "Trader"
        max_risk = getattr(user, "max_risk_percent", 2.0) or 2.0
        daily_loss_limit = getattr(user, "daily_max_loss", 500.0) or 500.0
        style = getattr(user, "ai_coaching_style", "socratic") or "socratic"

        # Gather real-time metrics
        stats = StatisticsService.get_dashboard_stats(user)
        analytics = AnalyticsService().get_dashboard_data(user)
        genome = analytics.get("genome") or {}
        behavior = analytics.get("behavior") or {}
        cooldown = TradeBuddyService.check_cooldown_status(user)
        portfolio = PortfolioService.get_or_create_portfolio(user)

        balance = portfolio.current_balance or portfolio.starting_balance or 10000.0
        archetype = genome.get("archetype", "Developing Apprentice")
        quality_score = round(genome.get("overall_score", 50.0), 1)
        win_rate = stats.get("win_rate", 0.0)
        total_pnl = stats.get("net_profit", 0.0)
        total_trades = stats.get("total_trades", 0)

        # Behavioral patterns
        patterns = behavior.get("patterns_detected") or []
        pattern_summaries = []
        for p in patterns[:3]:
            title = p.get("title") or p.get("pattern_type", "")
            pattern_summaries.append(f"- {title} (Severity: {p.get('severity', 'medium')})")
        patterns_str = "\n".join(pattern_summaries) if pattern_summaries else "- None detected. Clean execution."

        # Recent 4 trades snapshot
        recent_trades = (
            Trade.query.filter_by(user_id=user.id)
            .order_by(Trade.created_at.desc())
            .limit(4)
            .all()
        )
        trade_lines = []
        for t in recent_trades:
            pnl_val = f"+{curr}{t.profit_loss:.2f}" if (t.profit_loss or 0) >= 0 else f"-{curr}{abs(t.profit_loss or 0):.2f}"
            emo = getattr(t, "emotion_after", None) or getattr(t, "emotion_before", None) or "Neutral"
            trade_lines.append(
                f"- #{t.id} {t.symbol} ({t.market}) {t.trade_type} | Status: {t.status} | P/L: {pnl_val} | "
                f"Entry: {curr}{t.entry_price or 0} | Exit: {curr}{t.exit_price or 0} | "
                f"Emotion: {emo} | Setup: {t.strategy or 'Discretionary'}"
            )
        trades_str = "\n".join(trade_lines) if trade_lines else "- No trades logged yet."

        # Cooldown state
        if cooldown.get("in_cooldown"):
            cooldown_str = f"ACTIVE COOLDOWN (Triggered by {cooldown.get('trigger_symbol')} loss of {curr}{cooldown.get('loss_amount')}). Trader is under emotional firebreak."
        else:
            cooldown_str = "CLEAR (Trader is emotionally composed, no active cooldown)."

        # Coaching persona instructions
        if style == "disciplined":
            persona_guidance = (
                "Adopt a disciplined, uncompromising military-grade risk manager tone. "
                "Emphasize rule adherence, hard stop loss protection, and zero tolerance for gambling."
            )
        elif style == "analytical":
            persona_guidance = (
                "Adopt an analytical, data-driven quantitative tone. "
                "Focus on sample size, probability distributions, expected value (EV), and risk-to-reward ratios."
            )
        else:
            persona_guidance = (
                "Adopt a Socratic, empathetic trading psychologist tone (in the spirit of Mark Douglas' 'Trading in the Zone' "
                "and Dr. Brett Steenbarger). Ask probing questions to help the trader recognize emotional drivers."
            )

        system_prompt = f"""You are Aura, an elite AI Trading Psychology & Execution Coach at Tradenza.
Your mission is to guide {name} toward consistency, probabilistic thinking, and unwavering capital preservation.
{persona_guidance}

CRITICAL RULES:
1. NEVER invent or hallucinate trade results or account balances. Rely ONLY on the verified database facts below.
2. If asked about a trade, reference the specific trade number, symbol, and P/L from the verified facts.
3. Keep your replies concise (2-4 clear paragraphs or bullet points). Traders appreciate actionable clarity over fluff.
4. If the trader is on an active cooldown or expressing tilt/anger/revenge, DO NOT encourage trading. Enforce stepping away from the screen.
5. Format key metrics and takeaways cleanly in Markdown.

VERIFIED TRADER GROUND TRUTH:
- Trader Name: {name}
- Base Currency: {curr}
- Liquid Account Balance: {curr}{balance:.2f}
- Max Risk Per Trade Limit: {max_risk}%
- Daily Max Loss Limit: {curr}{daily_loss_limit:.2f}
- Trader Genome Archetype: {archetype} (Quality Index: {quality_score}/100)
- Lifetime Win Rate: {win_rate}% across {total_trades} trades (Net P/L: {curr}{total_pnl:.2f})
- Cooldown Firebreak Status: {cooldown_str}

IDENTIFIED BEHAVIORAL PATTERNS / LEAKS:
{patterns_str}

RECENT TRADE JOURNAL ENTRIES:
{trades_str}
"""
        return system_prompt.strip()

    @staticmethod
    def format_conversation_for_llm(
        system_prompt: str,
        conversation_history: List[Dict[str, Any]],
        new_user_message: str
    ) -> List[Dict[str, str]]:
        """
        Formats standard message history payload:
        [
            {"role": "system", "content": ...},
            {"role": "user", "content": ...},
            {"role": "assistant", "content": ...},
            {"role": "user", "content": new_user_message}
        ]
        """
        messages = [{"role": "system", "content": system_prompt}]

        for turn in conversation_history:
            role = "assistant" if turn.get("role") == "aura" else "user"
            content = turn.get("content") or ""
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": new_user_message})
        return messages
