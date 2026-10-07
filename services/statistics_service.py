from collections import Counter

from models.trade import Trade


class StatisticsService:

    @staticmethod
    def get_dashboard_stats(user):

        trades = Trade.query.filter_by(
            user_id=user.id
        ).all()

        total_trades = len(trades)

        open_trades = [
            trade for trade in trades
            if trade.status == "OPEN"
        ]

        closed_trades = [
            trade for trade in trades
            if trade.status == "CLOSED"
        ]

        winning_trades = [
            trade for trade in closed_trades
            if trade.profit_loss is not None
            and trade.profit_loss > 0
        ]

        losing_trades = [
            trade for trade in closed_trades
            if trade.profit_loss is not None
            and trade.profit_loss < 0
        ]

        net_profit = sum(
            trade.profit_loss or 0
            for trade in closed_trades
        )

        win_rate = 0

        if closed_trades:

            win_rate = round(
                (
                    len(winning_trades)
                    /
                    len(closed_trades)
                ) * 100,
                2
            )

        average_win = 0

        if winning_trades:

            average_win = round(

                sum(
                    trade.profit_loss
                    for trade in winning_trades
                )

                /

                len(winning_trades),

                2

            )

        average_loss = 0

        if losing_trades:

            average_loss = round(

                sum(
                    trade.profit_loss
                    for trade in losing_trades
                )

                /

                len(losing_trades),

                2

            )

        largest_win = 0

        if winning_trades:

            largest_win = max(
                trade.profit_loss
                for trade in winning_trades
            )

        largest_loss = 0

        if losing_trades:

            largest_loss = min(
                trade.profit_loss
                for trade in losing_trades
            )

        gross_profit = sum(
            trade.profit_loss
            for trade in winning_trades
        )

        gross_loss = abs(

            sum(
                trade.profit_loss
                for trade in losing_trades
            )

        )

        if gross_loss:

            profit_factor = round(
                gross_profit / gross_loss,
                2
            )

        else:

            profit_factor = gross_profit

        market_counter = Counter(
            trade.market
            for trade in trades
            if trade.market
        )

        strategy_counter = Counter(
            trade.strategy
            for trade in trades
            if trade.strategy
        )

        best_market = "-"

        if market_counter:

            best_market = market_counter.most_common(1)[0][0]

        best_strategy = "-"

        if strategy_counter:

            best_strategy = strategy_counter.most_common(1)[0][0]

        return {

            "total_trades": total_trades,

            "open_trades": len(open_trades),

            "closed_trades": len(closed_trades),

            "winning_trades": len(winning_trades),

            "losing_trades": len(losing_trades),

            "net_profit": round(
                net_profit,
                2
            ),

            "win_rate": win_rate,

            "average_win": average_win,

            "average_loss": average_loss,

            "largest_win": largest_win,

            "largest_loss": largest_loss,

            "profit_factor": profit_factor,

            "best_market": best_market,

            "best_strategy": best_strategy

        }