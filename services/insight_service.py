from collections import Counter

from models.trade import Trade


class InsightService:

    @staticmethod
    def generate_insights(user):

        trades = Trade.query.filter_by(
            user_id=user.id,
            status="CLOSED"
        ).all()

        insights = []

        if len(trades) < 5:

            insights.append(
                "Complete at least 5 trades to unlock advanced insights."
            )

            return insights

        # --------------------------
        # Win Rate
        # --------------------------

        winners = [
            trade for trade in trades
            if trade.profit_loss
            and trade.profit_loss > 0
        ]

        win_rate = round(

            len(winners) /
            len(trades) * 100,

            2

        )

        insights.append(

            f"Your current win rate is {win_rate}%."

        )

        # --------------------------
        # Best Market
        # --------------------------

        market_counter = Counter(
            trade.market
            for trade in trades
        )

        if market_counter:

            market = market_counter.most_common(1)[0][0]

            insights.append(

                f"You trade {market} most frequently."

            )

        # --------------------------
        # Best Strategy
        # --------------------------

        strategy_counter = Counter(
            trade.strategy
            for trade in trades
            if trade.strategy
        )

        if strategy_counter:

            strategy = strategy_counter.most_common(1)[0][0]

            insights.append(

                f'Your most used strategy is "{strategy}".'

            )

        # --------------------------
        # Winning Streak
        # --------------------------

        streak = 0
        best_streak = 0

        for trade in trades:

            if trade.profit_loss and trade.profit_loss > 0:

                streak += 1

                best_streak = max(
                    best_streak,
                    streak
                )

            else:

                streak = 0

        insights.append(

            f"Longest winning streak: {best_streak} trades."

        )

        # --------------------------
        # Average Confidence
        # --------------------------

        confidence = [

            trade.confidence

            for trade in trades

            if trade.confidence

        ]

        if confidence:

            avg = round(

                sum(confidence) /
                len(confidence),

                1

            )

            insights.append(

                f"Average confidence before trading: {avg}/10."

            )

        # --------------------------
        # Psychology
        # --------------------------

        emotions = Counter(

            trade.emotion_before

            for trade in trades

            if trade.emotion_before

        )

        if emotions:

            emotion = emotions.most_common(1)[0][0]

            insights.append(

                f"Your most common emotion before entering is {emotion}."

            )

        return insights