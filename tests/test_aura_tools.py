import unittest
from datetime import datetime, timezone
from core.factory import create_app
from extensions import db
from models.user import User
from models.trade import Trade
from models.portfolio import Portfolio
from models.genome import TraderGenome
from services.auth_service import AuthService
from services.portfolio_service import PortfolioService
from ai.aura_tools import AuraTools as AiAuraTools
from services.aura_tools import AuraTools as ServiceAuraTools


class AuraToolsTestCase(unittest.TestCase):

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

        _, _ = AuthService.register_user("Aura User", "aura_tools@tradenza.test", "SecurePass123!")
        self.user = User.query.filter_by(email="aura_tools@tradenza.test").first()
        self.user.max_risk_percent = 1.5
        self.user.daily_max_loss = 400.0
        db.session.commit()

        # Set starting balance and deposit
        PortfolioService.set_starting_balance(self.user, 10000.0)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def test_import_equivalence(self):
        self.assertIs(AiAuraTools, ServiceAuraTools)

    def test_get_risk_parameters(self):
        params = AiAuraTools.get_risk_parameters(self.user.id)
        self.assertEqual(params["max_risk_percent"], 1.5)
        self.assertEqual(params["daily_max_loss_limit"], 400.0)
        self.assertEqual(params["current_balance"], 10000.0)
        self.assertEqual(params["max_risk_dollars_per_trade"], 150.0)
        self.assertFalse(params["in_cooldown"])

    def test_get_drawdown_calculation(self):
        # Initial drawdown with peak = 10,000, balance = 10,000 -> 0%
        dd = AiAuraTools.get_drawdown(self.user.id)
        self.assertEqual(dd["drawdown_dollars"], 0.0)
        self.assertEqual(dd["drawdown_percent"], 0.0)
        self.assertEqual(dd["status"], "HEALTHY_EQUITY")

        # Now simulate a loss
        trade = Trade(
            user_id=self.user.id,
            market="Forex",
            symbol="EURUSD",
            trade_type="BUY",
            entry_price=1.1000,
            exit_price=1.0900,
            quantity=1000.0,
            profit_loss=-1000.0,
            status="CLOSED"
        )
        db.session.add(trade)
        db.session.commit()
        PortfolioService.update_portfolio(self.user)

        # Current balance is 9,000, peak was 10,000 -> DD is $1,000 (10.0%)
        dd_after = AiAuraTools.get_drawdown(self.user.id)
        self.assertEqual(dd_after["current_balance"], 9000.0)
        self.assertEqual(dd_after["high_water_mark"], 10000.0)
        self.assertEqual(dd_after["drawdown_dollars"], 1000.0)
        self.assertEqual(dd_after["drawdown_percent"], 10.0)
        self.assertEqual(dd_after["status"], "WARNING_DRAWDOWN")
        # Recovery needed to get back to 10k: 1000 / 9000 = 11.11%
        self.assertEqual(dd_after["recovery_percent_needed"], 11.11)

    def test_get_recent_trades_and_behavior(self):
        trade = Trade(
            user_id=self.user.id,
            market="Crypto",
            symbol="SOLUSDT",
            trade_type="BUY",
            entry_price=150.0,
            exit_price=165.0,
            quantity=10.0,
            profit_loss=150.0,
            planned_rr=2.5,
            realized_r=2.5,
            status="CLOSED"
        )
        db.session.add(trade)
        db.session.commit()

        recent = AiAuraTools.get_recent_trades(self.user.id, limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["symbol"], "SOLUSDT")
        self.assertEqual(recent[0]["planned_rr"], 2.5)
        self.assertEqual(recent[0]["realized_r"], 2.5)

        behavior = AiAuraTools.get_behavior_report(self.user.id)
        self.assertIn("patterns_detected", behavior)

    def test_calculate_position_size(self):
        sizing = AiAuraTools.calculate_position_size(
            account_balance=10000.0,
            risk_percent=2.0,     # $200 risk
            entry_price=100.0,
            stop_loss=95.0        # $5 distance
        )
        self.assertNotIn("error", sizing)
        self.assertEqual(sizing["risk_capital"], 200.0)
        self.assertEqual(sizing["stop_distance"], 5.0)
        self.assertEqual(sizing["recommended_quantity"], 40.0)


if __name__ == "__main__":
    unittest.main()
