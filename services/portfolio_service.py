from models.portfolio import Portfolio
from models.trade import Trade
from models.ledger import LedgerTransaction
from extensions import db

from services.equity_service import EquityService


class PortfolioService:

    @staticmethod
    def get_or_create_portfolio(user):
        portfolio = (
            Portfolio.query
            .filter_by(user_id=user.id)
            .first()
        )

        if portfolio is None:
            portfolio = Portfolio(
                user_id=user.id
            )

            db.session.add(portfolio)
            db.session.commit()

        return portfolio

    @staticmethod
    def update_portfolio(user):
        portfolio = PortfolioService.get_or_create_portfolio(user)

        trades = (
            Trade.query
            .filter_by(user_id=user.id)
            .all()
        )

        portfolio.total_trades = len(trades)

        portfolio.winning_trades = sum(
            1
            for trade in trades
            if trade.profit_loss is not None
            and trade.profit_loss > 0
        )

        portfolio.losing_trades = sum(
            1
            for trade in trades
            if trade.profit_loss is not None
            and trade.profit_loss < 0
        )

        portfolio.realized_profit = round(
            sum(
                trade.profit_loss or 0.0
                for trade in trades
            ),
            2
        )

        portfolio.current_balance = round(
            (portfolio.starting_balance or 0.0)
            + (portfolio.total_deposit or 0.0)
            - (portfolio.total_withdrawal or 0.0)
            + (portfolio.realized_profit or 0.0),
            2
        )

        if portfolio.highest_balance == 0:
            portfolio.highest_balance = (
                portfolio.current_balance
            )
            portfolio.lowest_balance = (
                portfolio.current_balance
            )
        else:
            portfolio.highest_balance = max(
                portfolio.highest_balance,
                portfolio.current_balance
            )

            portfolio.lowest_balance = min(
                portfolio.lowest_balance,
                portfolio.current_balance
            )

        db.session.commit()

        EquityService.create_snapshot(user)

        return portfolio

    @staticmethod
    def deposit(user, amount, notes=None):
        portfolio = PortfolioService.get_or_create_portfolio(user)

        portfolio.total_deposit = round((portfolio.total_deposit or 0.0) + amount, 2)
        db.session.commit()

        portfolio = PortfolioService.update_portfolio(user)

        tx = LedgerTransaction(
            user_id=user.id,
            portfolio_id=portfolio.id,
            tx_type="DEPOSIT",
            amount=amount,
            balance_after=portfolio.current_balance,
            notes=notes or f"Deposit of {amount:.2f}"
        )
        db.session.add(tx)
        db.session.commit()

        return portfolio

    @staticmethod
    def withdraw(user, amount, notes=None):
        portfolio = PortfolioService.get_or_create_portfolio(user)

        portfolio.total_withdrawal = round((portfolio.total_withdrawal or 0.0) + amount, 2)
        db.session.commit()

        portfolio = PortfolioService.update_portfolio(user)

        tx = LedgerTransaction(
            user_id=user.id,
            portfolio_id=portfolio.id,
            tx_type="WITHDRAWAL",
            amount=amount,
            balance_after=portfolio.current_balance,
            notes=notes or f"Withdrawal of {amount:.2f}"
        )
        db.session.add(tx)
        db.session.commit()

        return portfolio

    @staticmethod
    def set_starting_balance(user, amount, notes=None):
        portfolio = PortfolioService.get_or_create_portfolio(user)

        portfolio.starting_balance = amount
        db.session.commit()

        portfolio = PortfolioService.update_portfolio(user)

        tx = LedgerTransaction(
            user_id=user.id,
            portfolio_id=portfolio.id,
            tx_type="STARTING_CAPITAL",
            amount=amount,
            balance_after=portfolio.current_balance,
            notes=notes or f"Starting capital set to {amount:.2f}"
        )
        db.session.add(tx)
        db.session.commit()

        return portfolio

    @staticmethod
    def get_ledger_transactions(user, limit=50):
        return (
            LedgerTransaction.query
            .filter_by(user_id=user.id)
            .order_by(LedgerTransaction.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_summary(user):
        return PortfolioService.update_portfolio(user)