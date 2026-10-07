"""
Aura Conversational AI Coach Service - Tradenza
Provides context-grounded, Socratic conversational intelligence
deeply rooted in the trader's actual trade history, behavioral leaks,
and Trader Genome. Operates deterministically with zero latency.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app
from extensions import db
from models.coach_message import CoachMessage
from models.trade import Trade
from services.analytics import AnalyticsService
from services.statistics_service import StatisticsService
from services.tradebuddy import TradeBuddyService
from services.ai_gateway import AIGateway
from services.prompt_builder import PromptBuilder
from services.aura_tools import AuraTools
from services.evidence_board import EvidenceBoardService

logger = logging.getLogger(__name__)


class AuraChatService:
    """
    Conversational AI Engine for Aura Coach.
    Grounds natural language dialogue in verifiable database facts.
    """

    def process_message(self, user, user_message: str) -> Dict[str, Any]:
        user_text = (user_message or "").strip()
        if not user_text:
            return {
                "reply": "I'm listening. Ask me about your last trade, your behavioral leaks, or your session plan.",
                "followup_chips": ["Review my last trade", "What is my biggest leak?", "Am I on tilt right now?"],
                "orb_state": "calm",
                "intent": "empty"
            }

        # 1. Gather Trader Ground Truth Context
        trades = (
            Trade.query.filter_by(user_id=user.id)
            .order_by(Trade.created_at.desc())
            .all()
        )
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        open_trades = [t for t in trades if t.status == "OPEN"]

        stats = StatisticsService.get_dashboard_stats(user)
        analytics = AnalyticsService().get_dashboard_data(user)
        genome = analytics.get("genome") or {}
        behavior = analytics.get("behavior") or {}
        cooldown_info = TradeBuddyService.check_cooldown_status(user)

        # 2. Classify Intent
        intent = self._classify_intent(user_text)

        # 3. Hybrid AI Layer: Check if external LLM (NVIDIA/DeepSeek, Gemini, OpenAI, Ollama) is configured
        response_payload = None
        provider = getattr(user, "ai_provider", None) or "nvidia"
        try:
            cfg_provider = current_app.config.get("AI_PROVIDER", "nvidia")
            cfg_nvidia_key = current_app.config.get("NVIDIA_API_KEY", "")
            cfg_nvidia_base_url = current_app.config.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            cfg_gemini_key = current_app.config.get("GEMINI_API_KEY", "")
            cfg_openai_key = current_app.config.get("OPENAI_API_KEY", "")
            cfg_ollama = current_app.config.get("OLLAMA_ENDPOINT", "http://localhost:11434")
            user_model = getattr(user, "ai_model", None) or current_app.config.get("AI_MODEL")
        except Exception:
            cfg_provider = "nvidia"
            cfg_nvidia_key = ""
            cfg_nvidia_base_url = "https://integrate.api.nvidia.com/v1"
            cfg_gemini_key = ""
            cfg_openai_key = ""
            cfg_ollama = "http://localhost:11434"
            user_model = None

        active_provider = provider or cfg_provider
        api_key = ""
        if active_provider in ["nvidia", "deepseek"]:
            api_key = getattr(user, "nvidia_api_key", "") or cfg_nvidia_key
        elif active_provider == "gemini":
            api_key = getattr(user, "gemini_api_key", "") or cfg_gemini_key
        elif active_provider == "openai":
            api_key = getattr(user, "openai_api_key", "") or cfg_openai_key

        if active_provider not in ["offline"] and (api_key or active_provider in ["ollama", "local"]):
            try:
                system_prompt = PromptBuilder.build_system_prompt(user)
                history = self.get_conversation_history(user, limit=6)
                messages = PromptBuilder.format_conversation_for_llm(
                    system_prompt=system_prompt,
                    conversation_history=history,
                    new_user_message=user_text
                )
                success, reply = AIGateway.generate_chat_response(
                    provider=active_provider,
                    api_key=api_key,
                    messages=messages,
                    model=user_model,
                    ollama_endpoint=cfg_ollama,
                    nvidia_base_url=cfg_nvidia_base_url
                )
                if success and reply:
                    chips = self._get_contextual_chips(intent)
                    orb_state = "alert" if cooldown_info.get("in_cooldown") else "speaking"
                    response_payload = {
                        "reply": reply,
                        "followup_chips": chips,
                        "orb_state": orb_state,
                        "intent": intent,
                        "source": f"llm_{active_provider}"
                    }
            except Exception as e:
                logger.warning("LLM Gateway call failed, falling back to heuristics: %s", str(e))

        # 4. Fallback: Generate Grounded Heuristic Coaching Response
        if response_payload is None:
            response_payload = self._generate_response_for_intent(
                intent=intent,
                user_text=user_text,
                user=user,
                trades=trades,
                closed_trades=closed_trades,
                open_trades=open_trades,
                stats=stats,
                genome=genome,
                behavior=behavior,
                cooldown_info=cooldown_info
            )
            response_payload["source"] = "heuristic_engine"
            response_payload["intent"] = intent

        # 4. Persist User Message and Aura Response
        try:
            user_msg_record = CoachMessage(
                user_id=user.id,
                role="user",
                content=user_text,
                intent=intent
            )
            db.session.add(user_msg_record)

            aura_msg_record = CoachMessage(
                user_id=user.id,
                role="aura",
                content=response_payload["reply"],
                intent=intent,
                meta_json=json.dumps({
                    "chips": response_payload.get("followup_chips", []),
                    "orb_state": response_payload.get("orb_state", "calm")
                })
            )
            db.session.add(aura_msg_record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to persist coach messages: %s", str(e))

        return response_payload

    def get_conversation_history(self, user, limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieves recent conversation turns for the user."""
        records = (
            CoachMessage.query.filter_by(user_id=user.id)
            .order_by(CoachMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in records]

    def clear_conversation_history(self, user) -> bool:
        """Clears previous chat history."""
        try:
            CoachMessage.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to clear coach messages: %s", str(e))
            return False

    # ------------------------------------------------------------------
    # Intent Classification
    # ------------------------------------------------------------------

    def _classify_intent(self, text: str) -> str:
        q = text.lower()

        if any(k in q for k in ["last trade", "previous trade", "recent trade", "review trade", "trade #", "trade 4", "trade 1", "trade 2", "trade 3"]):
            return "review_last_trade"

        if any(k in q for k in ["tilt", "revenge", "cool down", "cooldown", "emotional", "angry", "frustrated"]):
            return "tilt_check"

        if any(k in q for k in ["leak", "weakness", "bad habit", "mistake", "why am i losing", "flaw"]):
            return "diagnose_leaks"

        if any(k in q for k in ["discipline", "genome", "quality score", "score", "archetype", "profile"]):
            return "discipline_score"

        if any(k in q for k in ["risk", "size", "sizing", "position size", "lot size", "stop loss", "sl"]):
            return "risk_sizing"

        if any(k in q for k in ["drawdown", "dd", "high water mark", "peak", "recovery", "underwater", "hwm"]):
            return "drawdown_analysis"

        if any(k in q for k in ["edge", "best setup", "best market", "strategy", "win rate", "crypto vs", "stocks vs"]):
            return "setup_edge"

        if any(k in q for k in ["plan", "pre-market", "prep", "routine", "mission", "today", "ready"]):
            return "session_prep"

        if any(k in q for k in ["avoid", "not trade", "avoidance", "danger zone", "what should i not trade", "avoid zone"]):
            return "avoidance_zone"

        if any(k in q for k in ["tata", "tatamotors", "aapl", "nvda", "tsla", "reliance", "tcs", "btc", "analyze setup", "should i buy", "should i trade", "case-based", "analogue"]):
            return "analyze_setup"

        return "general_coaching"

    # ------------------------------------------------------------------
    # Response Generation
    # ------------------------------------------------------------------

    def _generate_response_for_intent(
        self,
        intent: str,
        user_text: str,
        user,
        trades: List[Trade],
        closed_trades: List[Trade],
        open_trades: List[Trade],
        stats: Dict[str, Any],
        genome: Dict[str, Any],
        behavior: Dict[str, Any],
        cooldown_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        trader_name = user.name or "Trader"
        archetype = genome.get("archetype", "Developing Apprentice")
        quality_score = round(genome.get("overall_score", 50.0), 1)

        if intent == "analyze_setup":
            return self._handle_analyze_setup(trader_name, user, user_text)

        if intent == "avoidance_zone":
            return self._handle_avoidance_zone(trader_name, user, cooldown_info)

        if intent == "review_last_trade":
            return self._handle_review_last_trade(trader_name, closed_trades, open_trades)

        if intent == "tilt_check":
            return self._handle_tilt_check(trader_name, cooldown_info, closed_trades)

        if intent == "diagnose_leaks":
            return self._handle_diagnose_leaks(trader_name, behavior, closed_trades, genome)

        if intent == "discipline_score":
            return self._handle_discipline_score(trader_name, genome, quality_score, archetype)

        if intent == "risk_sizing":
            return self._handle_risk_sizing(trader_name, user, closed_trades, stats)

        if intent == "drawdown_analysis":
            return self._handle_drawdown_analysis(trader_name, user)

        if intent == "setup_edge":
            return self._handle_setup_edge(trader_name, closed_trades, stats)

        if intent == "session_prep":
            return self._handle_session_prep(trader_name, stats, genome, cooldown_info)

        return self._handle_general_coaching(trader_name, user_text, stats, genome, closed_trades)

    # ------------------------------------------------------------------
    # Specialized Handlers
    # ------------------------------------------------------------------

    def _handle_review_last_trade(self, name: str, closed: List[Trade], open_trades: List[Trade]) -> Dict[str, Any]:
        if not closed and not open_trades:
            return {
                "reply": f"You don't have any recorded trades in your journal yet, {name}. Log your first trade via the **New Trade** cockpit, and I'll dissect your entry, risk parameters, and execution quality.",
                "followup_chips": ["Help me plan my next trading session", "What is my primary behavioral leak?"],
                "orb_state": "calm"
            }

        target_trade = closed[0] if closed else open_trades[0]
        sym = target_trade.symbol
        dir_str = target_trade.trade_type
        entry = target_trade.entry_price
        exit_p = target_trade.exit_price
        pnl = target_trade.profit_loss
        sl = target_trade.stop_loss
        tp = target_trade.target
        qty = abs(float(target_trade.quantity or 1.0))

        lines = [f"### Post-Mortem: Trade #{target_trade.id} — {sym} ({dir_str})"]

        if target_trade.status == "CLOSED":
            is_win = (pnl or 0) >= 0
            pnl_badge = f"+${pnl:.2f} (WIN 🎯)" if is_win else f"-${abs(pnl):.2f} (LOSS 🛑)"
            lines.append(f"• **Outcome**: {pnl_badge} on {qty:.2f} units.")
            lines.append(f"• **Execution**: Entered @ ${entry:.2f} ➔ Exited @ ${exit_p:.2f}.")

            # Target / SL analysis
            if tp and exit_p:
                if (dir_str == "BUY" and exit_p >= tp) or (dir_str == "SELL" and exit_p <= tp):
                    lines.append(f"• **Target Adherence**: Full planned target (${tp:.2f}) was achieved. Exemplary patience holding the position.")
                elif abs(exit_p - tp) < 0.5:
                    lines.append(f"• **Target Adherence**: Exited virtually at your planned target (${tp:.2f}).")
                elif is_win:
                    lines.append(f"• **Target Adherence**: You exited profitably, but ahead of your full target (${tp:.2f}). Did fear of giving back profit prompt an early exit?")

            if sl and not is_win:
                if (dir_str == "BUY" and exit_p <= sl) or (dir_str == "SELL" and exit_p >= sl):
                    lines.append(f"• **Risk Discipline**: Stop loss was respected cleanly at ${sl:.2f}. Taking defined losses is the mark of a professional.")
                else:
                    lines.append(f"• **Risk Discipline**: Loss exceeded planned SL (${sl:.2f}). Never widen a stop loss mid-trade.")

            if target_trade.emotion_after:
                lines.append(f"• **Post-Exit Psychology**: Logged as *'{target_trade.emotion_after}'*.")

            lines.append("\n**Socratic Reflection**: *When you executed your exit, were you responding to an objective market signal or an internal emotional impulse?*")
        else:
            lines.append(f"• **Status**: Position is currently **OPEN**.")
            lines.append(f"• **Parameters**: Entry @ ${entry:.2f} | SL @ ${sl or 'None'} | Target @ ${tp or 'None'}.")
            lines.append(f"• **Active Focus**: Let the trade work according to your pre-defined rules. Avoid micromanaging sub-minute candles.")

        return {
            "reply": "\n".join(lines),
            "followup_chips": ["What is my primary behavioral leak?", "Am I on tilt right now?", "How is my discipline score trending?"],
            "orb_state": "speaking"
        }

    def _handle_tilt_check(self, name: str, cooldown: Dict[str, Any], closed: List[Trade]) -> Dict[str, Any]:
        in_cooldown = cooldown.get("in_cooldown", False)
        cooldown_mins = cooldown.get("remaining_minutes", 0)

        if in_cooldown:
            return {
                "reply": f"⚠️ **Tilt Alert Active for {name}**.\n\nYou closed a losing trade within the last 20 minutes ({cooldown_mins} minutes remaining in psychological reset window).\n\n• **Neurological Fact**: After an unexpected loss, the brain's amygdala triggers an urgent drive to recover lost capital ('Revenge Trading'). Heart rates spike, and trade selection quality drops by over 60%.\n• **Prescription**: Step away from the screens immediately. Drink water, take 10 slow breaths, and let your prefrontal cortex regain emotional equilibrium before placing any order.",
                "followup_chips": ["Review my last trade", "Give me a breathing exercise", "Help me plan my next trading session"],
                "orb_state": "alert"
            }

        # Check consecutive loss streak
        recent_losses = 0
        for t in closed[:3]:
            if (t.profit_loss or 0) < 0:
                recent_losses += 1

        if recent_losses >= 2:
            return {
                "reply": f"You are not in a hard cooldown window, {name}, but you have taken **{recent_losses} losses in your last 3 trades**.\n\nWhile consecutive losses are a statistical certainty in trading, this is the prime incubation zone for emotional revenge entries. Maintain strict 1% risk on your next entry and wait for an A+ confirmation.",
                "followup_chips": ["What is my primary behavioral leak?", "Check my risk parameters", "Plan next session"],
                "orb_state": "speaking"
            }

        return {
            "reply": f"🟢 **Emotional State: Centered & Neutral**.\n\nNo active cooldown is in effect, and your recent trade spacing indicates calm execution. You are in a sound headspace to evaluate high-conviction market setups.",
            "followup_chips": ["Review my last trade", "What is my primary behavioral leak?", "Am I respecting my risk parameters?"],
            "orb_state": "calm"
        }

    def _handle_diagnose_leaks(self, name: str, behavior: Dict[str, Any], closed: List[Trade], genome: Dict[str, Any]) -> Dict[str, Any]:
        patterns = behavior.get("patterns", [])
        leaks = []

        for p in patterns:
            title = p.get("title", "")
            drag = p.get("dollar_drag") or p.get("cost")
            drag_str = f" (Estimated capital drag: -${abs(drag):.2f})" if drag else ""
            leaks.append(f"• **{title}**{drag_str}: {p.get('description', '')}")

        if not leaks:
            return {
                "reply": f"Impressive execution, {name}. Your recent trading history exhibits **zero major behavioral leaks** (no revenge trades, no runaway positions, no post-loss overtrading).\n\nYour primary objective now is sustaining this baseline across changing market regimes.",
                "followup_chips": ["How is my discipline score trending?", "Review my last trade", "Help me plan my next trading session"],
                "orb_state": "calm"
            }

        reply_text = (
            f"Here is your **Behavioral Leak Diagnostic**, {name}:\n\n"
            + "\n".join(leaks)
            + "\n\n💡 **Aura's Rule**: Fix one leak at a time. Trying to eliminate every flaw simultaneously causes cognitive fatigue. Pick your costliest leak above and make eliminating it your singular mission today."
        )

        return {
            "reply": reply_text,
            "followup_chips": ["How is my discipline score trending?", "Am I on tilt right now?", "Review my last trade"],
            "orb_state": "speaking"
        }

    def _handle_discipline_score(self, name: str, genome: Dict[str, Any], score: float, archetype: str) -> Dict[str, Any]:
        disc = genome.get("discipline", 50.0)
        risk_ctrl = genome.get("risk_control", 50.0)
        patience = genome.get("patience", 50.0)
        consistency = genome.get("consistency", 50.0)
        confidence_tier = genome.get("confidence_tier", "INSUFFICIENT_SAMPLE")
        confidence_msg = genome.get("confidence_message", "")
        factors = genome.get("factor_breakdowns", {})

        disc_factors = [f"• {f['factor']} ({f['impact']:+0.1f})" for f in factors.get("discipline", [])[1:3]]
        risk_factors = [f"• {f['factor']} ({f['impact']:+0.1f})" for f in factors.get("risk_control", [])[1:3]]

        factor_summary = ""
        if disc_factors or risk_factors:
            factor_summary = "\n\n**Explainability Audit Drivers**:\n" + "\n".join(disc_factors + risk_factors)

        tier_warning = ""
        if confidence_tier == "INSUFFICIENT_SAMPLE":
            tier_warning = f"\n\n⚠️ **Sample Size Notice**: {confidence_msg} Scores are calibrating."

        return {
            "reply": (
                f"### Trader Genome Assessment: {archetype}\n"
                f"**Composite Quality Index**: **{score} / 100**\n\n"
                f"• **Rule Discipline**: {disc:.1f}/100\n"
                f"• **Risk Control**: {risk_ctrl:.1f}/100\n"
                f"• **Execution Patience**: {patience:.1f}/100\n"
                f"• **Consistency**: {consistency:.1f}/100"
                f"{factor_summary}"
                f"{tier_warning}\n\n"
                f"Focus on strict stop-loss adherence and maintaining disciplined position sizing to expand your edge."
            ),
            "followup_chips": ["What is my primary behavioral leak?", "Check my drawdown status", "Am I respecting my risk parameters?"],
            "orb_state": "speaking"
        }

    def _handle_risk_sizing(self, name: str, user, closed: List[Trade], stats: Dict[str, Any]) -> Dict[str, Any]:
        params = AuraTools.get_risk_parameters(user.id)
        curr = params.get("currency", "$")
        max_pct = params.get("max_risk_percent", 2.0)
        max_dollars = params.get("max_risk_dollars_per_trade", 0.0)
        daily_limit = params.get("daily_max_loss_limit", 500.0)
        in_cd = params.get("in_cooldown", False)

        if not closed:
            return {
                "reply": (
                    f"### Risk Envelope Guidelines, {name}\n\n"
                    f"• **Max Risk Per Trade**: {max_pct}% ({curr}{max_dollars:.2f})\n"
                    f"• **Daily Max Loss Limit**: {curr}{daily_limit:.2f}\n\n"
                    f"Never enter a trade without an explicit invalidation stop loss."
                ),
                "followup_chips": ["Help me plan my next trading session", "Review my last trade"],
                "orb_state": "calm"
            }

        large_losses = [t for t in closed if (t.profit_loss or 0) < -max_dollars]
        if large_losses:
            worst = min(large_losses, key=lambda t: t.profit_loss or 0)
            return {
                "reply": (
                    f"### Risk Envelope Audit\n\n"
                    f"• **Enforced Max Risk Per Trade**: {max_pct}% ({curr}{max_dollars:.2f})\n"
                    f"• **Daily Max Loss Cap**: {curr}{daily_limit:.2f}\n\n"
                    f"⚠️ In your trading history, you took an outsized loss on **{worst.symbol}** ({curr}{abs(worst.profit_loss):.2f}) which breached your {curr}{max_dollars:.2f} threshold.\n\n"
                    f"• **Golden Sizing Equation**: `Quantity = Max $ Risk / |Entry - SL|`. Never adjust your stop to fit your preferred position size; adjust your size to fit the chart invalidation."
                ),
                "followup_chips": ["Check my drawdown status", "What is my primary behavioral leak?", "Am I on tilt right now?"],
                "orb_state": "alert"
            }

        return {
            "reply": (
                f"✅ **Risk Envelope Discipline: Sound**\n\n"
                f"• **Configured Risk Per Trade**: {max_pct}% ({curr}{max_dollars:.2f})\n"
                f"• **Daily Max Loss Limit**: {curr}{daily_limit:.2f}\n"
                f"• **Emotional Guardrail**: {'Active Cooldown 🛑' if in_cd else 'Normal Execution 🟢'}\n\n"
                f"Your logged positions are sized proportionally within your defined parameters."
            ),
            "followup_chips": ["Check my drawdown status", "What is my primary behavioral leak?", "How is my discipline score trending?"],
            "orb_state": "calm"
        }

    def _handle_drawdown_analysis(self, name: str, user) -> Dict[str, Any]:
        dd = AuraTools.get_drawdown(user.id)
        curr = dd.get("currency", "$")
        balance = dd.get("current_balance", 0.0)
        hwm = dd.get("high_water_mark", 0.0)
        dd_dollars = dd.get("drawdown_dollars", 0.0)
        dd_pct = dd.get("drawdown_percent", 0.0)
        recovery_needed = dd.get("recovery_percent_needed", 0.0)
        status = dd.get("status", "NORMAL")

        if dd_pct <= 0.01:
            reply = (
                f"### High-Water Mark & Capital Status\n\n"
                f"🏔️ **Account At Peak Equity!**\n"
                f"• **Current Liquid Equity**: {curr}{balance:,.2f}\n"
                f"• **High-Water Mark (Peak)**: {curr}{hwm:,.2f}\n"
                f"• **Current Drawdown**: 0.0%\n\n"
                f"You are trading at peak capital efficiency. Stay patient and avoid increasing position sizing recklessly on euphoria."
            )
            orb = "calm"
        else:
            status_emoji = "⚠️" if dd_pct < 15.0 else "🚨"
            reply = (
                f"### High-Water Mark & Drawdown Forensic\n\n"
                f"{status_emoji} **Drawdown Status**: **{status.replace('_', ' ')}** ({dd_pct:.2f}%)\n\n"
                f"• **Peak Equity (HWM)**: {curr}{hwm:,.2f}\n"
                f"• **Current Equity**: {curr}{balance:,.2f}\n"
                f"• **Capital Underwater**: -{curr}{dd_dollars:,.2f}\n"
                f"• **Required Return to Breakeven**: **+{recovery_needed:.2f}%**\n\n"
                f"💡 **Capital Protection Principle**: When in drawdown, your instinct is to trade bigger to recover faster. The quantitative reality is the opposite: scale down by 50% until positive expectancy is re-proven."
            )
            orb = "alert" if dd_pct >= 10.0 else "speaking"

        return {
            "reply": reply,
            "followup_chips": ["Am I on tilt right now?", "Am I respecting my risk parameters?", "What is my primary behavioral leak?"],
            "orb_state": orb
        }

    def _handle_setup_edge(self, name: str, closed: List[Trade], stats: Dict[str, Any]) -> Dict[str, Any]:
        if len(closed) < 2:
            return {
                "reply": f"I need at least 3-5 closed trades to map your mathematical edge with statistical validity, {name}. Continue logging your executions and setups.",
                "followup_chips": ["Help me plan my next trading session", "What is my primary behavioral leak?"],
                "orb_state": "calm"
            }

        market_wins: Dict[str, List[float]] = {}
        for t in closed:
            m = t.market or "Other"
            if m not in market_wins:
                market_wins[m] = []
            market_wins[m].append(t.profit_loss or 0.0)

        lines = ["### Your Setup & Market Edge Matrix"]
        for m, pnls in market_wins.items():
            wins = sum(1 for p in pnls if p > 0)
            tot = len(pnls)
            wr = (wins / tot) * 100 if tot > 0 else 0
            net = sum(pnls)
            sign = "+" if net >= 0 else "-"
            lines.append(f"• **{m}**: {wr:.0f}% Win Rate across {tot} trades ({sign}${abs(net):.2f} Net P/L)")

        lines.append("\n**Aura's Recommendation**: Double down on the market where your win rate and comfort are highest, while scaling back on underperforming instruments.")

        return {
            "reply": "\n".join(lines),
            "followup_chips": ["What is my primary behavioral leak?", "Review my last trade", "Am I respecting my risk parameters?"],
            "orb_state": "speaking"
        }

    def _handle_session_prep(self, name: str, stats: Dict[str, Any], genome: Dict[str, Any], cooldown: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reply": (
                f"### Daily Pre-Market Battle Plan for {name}\n\n"
                f"1. **Pre-Session Breathwork**: 2 minutes of box breathing before charts open.\n"
                f"2. **Risk Rule**: Max risk capped at **1.5% per trade**.\n"
                f"3. **Loss Limit**: If you take 2 consecutive losses today, close the trading terminal for the session.\n"
                f"4. **Execution Gate**: No entry without a defined Stop Loss and written Strategy tag in the Trade Cockpit.\n\n"
                f"*Are you prepared to commit to your rules regardless of market volatility today?*"
            ),
            "followup_chips": ["I commit to my rules", "Review my last trade", "What is my primary behavioral leak?"],
            "orb_state": "speaking"
        }

    def _handle_general_coaching(self, name: str, query: str, stats: Dict[str, Any], genome: Dict[str, Any], closed: List[Trade]) -> Dict[str, Any]:
        total_trades = len(closed)
        win_rate = stats.get("win_rate", 0)

        return {
            "reply": (
                f"I hear you, {name}. As your trading coach, I look at your decisions through the lens of your long-term edge.\n\n"
                f"Across your {total_trades} recorded trades with a **{win_rate}% win rate**, your profitability is governed far more by your emotional discipline and loss containment than by finding the 'perfect' indicator.\n\n"
                f"What specific aspect of your execution would you like us to optimize right now?"
            ),
            "followup_chips": ["Review my last trade", "What is my primary behavioral leak?", "Am I on tilt right now?", "Help me plan my next trading session"],
            "orb_state": "calm"
        }

    def _handle_analyze_setup(self, name: str, user, text: str) -> Dict[str, Any]:
        q = (text or "").upper()
        symbol = "TATAMOTORS"
        for s in ["TATAMOTORS", "TATA", "RELIANCE", "TCS", "NVDA", "AAPL", "TSLA", "BTC", "ETH"]:
            if s in q:
                symbol = s if s != "TATA" else "TATAMOTORS"
                break

        strategy = "Breakout"
        if "PULLBACK" in q or "RETEST" in q:
            strategy = "Pullback"
        elif "REVERSAL" in q or "MEAN REVERSION" in q:
            strategy = "Mean Reversion"

        board = EvidenceBoardService.synthesize_evidence_board(
            user=user,
            symbol=symbol,
            setup_type=strategy
        )

        m_score = board["market_opportunity_score"]
        p_fit = board["personal_fit_score"]
        ana = board["analogue_data"]
        avoidance = board["avoidance_zone_triggered"]

        avoid_alert = ""
        if avoidance:
            avoid_alert = "\n\n⚠️ **CRITICAL AVOIDANCE ALERT**: " + " ".join(board["avoidance_zone_reasons"][:1])

        reply = (
            f"### Case-Based Intelligence: {symbol} [{strategy} Setup]\n\n"
            f"• **Market Opportunity**: **{m_score}/100** (Technical & historical statistical edge)\n"
            f"• **Personal Execution Fit**: **{p_fit}/100** (Your historical behavior & psychology)\n\n"
            f"**Historical Analogue Evidence (N = {ana.get('total_analogues_found', 0)})**:\n"
            f"Out of {ana.get('total_analogues_found', 0)} historically identical market situations, "
            f"**{ana.get('win_rate_pct', 0)}%** resolved positively with a median 5-day gain of **{ana.get('median_5d_return_pct', 0)}%** "
            f"and average pre-target drawdown of -{abs(ana.get('avg_max_drawdown_pct', 0)):.1f}%.\n\n"
            f"**Aura's Dual-Score Verdict**:\n"
            f"{'The setup is technically valid, but your personal execution history indicates severe risk of mishandling exits. Scale position down or await a clearer confirmation.' if p_fit < 50 else 'Both market conditions and your personal execution track record are in alignment for this trade.'}"
            f"{avoid_alert}"
        )

        return {
            "reply": reply,
            "followup_chips": ["What is my avoidance zone?", "Calculate position size", "Review my last trade"],
            "orb_state": "alert" if avoidance else "speaking"
        }

    def _handle_avoidance_zone(self, name: str, user, cooldown_info: Dict[str, Any]) -> Dict[str, Any]:
        board = EvidenceBoardService.synthesize_evidence_board(
            user=user,
            symbol="TATAMOTORS",
            setup_type="Breakout"
        )
        avoidance = board["avoidance_zone_triggered"]
        reasons = board["avoidance_zone_reasons"]

        if avoidance:
            reasons_str = "\n".join([f"• ⚠️ {r}" for r in reasons])
            reply = (
                f"### 🛑 Active Avoidance Zone for {name}\n\n"
                f"Your capital defense rules are currently flagging the following high-risk zones:\n\n"
                f"{reasons_str}\n\n"
                f"**Mandatory Prescription**: Step away from the screens. Statistically, taking trades under these conditions accounts for the vast majority of your historical drawdown."
            )
            orb = "alert"
        else:
            reply = (
                f"### ✅ Avoidance Zone Status: CLEAR for {name}\n\n"
                f"• **Cooldown**: No active tilt timeouts.\n"
                f"• **Risk Integrity**: No consecutive loss blowout detected.\n"
                f"• **Advice**: You are emotionally and structurally clear to take verified A+ setups that meet your 5 pre-flight checklist gates."
            )
            orb = "calm"

        return {
            "reply": reply,
            "followup_chips": ["Analyze Tata Motors setup", "Calculate position size", "Review my last trade"],
            "orb_state": orb
        }

    def _get_contextual_chips(self, intent: str) -> List[str]:
        chip_map = {
            "analyze_setup": ["What is my avoidance zone?", "Calculate position size", "Review my last trade"],
            "avoidance_zone": ["Analyze Tata Motors setup", "Check my daily loss limit", "Review my last trade"],
            "review_last_trade": ["What is my primary behavioral leak?", "Am I on tilt right now?", "How can I improve my R:R?"],
            "tilt_check": ["Help me reset my psychology", "Review my last trade", "Check my daily loss limit"],
            "diagnose_leaks": ["How do I fix revenge trading?", "What is my discipline score?", "Review my last trade"],
            "discipline_score": ["What is my primary leak?", "Am I on tilt right now?", "How do I upgrade archetype?"],
            "risk_sizing": ["Calculate position size", "Review my last trade", "What is my daily risk limit?"],
            "setup_edge": ["Which market gives me best edge?", "Review my last trade", "What is my win rate?"],
            "session_prep": ["Am I on tilt right now?", "Review my risk rules", "Let's log a trade"],
        }
        return chip_map.get(intent, ["Review my last trade", "What is my biggest leak?", "Am I on tilt right now?"])
