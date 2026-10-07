"""
Aura Tools & Execution Service - Tradenza
Provides deterministic tools and data retrieval functions that can be invoked
during Aura AI coaching sessions: position sizing calculator, live quotes lookup,
trade forensic audit, recent trades, behavioral report, genome metrics,
drawdown / high-water mark, and account risk parameters.
"""

from typing import Any, Dict, List, Optional
from extensions import db
from models.user import User
from models.trade import Trade
from models.portfolio import Portfolio
from models.genome import TraderGenome
from models.equity_history import EquityHistory
from services.market_data_service import TwelveDataService
from services.ai_trade_auditor import AiTradeAuditor
from engines.behavior_engine import BehaviorEngine


class AuraTools:
    """
    Deterministic tools for Aura Coach.
    Prevents LLM math and factual hallucinations by calculating risk, metrics,
    and retrieving structured evidence in pure deterministic Python.
    """

    @staticmethod
    def get_recent_trades(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves recent trades with complete quantitative execution data,
        R-multiples, and theses.
        """
        trades = (
            Trade.query.filter_by(user_id=user_id)
            .order_by(Trade.created_at.desc())
            .limit(limit)
            .all()
        )
        return [t.to_dict() for t in trades]

    @staticmethod
    def get_behavior_report(user_id: int) -> Dict[str, Any]:
        """
        Executes deterministic behavioral pattern analysis on the user's trade history.
        """
        user = db.session.get(User, user_id)
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        capital = portfolio.current_balance if portfolio else None

        trades = (
            Trade.query.filter_by(user_id=user_id)
            .order_by(Trade.created_at.asc())
            .all()
        )
        trade_dicts = [t.to_dict() for t in trades]

        engine = BehaviorEngine()
        report = engine.analyze(trade_dicts, account_capital=capital)
        return report.to_dict()

    @staticmethod
    def get_genome(user_id: int) -> Dict[str, Any]:
        """
        Retrieves the deterministic Trader Genome scores, factor breakdowns,
        and confidence tier.
        """
        genome = TraderGenome.query.filter_by(user_id=user_id).first()
        if not genome:
            return {
                "discipline": 50.0,
                "risk_control": 50.0,
                "patience": 50.0,
                "consistency": 50.0,
                "overall_score": 50.0,
                "archetype": "Developing Systematic Trader",
                "trade_count": 0,
                "confidence_tier": "INSUFFICIENT_SAMPLE",
                "confidence_message": "Insufficient evidence (< 5 trades logged).",
                "factor_breakdowns": {}
            }
        return genome.to_dict()

    @staticmethod
    def get_drawdown(user_id: int) -> Dict[str, Any]:
        """
        Calculates account high-water mark, current liquid equity, drawdown
        dollars, current drawdown percentage, and capital recovery required.
        """
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        user = db.session.get(User, user_id)
        currency = getattr(user, "currency", "$") or "$"

        if not portfolio:
            return {
                "currency": currency,
                "current_balance": 0.0,
                "high_water_mark": 0.0,
                "drawdown_dollars": 0.0,
                "drawdown_percent": 0.0,
                "recovery_percent_needed": 0.0,
                "status": "NORMAL"
            }

        current_balance = portfolio.current_balance or 0.0
        hwm = max(portfolio.highest_balance or 0.0, current_balance, portfolio.starting_balance or 0.0)

        drawdown_dollars = round(max(0.0, hwm - current_balance), 2)
        drawdown_percent = round((drawdown_dollars / hwm * 100), 2) if hwm > 0 else 0.0

        recovery_needed = 0.0
        if current_balance > 0 and drawdown_dollars > 0:
            recovery_needed = round((drawdown_dollars / current_balance * 100), 2)

        # Drawdown risk classification
        if drawdown_percent >= 20.0:
            status = "CRITICAL_DRAWDOWN"
        elif drawdown_percent >= 10.0:
            status = "WARNING_DRAWDOWN"
        elif drawdown_percent >= 5.0:
            status = "ELEVATED_DRAWDOWN"
        else:
            status = "HEALTHY_EQUITY"

        return {
            "currency": currency,
            "current_balance": current_balance,
            "high_water_mark": hwm,
            "lowest_balance": portfolio.lowest_balance or current_balance,
            "drawdown_dollars": drawdown_dollars,
            "drawdown_percent": drawdown_percent,
            "recovery_percent_needed": recovery_needed,
            "status": status
        }

    @staticmethod
    def get_risk_parameters(user_id: int) -> Dict[str, Any]:
        """
        Retrieves user-defined risk envelope, position risk limits, and cooldown status.
        """
        user = db.session.get(User, user_id)
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        currency = getattr(user, "currency", "$") or "$"
        max_risk_pct = getattr(user, "max_risk_percent", 2.0) or 2.0
        daily_loss_limit = getattr(user, "daily_max_loss", 500.0) or 500.0
        current_balance = portfolio.current_balance if portfolio else 0.0

        max_risk_dollars = round(current_balance * (max_risk_pct / 100.0), 2)

        from services.tradebuddy import TradeBuddyService
        cooldown = TradeBuddyService.check_cooldown_status(user) if user else {"in_cooldown": False}

        return {
            "currency": currency,
            "current_balance": current_balance,
            "max_risk_percent": max_risk_pct,
            "max_risk_dollars_per_trade": max_risk_dollars,
            "daily_max_loss_limit": daily_loss_limit,
            "in_cooldown": cooldown.get("in_cooldown", False),
            "cooldown_reason": cooldown.get("message", "Normal trading state"),
            "ai_coaching_style": getattr(user, "ai_coaching_style", "socratic") or "socratic"
        }

    @staticmethod
    def calculate_position_size(
        account_balance: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float
    ) -> Dict[str, Any]:
        """Calculates exact risk-controlled position size."""
        try:
            account_balance = float(account_balance)
            risk_percent = max(0.1, min(10.0, float(risk_percent)))
            entry_price = float(entry_price)
            stop_loss = float(stop_loss)

            if entry_price <= 0 or stop_loss <= 0:
                return {"error": "Entry price and Stop Loss must be greater than zero."}

            stop_distance = abs(entry_price - stop_loss)
            if stop_distance <= 0:
                return {"error": "Stop loss cannot equal entry price."}

            risk_capital = round(account_balance * (risk_percent / 100.0), 2)
            quantity = round(risk_capital / stop_distance, 4)
            total_position_value = round(quantity * entry_price, 2)

            return {
                "account_balance": account_balance,
                "risk_percent": risk_percent,
                "risk_capital": risk_capital,
                "stop_distance": round(stop_distance, 4),
                "recommended_quantity": quantity,
                "position_notional_value": total_position_value,
                "message": (
                    f"At {risk_percent}% risk, max loss is ${risk_capital:.2f}. "
                    f"Recommended size: {quantity} units (Total value: ${total_position_value:.2f})."
                )
            }
        except (ValueError, TypeError, ZeroDivisionError) as e:
            return {"error": f"Invalid sizing parameters: {str(e)}"}

    @staticmethod
    def get_live_market_quote(symbol: str) -> Dict[str, Any]:
        """Fetches live quotes & market data."""
        service = TwelveDataService()
        return service.get_quote(symbol.strip().upper())

    @staticmethod
    def get_trade_forensics(user_id: int, trade_id: int) -> Dict[str, Any]:
        """Runs deep forensic execution audit on a trade."""
        try:
            trade = Trade.query.filter_by(id=trade_id, user_id=user_id).first()
            if not trade:
                return {"error": f"Trade #{trade_id} not found."}
            return AiTradeAuditor.audit_trade(trade)
        except Exception as e:
            return {"error": f"Failed to audit trade #{trade_id}: {str(e)}"}
