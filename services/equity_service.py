from datetime import date

from extensions import db
from models.equity_history import EquityHistory
from models.portfolio import Portfolio


class EquityService:

    @staticmethod
    def create_snapshot(user):

        portfolio = Portfolio.query.filter_by(
            user_id=user.id
        ).first()

        if portfolio is None:
            return None

        today = date.today()

        snapshot = (
            EquityHistory.query
            .filter(
                EquityHistory.user_id == user.id,
                db.func.date(
                    EquityHistory.created_at
                ) == today
            )
            .first()
        )

        if snapshot is None:

            snapshot = EquityHistory(

                user_id=user.id,

                portfolio_id=portfolio.id,

                balance=portfolio.current_balance,

                realized_profit=portfolio.realized_profit,

                unrealized_profit=portfolio.unrealized_profit,

                daily_profit=portfolio.realized_profit,

                total_trades=portfolio.total_trades,

                winning_trades=portfolio.winning_trades,

                losing_trades=portfolio.losing_trades,

                win_rate=portfolio.win_rate

            )

            db.session.add(snapshot)

        else:

            snapshot.balance = portfolio.current_balance

            snapshot.realized_profit = (
                portfolio.realized_profit
            )

            snapshot.unrealized_profit = (
                portfolio.unrealized_profit
            )

            snapshot.daily_profit = (
                portfolio.realized_profit
            )

            snapshot.total_trades = (
                portfolio.total_trades
            )

            snapshot.winning_trades = (
                portfolio.winning_trades
            )

            snapshot.losing_trades = (
                portfolio.losing_trades
            )

            snapshot.win_rate = (
                portfolio.win_rate
            )

        db.session.commit()

        return snapshot

    @staticmethod
    def get_history(user):

        return (

            EquityHistory.query

            .filter_by(
                user_id=user.id
            )

            .order_by(
                EquityHistory.created_at.asc()
            )

            .all()

        )

    @staticmethod
    def get_latest_snapshot(user):

        return (

            EquityHistory.query

            .filter_by(
                user_id=user.id
            )

            .order_by(
                EquityHistory.created_at.desc()
            )

            .first()

        )