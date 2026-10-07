import io
import unittest
from datetime import datetime, timezone

try:
    from core.factory import create_app
    from extensions import db
    from models.user import User
    from models.trade import Trade
    from models.portfolio import Portfolio
    from services.auth_service import AuthService
    from services.portfolio_service import PortfolioService
    from utils.csv_import import parse_trades_csv
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@unittest.skipUnless(HAS_FLASK, "Flask dependencies required")
class FeaturesRoadmapTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            AuthService.register_user("Roadmap User", "roadmap@example.com", "mypassword123")
            self.user = User.query.filter_by(email="roadmap@example.com").first()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _login(self):
        return self.client.post("/login", data={
            "email": "roadmap@example.com",
            "password": "mypassword123"
        }, follow_redirects=True)

    def test_settings_update_preferences(self):
        self._login()

        # Update currency to INR, risk 1.5%, daily loss 300
        res = self.client.post("/settings/", data={
            "action": "preferences",
            "name": "Roadmap Pro Trader",
            "currency": "₹",
            "max_risk_percent": "1.5",
            "daily_max_loss": "300.0",
            "starting_balance": "25000.0"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            self.assertEqual(u.name, "Roadmap Pro Trader")
            self.assertEqual(u.currency, "₹")
            self.assertEqual(u.max_risk_percent, 1.5)
            self.assertEqual(u.daily_max_loss, 300.0)

            port = Portfolio.query.filter_by(user_id=u.id).first()
            self.assertEqual(port.starting_balance, 25000.0)

    def test_portfolio_ledger_and_transactions(self):
        self._login()

        # 1. Get Portfolio page
        res = self.client.get("/portfolio/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Portfolio & Capital Ledger", res.data)

        # 2. Deposit 5,000
        res = self.client.post("/portfolio/transaction", data={
            "tx_type": "deposit",
            "amount": "5000"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            port = PortfolioService.get_or_create_portfolio(u)
            self.assertEqual(port.total_deposit, 5000.0)
            self.assertEqual(port.current_balance, 5000.0)

        # 3. Withdraw 2,000
        res = self.client.post("/portfolio/transaction", data={
            "tx_type": "withdrawal",
            "amount": "2000"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            port = PortfolioService.get_or_create_portfolio(u)
            self.assertEqual(port.total_withdrawal, 2000.0)
            self.assertEqual(port.current_balance, 3000.0)

        # 4. Over-withdrawal guard
        res = self.client.post("/portfolio/transaction", data={
            "tx_type": "withdrawal",
            "amount": "999999"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"exceeds available balance", res.data)

        # 5. Reset starting equity
        res = self.client.post("/portfolio/transaction", data={
            "tx_type": "reset_balance",
            "amount": "50000"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            port = PortfolioService.get_or_create_portfolio(u)
            self.assertEqual(port.starting_balance, 50000.0)
            self.assertEqual(port.current_balance, 50000.0)

    def test_learn_playbook_route(self):
        self._login()
        res = self.client.get("/learn/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Trader Playbook", res.data)
        self.assertIn(b"The 5 Golden Rules of Capital Preservation", res.data)
        self.assertIn(b"Strategy Playbook", res.data)

    def test_analytics_dashboard_metrics(self):
        self._login()

        # Seed closed trades with diverse strategies
        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            t1 = Trade(
                user_id=u.id,
                market="Stocks",
                symbol="NVDA",
                trade_type="BUY",
                entry_price=100.0,
                exit_price=120.0,
                quantity=10.0,
                strategy="Breakout",
                status="CLOSED",
                profit_loss=200.0,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            t2 = Trade(
                user_id=u.id,
                market="Crypto",
                symbol="BTCUSDT",
                trade_type="BUY",
                entry_price=60000.0,
                exit_price=58000.0,
                quantity=0.1,
                strategy="Pullback",
                status="CLOSED",
                profit_loss=-200.0,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            t3 = Trade(
                user_id=u.id,
                market="Stocks",
                symbol="AAPL",
                trade_type="BUY",
                entry_price=150.0,
                exit_price=165.0,
                quantity=10.0,
                strategy="Breakout",
                status="CLOSED",
                profit_loss=150.0,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.session.add_all([t1, t2, t3])
            db.session.commit()

        res = self.client.get("/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Strategy Edge Matrix", res.data)
        self.assertIn(b"Breakout", res.data)
        self.assertIn(b"Pullback", res.data)

    def test_parse_trades_csv_standard_and_alias(self):
        csv_data = """symbol,market,trade_type,entry_price,exit_price,quantity,strategy,profit_loss,status
AAPL,Stocks,BUY,150.0,160.0,10,Breakout,100.0,CLOSED
BTCUSDT,Crypto,BUY,60000,59000,0.5,Trend Following,-500.0,CLOSED
MSFT,Stocks,BUY,400.0,,,5,Pullback,,OPEN
"""
        stream = io.BytesIO(csv_data.encode("utf-8"))
        trades, errors = parse_trades_csv(stream)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(trades), 3)

        # First trade
        self.assertEqual(trades[0]["symbol"], "AAPL")
        self.assertEqual(trades[0]["market"], "Stocks")
        self.assertEqual(trades[0]["trade_type"], "BUY")
        self.assertEqual(trades[0]["entry_price"], 150.0)
        self.assertEqual(trades[0]["exit_price"], 160.0)
        self.assertEqual(trades[0]["quantity"], 10.0)
        self.assertEqual(trades[0]["profit_loss"], 100.0)
        self.assertEqual(trades[0]["status"], "CLOSED")

        # Third trade is OPEN
        self.assertEqual(trades[2]["symbol"], "MSFT")
        self.assertEqual(trades[2]["status"], "OPEN")
        self.assertIsNone(trades[2]["exit_price"])

    def test_parse_trades_csv_broker_header_aliases(self):
        # Testing Zerodha/Groww style column aliases
        broker_csv = """tradingsymbol,segment,type,price,exit_price,quantity,pnl
RELIANCE,Stocks,BUY,2500,2600,10,1000
TCS,Stocks,SELL,3500,3400,5,500
"""
        stream = io.BytesIO(broker_csv.encode("utf-8"))
        trades, errors = parse_trades_csv(stream)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]["symbol"], "RELIANCE")
        self.assertEqual(trades[0]["entry_price"], 2500.0)
        self.assertEqual(trades[0]["profit_loss"], 1000.0)
        self.assertEqual(trades[1]["symbol"], "TCS")
        self.assertEqual(trades[1]["trade_type"], "SELL")

    def test_csv_import_route(self):
        self._login()

        csv_content = """Symbol,Market,Type,Entry Price,Exit Price,Quantity,Notes
NVDA,Stocks,BUY,110.0,125.0,20,Imported breakout winner
TSLA,Stocks,BUY,200.0,,15,Open position
"""
        data = {
            "csv_file": (io.BytesIO(csv_content.encode("utf-8")), "my_trades.csv")
        }
        res = self.client.post("/trades/import", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Successfully imported 2 trades", res.data)

        with self.app.app_context():
            u = User.query.filter_by(email="roadmap@example.com").first()
            nvda = Trade.query.filter_by(user_id=u.id, symbol="NVDA").first()
            tsla = Trade.query.filter_by(user_id=u.id, symbol="TSLA").first()

            self.assertIsNotNone(nvda)
            self.assertEqual(nvda.status, "CLOSED")
            self.assertEqual(nvda.profit_loss, 300.0)  # (125 - 110) * 20

            self.assertIsNotNone(tsla)
            self.assertEqual(tsla.status, "OPEN")
            self.assertIsNone(tsla.exit_price)


if __name__ == "__main__":
    unittest.main()
