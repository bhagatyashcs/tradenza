"""
AI Trade Post-Mortem Auditor & Execution Alpha Engine - Tradenza
Performs rigorous post-trade forensic audits evaluating:
- Execution Alpha Score (0-100)
- Planned vs Realized Risk-to-Reward (R:R)
- Exit Quality Classification (Target Hit, Disciplined Stop, Premature Exit, Stop Violation)
- Actionable AI Takeaway & Root Cause Analysis
"""

import math
from typing import Any, Dict, Optional


class AiTradeAuditor:
    """
    Forensic AI Auditor analyzing single-trade execution precision.
    Grounded in pure risk-adjusted trade mathematics and behavioral psychology.
    """

    @staticmethod
    def audit_trade(trade) -> Dict[str, Any]:
        """
        Audits a trade instance and returns structured forensic analysis.
        """
        entry_price = float(trade.entry_price or 0.0)
        exit_price = float(trade.exit_price) if trade.exit_price is not None else None
        stop_loss = float(trade.stop_loss) if trade.stop_loss is not None else None
        target = float(trade.target) if trade.target is not None else None
        pnl = float(trade.profit_loss) if trade.profit_loss is not None else 0.0
        trade_type = (trade.trade_type or "BUY").upper()
        status = trade.status or "OPEN"

        # -------------------------------------------------------------
        # 1. Planned Risk, Reward, and R:R Ratio
        # -------------------------------------------------------------
        planned_risk_per_unit = 0.0
        planned_reward_per_unit = 0.0
        planned_rr = 0.0

        if stop_loss and entry_price:
            planned_risk_per_unit = abs(entry_price - stop_loss)

        if target and entry_price:
            planned_reward_per_unit = abs(target - entry_price)

        if planned_risk_per_unit > 0 and planned_reward_per_unit > 0:
            planned_rr = round(planned_reward_per_unit / planned_risk_per_unit, 2)

        # -------------------------------------------------------------
        # 2. Realized Risk-to-Reward & R Efficiency
        # -------------------------------------------------------------
        realized_r = 0.0
        r_efficiency_pct = 0.0

        if exit_price is not None and planned_risk_per_unit > 0:
            if trade_type == "BUY":
                delta = exit_price - entry_price
            else:
                delta = entry_price - exit_price

            realized_r = round(delta / planned_risk_per_unit, 2)

            if planned_rr > 0:
                if realized_r > 0:
                    r_efficiency_pct = round((realized_r / planned_rr) * 100, 1)
                else:
                    r_efficiency_pct = round((realized_r / planned_rr) * 100, 1)

        # -------------------------------------------------------------
        # 3. Exit Quality Classification
        # -------------------------------------------------------------
        exit_quality = "PENDING_EXECUTION"
        exit_badge_class = "info"
        exit_summary = "Position remains open."

        if status == "CLOSED" and exit_price is not None:
            if stop_loss and entry_price:
                # Check stop violation (loss allowed to run > 10% past SL)
                sl_distance = abs(entry_price - stop_loss)
                if trade_type == "BUY" and exit_price < (stop_loss - 0.05 * sl_distance):
                    exit_quality = "STOP_VIOLATION"
                    exit_badge_class = "danger"
                    exit_summary = "Stop Loss was violated or moved. Loss allowed to exceed defined risk."
                elif trade_type == "SELL" and exit_price > (stop_loss + 0.05 * sl_distance):
                    exit_quality = "STOP_VIOLATION"
                    exit_badge_class = "danger"
                    exit_summary = "Stop Loss was violated or moved. Loss allowed to exceed defined risk."

            if exit_quality != "STOP_VIOLATION":
                if target and entry_price:
                    target_distance = abs(target - entry_price)
                    achieved_distance = (exit_price - entry_price) if trade_type == "BUY" else (entry_price - exit_price)

                    if achieved_distance >= 0.92 * target_distance:
                        exit_quality = "TARGET_ACHIEVED"
                        exit_badge_class = "success"
                        exit_summary = "Profit target achieved. Patient plan execution."
                    elif achieved_distance > 0 and achieved_distance < 0.60 * target_distance:
                        exit_quality = "PREMATURE_EXIT"
                        exit_badge_class = "warning"
                        exit_summary = "Exited prematurely in profit before target. Fear or impatience trimmed edge."
                    elif achieved_distance > 0:
                        exit_quality = "DISCRETIONARY_PROFIT"
                        exit_badge_class = "success"
                        exit_summary = "Captured solid profit near target."

            if exit_quality in ("PENDING_EXECUTION", "STOP_VIOLATION"):
                if exit_quality == "PENDING_EXECUTION":
                    if stop_loss:
                        # Check disciplined stop
                        if (trade_type == "BUY" and abs(exit_price - stop_loss) / max(entry_price, 1) < 0.015) or \
                           (trade_type == "SELL" and abs(exit_price - stop_loss) / max(entry_price, 1) < 0.015):
                            exit_quality = "DISCIPLINED_STOP"
                            exit_badge_class = "neutral"
                            exit_summary = "Disciplined stop loss hit. Textbook risk preservation."
                        elif pnl < 0:
                            exit_quality = "STOPPED_OUT"
                            exit_badge_class = "neutral"
                            exit_summary = "Exited on adverse move within acceptable risk."
                        else:
                            exit_quality = "DISCRETIONARY_EXIT"
                            exit_badge_class = "info"
                            exit_summary = "Closed discretionarily."

        # -------------------------------------------------------------
        # 4. Execution Alpha Score Calculation (0 - 100)
        # -------------------------------------------------------------
        alpha_score = 50.0  # Base

        # A. Risk Guardrail (+25 points max)
        if stop_loss is not None and stop_loss > 0:
            alpha_score += 15.0
        else:
            alpha_score -= 15.0

        if target is not None and target > 0:
            alpha_score += 10.0
        else:
            alpha_score -= 5.0

        # B. Exit Quality Impact (+25 points max)
        if exit_quality == "TARGET_ACHIEVED":
            alpha_score += 20.0
        elif exit_quality == "DISCIPLINED_STOP":
            alpha_score += 18.0  # Taking a disciplined stop deserves high marks!
        elif exit_quality == "DISCRETIONARY_PROFIT":
            alpha_score += 12.0
        elif exit_quality == "PREMATURE_EXIT":
            alpha_score += 5.0   # Profitable but flawed discipline
        elif exit_quality == "STOP_VIOLATION":
            alpha_score -= 30.0  # Severe penalty for runaway loss

        # C. Psychology & Notes Logging (+20 points max)
        if trade.notes and len(trade.notes.strip()) >= 20:
            alpha_score += 10.0
        elif trade.notes:
            alpha_score += 5.0

        if trade.emotion_before:
            alpha_score += 5.0
        if trade.emotion_after:
            alpha_score += 5.0

        # D. Strategy Rigor (+10 points max)
        if trade.strategy and trade.strategy.strip():
            alpha_score += 10.0

        alpha_score = max(5, min(100, round(alpha_score)))

        # Letter Grade
        if alpha_score >= 90:
            grade = "A+"
            grade_title = "Elite Execution"
            grade_color = "#10b981"
        elif alpha_score >= 80:
            grade = "A"
            grade_title = "Disciplined Execution"
            grade_color = "#34d399"
        elif alpha_score >= 70:
            grade = "B"
            grade_title = "Solid Setup"
            grade_color = "#38bdf8"
        elif alpha_score >= 55:
            grade = "C"
            grade_title = "Hesitant / Leaky"
            grade_color = "#f59e0b"
        else:
            grade = "D"
            grade_title = "Discipline Breach"
            grade_color = "#ef4444"

        # -------------------------------------------------------------
        # 5. AI Post-Mortem Key Takeaway
        # -------------------------------------------------------------
        takeaway = AiTradeAuditor._generate_takeaway(
            trade=trade,
            exit_quality=exit_quality,
            alpha_score=alpha_score,
            planned_rr=planned_rr,
            realized_r=realized_r,
            pnl=pnl
        )

        return {
            "execution_alpha_score": alpha_score,
            "grade": grade,
            "grade_title": grade_title,
            "grade_color": grade_color,
            "planned_rr": planned_rr,
            "realized_r": realized_r,
            "r_efficiency_pct": r_efficiency_pct,
            "exit_quality": exit_quality,
            "exit_badge_class": exit_badge_class,
            "exit_summary": exit_summary,
            "takeaway": takeaway,
        }

    @staticmethod
    def _generate_takeaway(
        trade,
        exit_quality: str,
        alpha_score: int,
        planned_rr: float,
        realized_r: float,
        pnl: float
    ) -> str:
        symbol = trade.symbol or "Instrument"
        direction = trade.trade_type or "Trade"

        if exit_quality == "TARGET_ACHIEVED":
            return (
                f"Flawless plan execution on {symbol}. You respected your planned target and captured "
                f"+{realized_r}R ({'+$' if pnl >= 0 else '-$'}{abs(pnl):.2f}). Continue letting winning setups reach maturity."
            )

        if exit_quality == "DISCIPLINED_STOP":
            return (
                f"Textbook risk preservation on {symbol}. You accepted the predefined stop at {realized_r}R without "
                f"widening your risk parameter. Losses are the cost of doing business in trading when disciplined."
            )

        if exit_quality == "PREMATURE_EXIT":
            return (
                f"Edge leakage detected on {symbol}. You exited in profit at +{realized_r}R, but significantly before your "
                f"planned {planned_rr}R target. Work on trade management rules (e.g., trailing stop) to combat impatience."
            )

        if exit_quality == "STOP_VIOLATION":
            return (
                f"Critical risk violation on {symbol}. You allowed this loss to run past your initial Stop Loss to {realized_r}R. "
                f"Always use hard broker stop orders to eliminate emotional hope on losing positions."
            )

        if trade.status == "OPEN":
            if not trade.stop_loss:
                return f"Active position on {symbol} lacks a defined Stop Loss! Set your risk ceiling immediately to prevent unexpected drawdowns."
            return f"Active position on {symbol} is monitored. Keep emotion detached and allow your planned rules to govern the exit."

        # Default fallback
        sign = "+$" if pnl >= 0 else "-$"
        return (
            f"Closed {direction} trade on {symbol} with {sign}{abs(pnl):.2f} P/L. "
            f"Review your entry checklist to ensure your trigger was aligned with your edge."
        )

    @classmethod
    def enrich_with_deepseek_audit(cls, trade, audit_data: Dict[str, Any], user=None) -> Dict[str, Any]:
        """
        Enriches post-mortem audit with DeepSeek V4.1 Flash via NVIDIA NIM.
        """
        user_obj = user or getattr(trade, "user", None)
        provider = getattr(user_obj, "ai_provider", None) or "nvidia"
        api_key = ""

        try:
            from flask import current_app
            cfg_provider = current_app.config.get("AI_PROVIDER", "nvidia")
            cfg_nvidia_key = current_app.config.get("NVIDIA_API_KEY", "")
            cfg_nvidia_base_url = current_app.config.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            cfg_gemini_key = current_app.config.get("GEMINI_API_KEY", "")
            cfg_openai_key = current_app.config.get("OPENAI_API_KEY", "")
            cfg_ollama = current_app.config.get("OLLAMA_ENDPOINT", "http://localhost:11434")
            user_model = getattr(user_obj, "ai_model", None) or current_app.config.get("AI_MODEL")
        except Exception:
            cfg_provider = "nvidia"
            cfg_nvidia_key = ""
            cfg_nvidia_base_url = "https://integrate.api.nvidia.com/v1"
            cfg_gemini_key = ""
            cfg_openai_key = ""
            cfg_ollama = "http://localhost:11434"
            user_model = None

        active_provider = provider or cfg_provider
        if active_provider in ["nvidia", "deepseek"]:
            api_key = getattr(user_obj, "nvidia_api_key", "") or cfg_nvidia_key
        elif active_provider == "gemini":
            api_key = getattr(user_obj, "gemini_api_key", "") or cfg_gemini_key
        elif active_provider == "openai":
            api_key = getattr(user_obj, "openai_api_key", "") or cfg_openai_key

        model_name = user_model or "deepseek-ai/deepseek-v4.1-flash"

        if active_provider not in ["offline"] and (api_key or active_provider in ["ollama", "local"]):
            try:
                from services.ai_gateway import AIGateway
                system_prompt = (
                    "You are Aura's Forensic AI Trade Auditor at Tradenza. A trade has completed. "
                    "Provide a crisp, forensic post-mortem breakdown in 3 bulleted sections:\n"
                    "1. 🔬 Execution Precision: Planned vs Realized R:R analysis.\n"
                    "2. 🧠 Behavioral Root Cause: Identify whether fear, greed, FOMO, or strict discipline drove this exit.\n"
                    "3. 💡 Golden Rule for Next Trade: One single uncompromising rule to improve future EV."
                )
                user_msg = (
                    f"FORENSIC TRADE AUDIT:\n"
                    f"- Symbol: {trade.symbol} ({trade.trade_type})\n"
                    f"- Entry: {trade.entry_price} | Exit: {trade.exit_price}\n"
                    f"- Stop Loss: {trade.stop_loss} | Target: {trade.target}\n"
                    f"- Net P/L: ${trade.profit_loss} | Planned R:R: {audit_data.get('planned_rr')}:1 | Realized R: {audit_data.get('realized_r')}R\n"
                    f"- Exit Quality: {audit_data.get('exit_quality')} ({audit_data.get('exit_summary')})\n"
                    f"- Execution Alpha Score: {audit_data.get('execution_alpha_score')}/100 ({audit_data.get('grade')})\n"
                    f"- Emotions: Before: {trade.emotion_before or 'None'} | After: {trade.emotion_after or 'None'}\n"
                    f"- Notes: {trade.notes or 'None'}\n\n"
                    f"Deliver your forensic post-mortem analysis."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ]
                success, reply = AIGateway.generate_chat_response(
                    provider=active_provider,
                    api_key=api_key,
                    messages=messages,
                    model=model_name,
                    ollama_endpoint=cfg_ollama,
                    nvidia_base_url=cfg_nvidia_base_url,
                    timeout_seconds=8
                )
                if success and reply:
                    audit_data["deepseek_forensic_critique"] = reply
                    audit_data["ai_source"] = f"llm_{active_provider}"
                    return audit_data
            except Exception:
                pass

        # Heuristic fallback
        audit_data["deepseek_forensic_critique"] = audit_data.get("takeaway", "")
        audit_data["ai_source"] = "deterministic_heuristics"
        return audit_data
