"""
Digital Twin "Leak Eliminator" Counterfactual Simulator - Tradenza
Simulates alternate-universe performance curves answering:
"What would my account look like if I eliminated tilt, respected stops, and let targets run?"
"""

from datetime import timedelta
from typing import Any, Dict, List, Optional
from services.ai_trade_auditor import AiTradeAuditor


class TwinSimulator:
    """
    Forensic Counterfactual Simulation Engine.
    Quantifies the exact dollar cost of psychological and rule execution leaks.
    """

    TILT_EMOTIONS = {"revenge", "frustrated", "angry", "furious", "tilt", "anxious", "fear"}

    @classmethod
    def simulate(cls, user, trades: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Runs counterfactual simulations over closed trades.
        """
        if trades is None:
            from models.trade import Trade
            trades = (
                Trade.query.filter_by(user_id=user.id, status="CLOSED")
                .order_by(Trade.created_at.asc())
                .all()
            )

        if not trades:
            return {
                "has_data": False,
                "trade_count": 0,
                "actual_pnl": 0.0,
                "potential_pnl": 0.0,
                "total_leaked_capital": 0.0,
                "tilt_leak_cost": 0.0,
                "stop_leak_cost": 0.0,
                "premature_exit_cost": 0.0,
                "primary_leak": "No closed trades recorded yet.",
                "actionable_rule": "Log and close your first trade to activate your Counterfactual Twin.",
                "curves": {
                    "actual": [],
                    "tilt_free": [],
                    "disciplined": [],
                }
            }

        actual_pnls = [float(t.profit_loss or 0.0) for t in trades]
        actual_total_pnl = sum(actual_pnls)

        # -------------------------------------------------------------
        # 1. Identify Leaks per Trade
        # -------------------------------------------------------------
        tilt_trade_ids = set()
        stop_leak_dollars = 0.0
        premature_dollars = 0.0
        tilt_leak_dollars = 0.0

        for i, t in enumerate(trades):
            pnl = float(t.profit_loss or 0.0)
            entry = float(t.entry_price or 0.0)
            exit_p = float(t.exit_price or 0.0) if t.exit_price is not None else None
            sl = float(t.stop_loss or 0.0) if t.stop_loss else None
            target = float(t.target or 0.0) if t.target else None
            qty = abs(float(t.quantity or 0.0))
            is_buy = (t.trade_type or "BUY").upper() == "BUY"

            # Check Tilt Trigger:
            # 1. Emotion tag
            emo_before = (t.emotion_before or "").lower()
            emo_after = (t.emotion_after or "").lower()
            is_tilt_emotion = any(e in emo_before or e in emo_after for e in cls.TILT_EMOTIONS)

            # 2. Taken quickly after a loss (< 15 mins)
            is_quick_revenge = False
            if i > 0:
                prev = trades[i - 1]
                prev_pnl = float(prev.profit_loss or 0.0)
                if prev_pnl < 0 and prev.exit_time and t.created_at:
                    if (t.created_at - prev.exit_time) <= timedelta(minutes=15):
                        is_quick_revenge = True

            if (is_tilt_emotion or is_quick_revenge) and pnl < 0:
                tilt_trade_ids.add(t.id)
                tilt_leak_dollars += abs(pnl)

            # Check Stop Loss Runaway Violation:
            if sl and entry and exit_p and pnl < 0:
                planned_loss_per_unit = abs(entry - sl)
                actual_loss_per_unit = (entry - exit_p) if is_buy else (exit_p - entry)
                if actual_loss_per_unit > (1.10 * planned_loss_per_unit):
                    excess_loss = (actual_loss_per_unit - planned_loss_per_unit) * qty
                    if excess_loss > 0:
                        stop_leak_dollars += excess_loss

            # Check Premature Profit Exit:
            if target and entry and exit_p and pnl > 0:
                target_dist = abs(target - entry)
                captured_dist = (exit_p - entry) if is_buy else (entry - exit_p)
                if captured_dist < (0.60 * target_dist):
                    left_on_table = (target_dist - captured_dist) * qty
                    if left_on_table > 0:
                        premature_dollars += left_on_table

        # -------------------------------------------------------------
        # 2. Build Counterfactual Performance Curves
        # -------------------------------------------------------------
        actual_running = []
        tilt_free_running = []
        disciplined_running = []

        curr_actual = 0.0
        curr_tilt_free = 0.0
        curr_disciplined = 0.0

        for t in trades:
            pnl = float(t.profit_loss or 0.0)
            curr_actual += pnl
            actual_running.append(round(curr_actual, 2))

            # Tilt-Free curve skips tilt-induced losing trades
            if t.id not in tilt_trade_ids:
                curr_tilt_free += pnl
            tilt_free_running.append(round(curr_tilt_free, 2))

            # Disciplined curve adjusts stop violations & premature exits
            adj_pnl = pnl
            if t.id in tilt_trade_ids:
                # Tilt trade eliminated
                adj_pnl = 0.0
            else:
                sl = float(t.stop_loss or 0.0) if t.stop_loss else None
                entry = float(t.entry_price or 0.0)
                exit_p = float(t.exit_price or 0.0) if t.exit_price is not None else None
                target = float(t.target or 0.0) if t.target else None
                qty = abs(float(t.quantity or 0.0))
                is_buy = (t.trade_type or "BUY").upper() == "BUY"

                if sl and entry and exit_p and pnl < 0:
                    planned_loss = abs(entry - sl) * qty
                    if abs(pnl) > (1.10 * planned_loss):
                        adj_pnl = -planned_loss

                if target and entry and exit_p and pnl > 0:
                    target_dist = abs(target - entry)
                    captured_dist = (exit_p - entry) if is_buy else (entry - exit_p)
                    if captured_dist < (0.60 * target_dist):
                        # Gained 75% of full target with patient trailing stop
                        adj_pnl = (0.75 * target_dist) * qty

            curr_disciplined += adj_pnl
            disciplined_running.append(round(curr_disciplined, 2))

        # -------------------------------------------------------------
        # 3. Aggregate Dollar Leaks & Primary Culprit
        # -------------------------------------------------------------
        total_leaked = tilt_leak_dollars + stop_leak_dollars + premature_dollars
        potential_pnl = round(actual_total_pnl + total_leaked, 2)

        # Determine Primary Leak
        leak_candidates = [
            ("Tilt / Revenge Trades", tilt_leak_dollars, "Enforce a mandatory 15-minute cooldown timer after every loss."),
            ("Stop Loss Violations", stop_leak_dollars, "Automate hard broker stop loss orders immediately upon entry."),
            ("Premature Profit Exits", premature_dollars, "Use a structured trailing stop to avoid exiting winning trades in fear."),
        ]
        leak_candidates.sort(key=lambda x: x[1], reverse=True)

        if total_leaked > 0 and leak_candidates[0][1] > 0:
            top_leak_name, top_leak_cost, top_leak_rule = leak_candidates[0]
            primary_leak = f"{top_leak_name} cost you ${top_leak_cost:.2f}"
            actionable_rule = top_leak_rule
        else:
            primary_leak = "No significant execution leaks detected across recorded trades."
            actionable_rule = "Maintain your current disciplined execution and risk guardrails."

        return {
            "has_data": True,
            "trade_count": len(trades),
            "actual_pnl": round(actual_total_pnl, 2),
            "potential_pnl": potential_pnl,
            "total_leaked_capital": round(total_leaked, 2),
            "tilt_leak_cost": round(tilt_leak_dollars, 2),
            "stop_leak_cost": round(stop_leak_dollars, 2),
            "premature_exit_cost": round(premature_dollars, 2),
            "primary_leak": primary_leak,
            "actionable_rule": actionable_rule,
            "tilt_trades_count": len(tilt_trade_ids),
            "curves": {
                "actual": actual_running,
                "tilt_free": tilt_free_running,
                "disciplined": disciplined_running,
            }
        }
