import unittest
from datetime import datetime, timezone
from core.factory import create_app
from extensions import db
from models.user import User
from models.portfolio import Portfolio
from models.ledger import LedgerTransaction
from models.trade import Trade
from services.auth_service import AuthService
from services.portfolio_service import PortfolioService
from services.trade_service import TradeService


class PortfolioLedgerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-key"
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        _, _ = AuthService.register_user("Ledger User", "ledger@tradenza.test", "SecurePass123!")
        self.user = User.query.filter_by(email="ledger@tradenza.test").first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def test_deposit_records_ledger_transaction(self):
        port = PortfolioService.deposit(self.user, 5000.0, notes="Initial fund wire")
        self.assertEqual(port.total_deposit, 5000.0)
        self.assertEqual(port.current_balance, 5000.0)

        txs = PortfolioService.get_ledger_transactions(self.user)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_type, "DEPOSIT")
        self.assertEqual(txs[0].amount, 5000.0)
        self.assertEqual(txs[0].balance_after, 5000.0)
        self.assertEqual(txs[0].notes, "Initial fund wire")

    def test_withdrawal_records_ledger_transaction(self):
        PortfolioService.deposit(self.user, 10000.0, notes="Deposit")
        port = PortfolioService.withdraw(self.user, 2500.0, notes="Profit payout")

        self.assertEqual(port.total_deposit, 10000.0)
        self.assertEqual(port.total_withdrawal, 2500.0)
        self.assertEqual(port.current_balance, 7500.0)

        txs = PortfolioService.get_ledger_transactions(self.user)
        self.assertEqual(len(txs), 2)
        # Latest first
        self.assertEqual(txs[0].tx_type, "WITHDRAWAL")
        self.assertEqual(txs[0].amount, 2500.0)
        self.assertEqual(txs[0].balance_after, 7500.0)
        self.assertEqual(txs[0].notes, "Profit payout")

    def test_starting_balance_and_trading_roi_isolation(self):
        # Anchor starting balance to 10,000
        port = PortfolioService.set_starting_balance(self.user, 10000.0, notes="Starting account allocation")
        self.assertEqual(port.starting_balance, 10000.0)
        self.assertEqual(port.current_balance, 10000.0)

        # Record a trade with +1,000 profit
        trade = Trade(
            user_id=self.user.id,
            market="Crypto",
            symbol="BTCUSDT",
            trade_type="BUY",
            entry_price=50000.0,
            exit_price=60000.0,
            quantity=0.1,
            profit_loss=1000.0,
            status="CLOSED"
        )
        db.session.add(trade)
        db.session.commit()
        PortfolioService.update_portfolio(self.user)

        refreshed_port = PortfolioService.get_or_create_portfolio(self.user)
        self.assertEqual(refreshed_port.realized_profit, 1000.0)
        self.assertEqual(refreshed_port.current_balance, 11000.0)
        # Growth percentage should be 10.0% (1000 / 10000)
        self.assertEqual(refreshed_port.growth_percentage, 10.0)

        # Deposit $5,000 extra cash
        PortfolioService.deposit(self.user, 5000.0, notes="Additional funds")
        refreshed_port = PortfolioService.get_or_create_portfolio(self.user)

        # Current balance is 10000 (starting) + 5000 (deposit) + 1000 (trading profit) = 16000
        self.assertEqual(refreshed_port.current_balance, 16000.0)
        # Realized trading profit remains 1000, not conflated with 5000 deposit
        self.assertEqual(refreshed_port.realized_profit, 1000.0)
        self.assertEqual(refreshed_port.growth_percentage, 10.0)

        # Ledger transactions should include STARTING_CAPITAL and DEPOSIT
        txs = PortfolioService.get_ledger_transactions(self.user)
        tx_types = [t.tx_type for t in txs]
        self.assertIn("STARTING_CAPITAL", tx_types)
        self.assertIn("DEPOSIT", tx_types)


if __name__ == "__main__":
    unittest.main()
