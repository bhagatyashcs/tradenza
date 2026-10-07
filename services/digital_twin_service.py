from collections import Counter
from statistics import mean

from models.trade import Trade
from services.twin_simulator import TwinSimulator


class DigitalTwinService:
    """
    Builds a deterministic behavioral representation of a trader.

    Digital Twin does not calculate a second version of Behavior or Genome.
    It consumes the existing intelligence pipeline and adds a higher-level
    representation of how the trader currently behaves.
    """

    def get_twin(self, user, analytics=None):
        if analytics is None:
            analytics = self._get_analytics(user)

        trades = (
            Trade.query
            .filter_by(
                user_id=user.id,
                status="CLOSED"
            )
            .order_by(Trade.created_at.asc())
            .all()
        )

        behavior = analytics.get("behavior") or {}
        genome = analytics.get("genome") or {}
        insights = analytics.get("insights") or {}
        aura = analytics.get("aura") or {}

        return {
            "identity": self._build_identity(
                genome,
                behavior
            ),
            "personality": self._build_personality(
                behavior,
                genome,
                trades
            ),
            "risk_profile": self._build_risk_profile(
                behavior,
                genome,
                trades
            ),
            "decision_profile": self._build_decision_profile(
                behavior,
                trades
            ),
            "strengths": self._extract_strengths(
                genome,
                insights
            ),
            "weaknesses": self._extract_weaknesses(
                genome,
                insights
            ),
            "market_preferences": self._market_preferences(
                trades
            ),
            "strategy_preferences": self._strategy_preferences(
                trades
            ),
            "confidence_pattern": self._confidence_pattern(
                trades
            ),
            "emotional_pattern": self._emotional_pattern(
                trades
            ),
            "discipline_pattern": self._discipline_pattern(
                behavior,
                genome
            ),
            "current_state": self._current_state(
                trades,
                behavior,
                genome
            ),
            "evolution": self._build_evolution(
                trades
            ),
            "aura": aura,
            "simulation": TwinSimulator.simulate(user, trades),
        }

    @staticmethod
    def _get_analytics(user):
        from services.analytics import AnalyticsService

        return AnalyticsService().get_dashboard_data(user)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @staticmethod
    def _build_identity(genome, behavior):

        archetype = (
            genome.get("archetype")
            or behavior.get("archetype")
            or "Developing Trader"
        )

        score = (
            genome.get("overall_score")
            or behavior.get("overall_score")
            or 0
        )

        return {
            "archetype": archetype,
            "quality_score": round(float(score), 2)
        }

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    @staticmethod
    def _build_personality(
        behavior,
        genome,
        trades
    ):

        aggression = DigitalTwinService._score_value(
            behavior,
            genome,
            "aggression"
        )

        discipline = DigitalTwinService._score_value(
            behavior,
            genome,
            "discipline"
        )

        patience = DigitalTwinService._score_value(
            behavior,
            genome,
            "patience"
        )

        if aggression >= 70:
            style = "Aggressive"
        elif aggression >= 45:
            style = "Balanced"
        else:
            style = "Conservative"

        if discipline >= 70:
            discipline_style = "Structured"
        elif discipline >= 45:
            discipline_style = "Developing"
        else:
            discipline_style = "Reactive"

        if patience >= 70:
            patience_style = "Patient"
        elif patience >= 45:
            patience_style = "Moderately Patient"
        else:
            patience_style = "Impatient"

        return {
            "trading_style": style,
            "discipline_style": discipline_style,
            "patience_style": patience_style,
            "aggression_score": aggression,
            "discipline_score": discipline,
            "patience_score": patience,
            "sample_size": len(trades)
        }

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    @staticmethod
    def _build_risk_profile(
        behavior,
        genome,
        trades
    ):

        risk_score = DigitalTwinService._score_value(
            behavior,
            genome,
            "risk_control"
        )

        if risk_score >= 75:
            profile = "Controlled"
        elif risk_score >= 50:
            profile = "Moderate"
        elif risk_score > 0:
            profile = "Elevated"
        else:
            profile = "Unknown"

        average_risk = None

        risks = []

        for trade in trades:

            if (
                trade.stop_loss is not None
                and trade.entry_price is not None
            ):
                distance = abs(
                    trade.entry_price -
                    trade.stop_loss
                )

                if trade.entry_price:
                    risks.append(
                        distance /
                        abs(trade.entry_price) *
                        100
                    )

        if risks:
            average_risk = round(
                mean(risks),
                2
            )

        return {
            "profile": profile,
            "risk_control_score": risk_score,
            "average_stop_distance_percent": average_risk
        }

    # ------------------------------------------------------------------
    # Decision profile
    # ------------------------------------------------------------------

    @staticmethod
    def _build_decision_profile(
        behavior,
        trades
    ):

        confidence = [
            float(trade.confidence)
            for trade in trades
            if trade.confidence is not None
        ]

        emotional_trades = [
            trade
            for trade in trades
            if trade.emotion_before
        ]

        return {
            "average_confidence": (
                round(mean(confidence), 2)
                if confidence
                else None
            ),
            "emotion_tracked_ratio": (
                round(
                    len(emotional_trades) /
                    len(trades) *
                    100,
                    2
                )
                if trades
                else 0
            ),
            "behavior_state": (
                behavior.get("current_state")
                or behavior.get("state")
                or "Unknown"
            )
        }

    # ------------------------------------------------------------------
    # Strengths / weaknesses
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_strengths(
        genome,
        insights
    ):

        strengths = []

        primary = genome.get(
            "primary_strength"
        )

        if primary:
            strengths.append(primary)

        insight_strength = insights.get(
            "primary_strength"
        )

        if (
            insight_strength
            and insight_strength not in strengths
        ):
            strengths.append(
                insight_strength
            )

        genome_strengths = genome.get(
            "strengths"
        )

        if isinstance(genome_strengths, list):

            for strength in genome_strengths:

                if strength not in strengths:
                    strengths.append(strength)

        return strengths

    @staticmethod
    def _extract_weaknesses(
        genome,
        insights
    ):

        weaknesses = []

        primary = genome.get(
            "primary_weakness"
        )

        if primary:
            weaknesses.append(primary)

        insight_weakness = insights.get(
            "primary_weakness"
        )

        if (
            insight_weakness
            and insight_weakness not in weaknesses
        ):
            weaknesses.append(
                insight_weakness
            )

        genome_weaknesses = genome.get(
            "weaknesses"
        )

        if isinstance(genome_weaknesses, list):

            for weakness in genome_weaknesses:

                if weakness not in weaknesses:
                    weaknesses.append(
                        weakness
                    )

        return weaknesses

    # ------------------------------------------------------------------
    # Market preferences
    # ------------------------------------------------------------------

    @staticmethod
    def _market_preferences(trades):

        counter = Counter(
            trade.market
            for trade in trades
            if trade.market
        )

        total = sum(
            counter.values()
        )

        preferences = []

        for market, count in counter.most_common():

            preferences.append({
                "market": market,
                "trades": count,
                "percentage": round(
                    count / total * 100,
                    2
                ) if total else 0
            })

        return preferences

    # ------------------------------------------------------------------
    # Strategy preferences
    # ------------------------------------------------------------------

    @staticmethod
    def _strategy_preferences(trades):

        counter = Counter(
            trade.strategy
            for trade in trades
            if trade.strategy
        )

        total = sum(
            counter.values()
        )

        preferences = []

        for strategy, count in counter.most_common():

            preferences.append({
                "strategy": strategy,
                "trades": count,
                "percentage": round(
                    count / total * 100,
                    2
                ) if total else 0
            })

        return preferences

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_pattern(trades):

        values = [
            float(trade.confidence)
            for trade in trades
            if trade.confidence is not None
        ]

        if not values:
            return {
                "average": None,
                "minimum": None,
                "maximum": None,
                "pattern": "Insufficient data"
            }

        average = mean(values)

        if average >= 8:
            pattern = "High Confidence"
        elif average >= 5:
            pattern = "Moderate Confidence"
        else:
            pattern = "Low Confidence"

        return {
            "average": round(average, 2),
            "minimum": min(values),
            "maximum": max(values),
            "pattern": pattern
        }

    # ------------------------------------------------------------------
    # Emotional pattern
    # ------------------------------------------------------------------

    @staticmethod
    def _emotional_pattern(trades):

        emotions = Counter(
            trade.emotion_before
            for trade in trades
            if trade.emotion_before
        )

        if not emotions:
            return {
                "dominant": None,
                "distribution": {}
            }

        return {
            "dominant": emotions.most_common(1)[0][0],
            "distribution": dict(
                emotions
            )
        }

    # ------------------------------------------------------------------
    # Discipline
    # ------------------------------------------------------------------

    @staticmethod
    def _discipline_pattern(
        behavior,
        genome
    ):

        score = DigitalTwinService._score_value(
            behavior,
            genome,
            "discipline"
        )

        if score >= 80:
            state = "Highly Disciplined"
        elif score >= 60:
            state = "Disciplined"
        elif score >= 40:
            state = "Developing Discipline"
        elif score > 0:
            state = "Reactive"
        else:
            state = "Insufficient Data"

        return {
            "score": score,
            "state": state
        }

    # ------------------------------------------------------------------
    # Current state
    # ------------------------------------------------------------------

    @staticmethod
    def _current_state(
        trades,
        behavior,
        genome
    ):

        if not trades:
            return "No Trading History"

        recent = trades[-5:]

        wins = sum(
            1
            for trade in recent
            if (
                trade.profit_loss is not None
                and trade.profit_loss > 0
            )
        )

        losses = sum(
            1
            for trade in recent
            if (
                trade.profit_loss is not None
                and trade.profit_loss < 0
            )
        )

        if wins > losses:
            state = "Performing Well"
        elif losses > wins:
            state = "Under Pressure"
        else:
            state = "Neutral"

        return state

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------

    @staticmethod
    def _build_evolution(trades):

        if not trades:
            return {
                "trade_count": 0,
                "early_win_rate": None,
                "recent_win_rate": None,
                "direction": "No Data"
            }

        midpoint = max(
            1,
            len(trades) // 2
        )

        early = trades[:midpoint]
        recent = trades[midpoint:]

        def win_rate(items):

            if not items:
                return None

            wins = sum(
                1
                for trade in items
                if (
                    trade.profit_loss is not None
                    and trade.profit_loss > 0
                )
            )

            return round(
                wins / len(items) * 100,
                2
            )

        early_rate = win_rate(early)
        recent_rate = win_rate(recent)

        if (
            early_rate is None
            or recent_rate is None
        ):
            direction = "Insufficient Data"

        elif recent_rate > early_rate + 5:
            direction = "Improving"

        elif recent_rate < early_rate - 5:
            direction = "Declining"

        else:
            direction = "Stable"

        return {
            "trade_count": len(trades),
            "early_win_rate": early_rate,
            "recent_win_rate": recent_rate,
            "direction": direction
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_value(
        behavior,
        genome,
        key
    ):

        value = genome.get(key)

        if value is None:
            value = behavior.get(key)

        try:
            value = float(value)
        except (
            TypeError,
            ValueError
        ):
            return 0.0

        return round(
            max(
                0.0,
                min(100.0, value)
            ),
            2
        )