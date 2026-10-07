from typing import Any, Dict, List, Optional

from extensions import db

from models.trade import Trade
from models.genome import TraderGenome, TraderGenomeHistory
from engines.behavior_engine import BehaviorEngine
from engines.genome_engine import GenomeEngine, TraderGenomeScore
from engines.insight_engine import InsightEngine
from ai.aura import AuraCoach


class AnalyticsService:
    """
    Central intelligence orchestrator for Tradenza.

    Pipeline:

        Trade records
            ↓
        Trade normalization
            ↓
        Behavior Engine
            ↓
        Genome Engine
            ↓
        Insight Engine
            ↓
        Aura Coach
            ↓
        TraderGenome persistence
    """

    def __init__(self) -> None:
        self.behavior_engine = BehaviorEngine()
        self.genome_engine = GenomeEngine(
            behavior_engine=self.behavior_engine
        )
        self.insight_engine = InsightEngine()
        self.aura = AuraCoach()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def refresh_user(
        self,
        user,
        account_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Recalculate the complete intelligence profile for a user.

        This method is intentionally responsible for orchestration only.
        Individual calculations remain inside their respective engines.
        """

        trades = self._get_user_trades(user.id)

        trade_data = [
            self._serialize_trade(trade)
            for trade in trades
        ]

        # --------------------------------------------------------------
        # 1. Behavior
        # --------------------------------------------------------------

        behavior_report = self.behavior_engine.analyze(
            trades=trade_data,
            account_capital=account_capital
        )

        # --------------------------------------------------------------
        # 2. Previous Genome
        # --------------------------------------------------------------

        genome_record = (
            TraderGenome.query
            .filter_by(user_id=user.id)
            .first()
        )

        previous_genome = self._build_previous_genome(
            genome_record
        )

        # --------------------------------------------------------------
        # 3. Genome
        # --------------------------------------------------------------

        genome_score = self.genome_engine.calculate_genome(
            trades=trade_data,
            behavior_report=behavior_report,
            previous_genome=previous_genome,
            account_capital=account_capital
        )

        # --------------------------------------------------------------
        # 4. Insights
        # --------------------------------------------------------------

        insight_report = self.insight_engine.generate_insights(
            trades=trade_data,
            behavior_report=behavior_report,
            genome_score=genome_score
        )

        # --------------------------------------------------------------
        # 5. Aura
        # --------------------------------------------------------------

        trader_name = getattr(
            user,
            "name",
            None
        ) or "Trader"

        aura_response = self.aura.explain_session(
            behavior_report=behavior_report,
            genome_score=genome_score,
            insight_report=insight_report,
            trader_name=trader_name
        )

        # --------------------------------------------------------------
        # 6. Persist Genome
        # --------------------------------------------------------------

        self._save_genome(
            user_id=user.id,
            genome_record=genome_record,
            genome_score=genome_score
        )

        db.session.commit()

        return {
            "behavior": behavior_report,
            "genome": genome_score,
            "insights": insight_report,
            "aura": aura_response,
            "trade_count": len(trade_data)
        }

    def analyze_user(
        self,
        user,
        account_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Public alias for refresh_user().
        """

        return self.refresh_user(
            user=user,
            account_capital=account_capital
        )

    def get_dashboard_data(
        self,
        user,
        account_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Return a dashboard-ready analytics payload.

        Analytics are recalculated through refresh_user() so the returned
        payload always represents the current trade history.
        """

        analytics = self.refresh_user(
            user=user,
            account_capital=account_capital
        )

        behavior = analytics["behavior"]
        genome = analytics["genome"]
        insights = analytics["insights"]
        aura = analytics["aura"]

        return {
            "summary": {
                "total_trades": analytics["trade_count"],
                "discipline_score": round(
                    genome.discipline,
                    1
                ),
                "overall_score": round(
                    genome.overall_score,
                    1
                ),
                "archetype": genome.archetype,
                "primary_strength": (
                    insights.primary_strength
                ),
                "primary_weakness": (
                    insights.primary_weakness
                ),
                "confidence_tier": getattr(genome, "confidence_tier", "INSUFFICIENT_SAMPLE"),
                "confidence_message": getattr(genome, "confidence_message", "Insufficient evidence (< 5 trades logged)."),
            },
            "behavior": behavior.to_dict(),
            "genome": genome.to_dict(),
            "insights": insights.to_dict(),
            "aura": aura
        }

    def get_trade_statistics(
        self,
        user
    ) -> Dict[str, Any]:
        """
        Return basic trade statistics for a user.
        """

        trades = self._get_user_trades(user.id)

        total = len(trades)

        winning_trades = [
            trade
            for trade in trades
            if (trade.profit_loss or 0.0) > 0
        ]

        losing_trades = [
            trade
            for trade in trades
            if (trade.profit_loss or 0.0) < 0
        ]

        net_pnl = sum(
            trade.profit_loss or 0.0
            for trade in trades
        )

        return {
            "total_trades": total,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(
                (
                    len(winning_trades) / total * 100
                )
                if total
                else 0.0,
                2
            ),
            "net_pnl": round(
                net_pnl,
                2
            )
        }

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_trades(
        user_id: int
    ) -> List[Trade]:
        """
        Retrieve all trades for a user in chronological order.
        """

        return (
            Trade.query
            .filter_by(user_id=user_id)
            .order_by(Trade.created_at.asc())
            .all()
        )

    @staticmethod
    def _serialize_trade(
        trade: Trade
    ) -> Dict[str, Any]:
        """
        Convert the database Trade model into the normalized structure
        expected by the intelligence engines.
        """

        created_at = trade.created_at

        return {
            "id": trade.id,
            "user_id": trade.user_id,
            "market": trade.market,
            "symbol": trade.symbol,
            "trade_type": trade.trade_type,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "strategy": trade.strategy,
            "timeframe": trade.timeframe,
            "stop_loss": trade.stop_loss,
            "target": trade.target,
            "emotion": trade.emotion_before,
            "emotion_before": trade.emotion_before,
            "emotion_after": trade.emotion_after,
            "confidence": trade.confidence,
            "notes": trade.notes,
            "pnl": trade.profit_loss,
            "profit_loss": trade.profit_loss,
            "status": trade.status,
            "entry_time": getattr(trade, "entry_time", None) or created_at,
            "exit_time": getattr(trade, "exit_time", None),
            "created_at": created_at,
            "updated_at": trade.updated_at,
            "chart_before": trade.chart_before,
            "chart_after": trade.chart_after,
            "setup_image": trade.setup_image,
            "tags": trade.tags,
            "review_score": trade.review_score,
            "ai_reviewed": trade.ai_reviewed,
            "risk_amount": getattr(trade, "risk_amount", None),
            "risk_percent": getattr(trade, "risk_percent", None),
            "planned_rr": getattr(trade, "planned_rr", None),
            "realized_r": getattr(trade, "realized_r", None),
            "exit_reason": getattr(trade, "exit_reason", None),
            "entry_thesis": getattr(trade, "entry_thesis", None),
            "exit_thesis": getattr(trade, "exit_thesis", None),
        }

    @staticmethod
    def _build_previous_genome(
        genome_record: Optional[TraderGenome]
    ) -> Optional[TraderGenomeScore]:
        """
        Convert the persisted TraderGenome database record into the
        TraderGenomeScore structure expected by GenomeEngine.
        """

        if genome_record is None:
            return None

        return TraderGenomeScore(
            discipline=genome_record.discipline or 50.0,
            patience=genome_record.patience or 50.0,
            consistency=genome_record.consistency or 50.0,
            aggression=genome_record.aggression or 50.0,
            risk_control=genome_record.risk_control or 50.0,
            decision_speed=genome_record.decision_speed or 50.0,
            adaptability=genome_record.adaptability or 50.0,
            confidence=genome_record.confidence or 50.0,
            learning_rate=genome_record.learning_rate or 50.0,
            overall_score=genome_record.overall_score or 50.0,
            archetype=(
                genome_record.archetype
                or "Developing Systematic Trader"
            ),
            dimension_deltas={},
            factor_breakdowns=getattr(genome_record, "factor_breakdowns", {}) or {},
            trade_count=getattr(genome_record, "trade_count", 0) or 0,
            confidence_tier=getattr(genome_record, "confidence_tier", "INSUFFICIENT_SAMPLE") or "INSUFFICIENT_SAMPLE"
        )

    @staticmethod
    def _save_genome(
        user_id: int,
        genome_record: Optional[TraderGenome],
        genome_score: TraderGenomeScore
    ) -> TraderGenome:
        """
        Persist the latest calculated Trader Genome and record a historical snapshot.
        """

        if genome_record is None:
            genome_record = TraderGenome(
                user_id=user_id
            )

            db.session.add(genome_record)

        genome_record.update_from_genome(
            genome_score
        )

        history_snapshot = TraderGenomeHistory(
            user_id=user_id,
            discipline=genome_score.discipline,
            patience=genome_score.patience,
            consistency=genome_score.consistency,
            aggression=genome_score.aggression,
            risk_control=genome_score.risk_control,
            decision_speed=genome_score.decision_speed,
            adaptability=genome_score.adaptability,
            confidence=genome_score.confidence,
            learning_rate=genome_score.learning_rate,
            overall_score=genome_score.overall_score,
            archetype=genome_score.archetype,
            trade_count=getattr(genome_score, "trade_count", 0),
            confidence_tier=getattr(genome_score, "confidence_tier", "INSUFFICIENT_SAMPLE"),
            factor_breakdowns=getattr(genome_score, "factor_breakdowns", {})
        )
        db.session.add(history_snapshot)

        return genome_record