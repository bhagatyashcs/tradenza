"""
TradeBuddy Pre-Trade Assistant & Risk Guardrail Module - Tradenza
Provides proactive pre-flight risk calculations, R:R analysis,
and revenge-trading cooldown warnings before trades are logged.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from models.trade import Trade
from services.portfolio_service import PortfolioService


class TradeBuddyService:
    """Pre-trade intelligence and risk control advisor."""

    DEFAULT_MAX_RISK_PERCENT = 2.0  # Max 2% capital per trade
    DEFAULT_MIN_RR_RATIO = 1.0      # Minimum 1:1 Risk-to-Reward
    REVENGE_COOLDOWN_MINUTES = 20   # 20-minute post-loss reset window

    @classmethod
    def calculate_risk_metrics(
        cls,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        target: Optional[float],
        quantity: Optional[float] = 1.0,
        account_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes planned risk, potential reward, and Risk-to-Reward ratio.
        """
        qty = quantity or 1.0

        metrics: Dict[str, Any] = {
            "risk_dollar": None,
            "reward_dollar": None,
            "rr_ratio": None,
            "risk_percent": None,
            "is_rr_violation": False,
            "is_capital_violation": False,
            "recommended_qty_2pct": None,
            "status": "incomplete"
        }

        if entry_price is None or stop_loss is None or entry_price <= 0:
            return metrics

        # Calculate Risk
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            return metrics

        total_risk = round(risk_per_unit * qty, 2)
        metrics["risk_dollar"] = total_risk

        # Calculate Capital Risk %
        if account_balance and account_balance > 0:
            risk_pct = round((total_risk / account_balance) * 100.0, 2)
            metrics["risk_percent"] = risk_pct
            metrics["is_capital_violation"] = risk_pct > cls.DEFAULT_MAX_RISK_PERCENT

            # Recommended position size to risk exactly 2% of account
            allowed_risk = account_balance * (cls.DEFAULT_MAX_RISK_PERCENT / 100.0)
            metrics["recommended_qty_2pct"] = round(allowed_risk / risk_per_unit, 2)

        # Calculate Potential Reward & R:R
        if target is not None and target > 0:
            reward_per_unit = abs(target - entry_price)
            total_reward = round(reward_per_unit * qty, 2)
            metrics["reward_dollar"] = total_reward

            if risk_per_unit > 0:
                rr = round(reward_per_unit / risk_per_unit, 2)
                metrics["rr_ratio"] = rr
                metrics["is_rr_violation"] = rr < cls.DEFAULT_MIN_RR_RATIO

        metrics["status"] = "calculated"
        return metrics

    @classmethod
    def check_cooldown_status(cls, user) -> Dict[str, Any]:
        """
        Checks whether the trader closed a losing trade within the past
        cooldown window (20 minutes). If so, returns an active cooldown warning.
        """
        if not user or not user.is_authenticated:
            return {"in_cooldown": False}

        # Find the latest closed trade
        latest_closed = (
            Trade.query
            .filter_by(user_id=user.id, status="CLOSED")
            .order_by(Trade.updated_at.desc())
            .first()
        )

        if not latest_closed:
            return {"in_cooldown": False}

        # Check if latest closed trade was a loss
        pnl = latest_closed.profit_loss or 0.0
        if pnl >= 0:
            return {"in_cooldown": False}

        exit_time = latest_closed.exit_time or latest_closed.updated_at
        if not exit_time:
            return {"in_cooldown": False}

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed = now - exit_time

        # If trade was closed within the cooldown window
        cooldown_delta = timedelta(minutes=cls.REVENGE_COOLDOWN_MINUTES)
        if timedelta(seconds=0) <= elapsed <= cooldown_delta:
            mins_elapsed = max(1, int(elapsed.total_seconds() // 60))
            mins_remaining = cls.REVENGE_COOLDOWN_MINUTES - mins_elapsed

            return {
                "in_cooldown": True,
                "trigger_trade_id": latest_closed.id,
                "trigger_symbol": latest_closed.symbol,
                "loss_amount": round(abs(pnl), 2),
                "minutes_elapsed": mins_elapsed,
                "minutes_remaining": max(1, mins_remaining),
                "message": (
                    f"Active Cooldown: You closed a loss on {latest_closed.symbol} (-${abs(pnl):.2f}) "
                    f"{mins_elapsed}m ago. Aura suggests a {mins_remaining}m reset break before entering "
                    f"another position to prevent emotional revenge trading."
                )
            }

        return {"in_cooldown": False}

    @classmethod
    def get_preflight_check(
        cls,
        user,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        target: Optional[float],
        quantity: Optional[float] = 1.0
    ) -> Dict[str, Any]:
        """
        Comprehensive pre-trade assessment combining cooldown and risk metrics.
        """
        portfolio = PortfolioService.get_or_create_portfolio(user)
        balance = portfolio.current_balance or portfolio.starting_balance or 0.0

        risk_metrics = cls.calculate_risk_metrics(
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            quantity=quantity,
            account_balance=balance
        )

        cooldown = cls.check_cooldown_status(user)

        return {
            "account_balance": balance,
            "risk_metrics": risk_metrics,
            "cooldown": cooldown
        }
