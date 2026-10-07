"""
Trader Episodic Memory - Tradenza
Retrieves and analyzes past concrete trade episodes taken by the user.
Binds current setup to the trader's personal execution track record.
"""

from typing import Any, Dict, List, Optional
from models.trade import Trade


class EpisodicMemory:
    """
    Manages episodic memory of user's past real trading experiences.
    """

    @staticmethod
    def get_user_setup_episodes(
        user,
        setup_type: str = "Breakout",
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves user's personal historical trades matching this setup type or symbol.
        Computes the trader's personal execution metrics for this setup.
        """
        if not user or not getattr(user, "id", None):
            return {
                "total_user_episodes": 0,
                "user_setup_win_rate": 0.0,
                "user_setup_net_pnl": 0.0,
                "sample_episodes": [],
                "personal_verdict": f"No previous recorded {setup_type} trades in your journal yet."
            }

        query = Trade.query.filter_by(user_id=user.id, status="CLOSED")

        if setup_type:
            query = query.filter(Trade.strategy.ilike(f"%{setup_type}%"))

        trades = query.order_by(Trade.created_at.desc()).all()

        if not trades:
            # Fallback to all closed trades by this user if setup-specific trades are sparse
            all_trades = Trade.query.filter_by(user_id=user.id, status="CLOSED").all()
            if not all_trades:
                return {
                    "total_user_episodes": 0,
                    "user_setup_win_rate": 0.0,
                    "user_setup_net_pnl": 0.0,
                    "sample_episodes": [],
                    "personal_verdict": f"No previous recorded {setup_type} trades in your journal yet."
                }
            trades = all_trades[:6]

        wins = [t for t in trades if (t.profit_loss or 0) > 0]
        losses = [t for t in trades if (t.profit_loss or 0) < 0]
        tot = len(trades)

        win_rate = round((len(wins) / tot) * 100.0, 1) if tot > 0 else 0.0
        net_pnl = round(sum((t.profit_loss or 0.0) for t in trades), 2)

        # Detect personal execution tendency
        premature_cuts = 0
        oversized = 0
        for t in trades:
            if t.target and t.entry_price and t.exit_price:
                target_dist = abs(t.target - t.entry_price)
                actual_gain = abs(t.exit_price - t.entry_price)
                if (t.profit_loss or 0) > 0 and actual_gain < (target_dist * 0.6):
                    premature_cuts += 1

        sample_cards = []
        for t in trades[:4]:
            curr = getattr(user, "currency", "$") or "$"
            pnl_val = f"+{curr}{t.profit_loss:.2f}" if (t.profit_loss or 0) >= 0 else f"-{curr}{abs(t.profit_loss or 0):.2f}"
            sample_cards.append({
                "trade_id": t.id,
                "symbol": t.symbol,
                "type": t.trade_type,
                "pnl": pnl_val,
                "emotion": t.emotion_after or t.emotion_before or "Neutral",
                "notes": (t.notes or "No notes")[:60]
            })

        verdict_notes = []
        if premature_cuts >= 2:
            verdict_notes.append(f"In {premature_cuts} of your recent trades, you cut winning setups prematurely before full target.")
        if win_rate < 50.0 and tot >= 3:
            verdict_notes.append(f"Your historical win rate on {setup_type} ({win_rate}%) is below break-even threshold.")

        return {
            "total_user_episodes": tot,
            "user_setup_win_rate": win_rate,
            "user_setup_net_pnl": net_pnl,
            "premature_exit_count": premature_cuts,
            "sample_episodes": sample_cards,
            "personal_tendency_flags": verdict_notes,
            "personal_verdict": " | ".join(verdict_notes) if verdict_notes else "Clean personal execution history on this setup."
        }
