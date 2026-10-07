import unittest
from datetime import datetime, timedelta, timezone
from engines.behavior_engine import BehaviorEngine
from engines.genome_engine import GenomeEngine
from engines.insight_engine import InsightEngine
from ai.aura import AuraCoach

try:
    from core.factory import create_app
    from extensions import db
    from models.user import User
    from models.trade import Trade
    from services.auth_service import AuthService
    from services.trade_service import TradeService
    from services.tradebuddy import TradeBuddyService
    HAS_TRADE_SERVICE = True
except ImportError:
    HAS_TRADE_SERVICE = False


class TradeAndIntelligenceTestCase(unittest.TestCase):

    @unittest.skipUnless(HAS_TRADE_SERVICE, "TradeService requires Flask/SQLAlchemy")
    def test_calculate_profit_buy_trade(self):
        class MockTrade:
            trade_type = "BUY"
            entry_price = 100.0
            exit_price = 110.0
            quantity = 2.0

        pnl = TradeService.calculate_profit(MockTrade())
        self.assertEqual(pnl, 20.0)

    @unittest.skipUnless(HAS_TRADE_SERVICE, "TradeService requires Flask/SQLAlchemy")
    def test_calculate_profit_sell_trade(self):
        class MockTrade:
            trade_type = "SELL"
            entry_price = 100.0
            exit_price = 90.0
            quantity = 3.0

        pnl = TradeService.calculate_profit(MockTrade())
        self.assertEqual(pnl, 30.0)

    def test_behavior_engine_revenge_trading_detection(self):
        engine = BehaviorEngine(revenge_time_window_minutes=20)
        t1 = datetime(2026, 1, 10, 10, 0, 0)
        t2 = datetime(2026, 1, 10, 10, 10, 0)

        trades = [
            {
                "id": 1,
                "entry_time": t1,
                "exit_time": t1 + timedelta(minutes=5),
                "entry_price": 100.0,
                "exit_price": 95.0,
                "stop_loss": 95.0,
                "target": 110.0,
                "quantity": 1.0,
                "pnl": -5.0,
            },
            {
                "id": 2,
                "entry_time": t2,
                "exit_time": t2 + timedelta(minutes=5),
                "entry_price": 95.0,
                "exit_price": 98.0,
                "stop_loss": 90.0,
                "target": 105.0,
                "quantity": 2.0,  # Scaled up size after loss
                "pnl": 6.0,
            }
        ]

        report = engine.analyze(trades)
        pattern_types = [p.pattern_type for p in report.patterns_detected]
        self.assertIn("revenge_trading", pattern_types)

    def test_behavior_engine_overtrading_detection(self):
        engine = BehaviorEngine(overtrading_daily_threshold=3)
        dt = datetime(2026, 1, 15, 10, 0, 0)

        trades = []
        for i in range(5):
            trades.append({
                "id": i + 1,
                "entry_time": dt + timedelta(minutes=i * 10),
                "exit_time": dt + timedelta(minutes=i * 10 + 5),
                "entry_price": 100.0,
                "exit_price": 102.0,
                "stop_loss": 99.0,
                "target": 105.0,
                "quantity": 1.0,
                "pnl": 2.0,
            })

        report = engine.analyze(trades)
        pattern_types = [p.pattern_type for p in report.patterns_detected]
        self.assertIn("overtrading", pattern_types)

    def test_genome_engine_and_archetype(self):
        genome_engine = GenomeEngine()
        dt = datetime(2026, 1, 12, 10, 0, 0)

        clean_trades = [
            {
                "id": 1,
                "entry_time": dt,
                "exit_time": dt + timedelta(minutes=30),
                "entry_price": 100.0,
                "exit_price": 115.0,
                "stop_loss": 90.0,
                "target": 120.0,
                "quantity": 1.0,
                "pnl": 15.0,
                "confidence": 8,
            },
            {
                "id": 2,
                "entry_time": dt + timedelta(hours=2),
                "exit_time": dt + timedelta(hours=3),
                "entry_price": 110.0,
                "exit_price": 125.0,
                "stop_loss": 100.0,
                "target": 130.0,
                "quantity": 1.0,
                "pnl": 15.0,
                "confidence": 9,
            }
        ]

        genome = genome_engine.calculate_genome(clean_trades)
        self.assertGreaterEqual(genome.discipline, 50.0)
        self.assertGreaterEqual(genome.overall_score, 50.0)
        self.assertIsInstance(genome.archetype, str)

    def test_insight_engine_and_aura_coach(self):
        insight_engine = InsightEngine()
        aura_coach = AuraCoach()
        dt = datetime(2026, 1, 12, 10, 0, 0)

        trades = [
            {
                "id": 1,
                "entry_time": dt,
                "exit_time": dt + timedelta(minutes=30),
                "entry_price": 100.0,
                "exit_price": 110.0,
                "stop_loss": 95.0,
                "target": 115.0,
                "quantity": 1.0,
                "pnl": 10.0,
            },
            {
                "id": 2,
                "entry_time": dt + timedelta(hours=1),
                "exit_time": dt + timedelta(hours=2),
                "entry_price": 100.0,
                "exit_price": 110.0,
                "stop_loss": 95.0,
                "target": 115.0,
                "quantity": 1.0,
                "pnl": 10.0,
            },
            {
                "id": 3,
                "entry_time": dt + timedelta(hours=3),
                "exit_time": dt + timedelta(hours=4),
                "entry_price": 100.0,
                "exit_price": 110.0,
                "stop_loss": 95.0,
                "target": 115.0,
                "quantity": 1.0,
                "pnl": 10.0,
            }
        ]

        behavior_report = BehaviorEngine().analyze(trades)
        genome = GenomeEngine().calculate_genome(trades, behavior_report=behavior_report)
        insights = insight_engine.generate_insights(trades, behavior_report=behavior_report, genome_score=genome)

        self.assertIsInstance(insights.insights, list)

        aura_response = aura_coach.explain_session(
            behavior_report=behavior_report,
            genome_score=genome,
            insight_report=insights,
            trader_name="Test Trader"
        )
        self.assertEqual(aura_response["trader_name"], "Test Trader")
        self.assertIn("coaching_message", aura_response)
        self.assertIn("reflective_question", aura_response)
        self.assertIn("daily_mission", aura_response)

    @unittest.skipUnless(HAS_TRADE_SERVICE, "TradeBuddyService requires Flask/SQLAlchemy")
    def test_tradebuddy_calculate_risk_metrics_healthy(self):
        metrics = TradeBuddyService.calculate_risk_metrics(
            entry_price=100.0,
            stop_loss=95.0,
            target=115.0,
            quantity=10.0,
            account_balance=10000.0
        )
        self.assertEqual(metrics["status"], "calculated")
        self.assertEqual(metrics["risk_dollar"], 50.0)
        self.assertEqual(metrics["reward_dollar"], 150.0)
        self.assertEqual(metrics["rr_ratio"], 3.0)
        self.assertEqual(metrics["risk_percent"], 0.5)
        self.assertFalse(metrics["is_rr_violation"])
        self.assertFalse(metrics["is_capital_violation"])
        self.assertEqual(metrics["recommended_qty_2pct"], 40.0)

    @unittest.skipUnless(HAS_TRADE_SERVICE, "TradeBuddyService requires Flask/SQLAlchemy")
    def test_tradebuddy_calculate_risk_metrics_violations(self):
        metrics = TradeBuddyService.calculate_risk_metrics(
            entry_price=100.0,
            stop_loss=90.0,
            target=105.0,
            quantity=10.0,
            account_balance=1000.0
        )
        self.assertTrue(metrics["is_rr_violation"])
        self.assertEqual(metrics["rr_ratio"], 0.5)
        self.assertTrue(metrics["is_capital_violation"])
        self.assertEqual(metrics["risk_percent"], 10.0)

    @unittest.skipUnless(HAS_TRADE_SERVICE, "TradeBuddyService requires Flask/SQLAlchemy")
    def test_tradebuddy_calculate_risk_metrics_incomplete(self):
        metrics = TradeBuddyService.calculate_risk_metrics(
            entry_price=100.0,
            stop_loss=None,
            target=110.0
        )
        self.assertEqual(metrics["status"], "incomplete")
        self.assertIsNone(metrics["risk_dollar"])


@unittest.skipUnless(HAS_TRADE_SERVICE, "Flask and SQLAlchemy dependencies required")
class TradeDatabaseAndLifecycleTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            AuthService.register_user("Trade Tester", "tester@example.com", "secret123")
            self.user = User.query.filter_by(email="tester@example.com").first()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_close_trade_execution_and_cooldown_trigger(self):
        with self.app.app_context():
            user = User.query.filter_by(email="tester@example.com").first()

            trade = Trade(
                user_id=user.id,
                market="Stocks",
                symbol="AAPL",
                trade_type="BUY",
                entry_price=150.0,
                quantity=10.0,
                status="OPEN"
            )
            db.session.add(trade)
            db.session.commit()

            # Initially open trade -> no cooldown
            cooldown_before = TradeBuddyService.check_cooldown_status(user)
            self.assertFalse(cooldown_before["in_cooldown"])

            # Close trade with a loss
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            closed_trade = TradeService.close_trade(
                trade=trade,
                exit_price=140.0,
                emotion_after="Frustrated",
                notes="Cut early on panic",
                exit_time=now
            )

            self.assertEqual(closed_trade.status, "CLOSED")
            self.assertEqual(closed_trade.profit_loss, -100.0)
            self.assertEqual(closed_trade.emotion_after, "Frustrated")
            self.assertIn("[Closing Notes]: Cut early on panic", closed_trade.notes)
            self.assertEqual(closed_trade.exit_time, now)

            # Check cooldown triggered
            cooldown_after = TradeBuddyService.check_cooldown_status(user)
            self.assertTrue(cooldown_after["in_cooldown"])
            self.assertEqual(cooldown_after["trigger_symbol"], "AAPL")
            self.assertEqual(cooldown_after["loss_amount"], 100.0)
            self.assertIn("Active Cooldown", cooldown_after["message"])

    def test_quantitative_risk_metrics_and_thesis_persistence(self):
        """Verify planned risk, planned R:R, realized R, and thesis persistence."""
        with self.app.app_context():
            user = User.query.filter_by(email="tester@example.com").first()

            # Mock Form with stop_loss and target
            class MockTradeForm:
                class Market: data = "Stocks"
                class Symbol: data = "NVDA"
                class TradeType: data = "BUY"
                class EntryPrice: data = 100.0
                class ExitPrice: data = None
                class Quantity: data = 10.0
                class Strategy: data = "Breakout"
                class Timeframe: data = "15m"
                class StopLoss: data = 95.0
                class Target: data = 115.0
                class EmotionBefore: data = "Confident"
                class Confidence: data = 8
                class Notes: data = "High relative volume breakout"
                class EntryTime: data = "2026-01-20 10:00"
                class ExitTime: data = None
                class EntryThesis: data = "Daily breakout invalidates below 95.0"
                class ExitThesis: data = None
                class ExitReason: data = None
                market = Market()
                symbol = Symbol()
                trade_type = TradeType()
                entry_price = EntryPrice()
                exit_price = ExitPrice()
                quantity = Quantity()
                strategy = Strategy()
                timeframe = Timeframe()
                stop_loss = StopLoss()
                target = Target()
                emotion_before = EmotionBefore()
                confidence = Confidence()
                notes = Notes()
                entry_time = EntryTime()
                exit_time = ExitTime()
                entry_thesis = EntryThesis()
                exit_thesis = ExitThesis()
                exit_reason = ExitReason()

            trade = TradeService.create_trade(user, MockTradeForm())
            self.assertIsNotNone(trade.id)
            # Planned Risk = |100 - 95| * 10 = 50.0
            self.assertEqual(trade.risk_amount, 50.0)
            # Planned R:R = |115 - 100| / |100 - 95| = 15 / 5 = 3.0
            self.assertEqual(trade.planned_rr, 3.0)
            self.assertEqual(trade.entry_thesis, "Daily breakout invalidates below 95.0")

            # Close the trade at 110.0 (Profit = +100.0)
            closed = TradeService.close_trade(
                trade=trade,
                exit_price=110.0,
                emotion_after="Satisfied",
                notes="Took profit into strength",
                exit_reason="TARGET_HIT",
                exit_thesis="Executed scale-out as planned"
            )

            self.assertEqual(closed.profit_loss, 100.0)
            # Realized R = 100.0 / 50.0 = +2.0R
            self.assertEqual(closed.realized_r, 2.0)
            self.assertEqual(closed.exit_reason, "TARGET_HIT")
            self.assertEqual(closed.exit_thesis, "Executed scale-out as planned")

            # Verify to_dict output
            t_dict = closed.to_dict()
            self.assertEqual(t_dict["symbol"], "NVDA")
            self.assertEqual(t_dict["realized_r"], 2.0)
            self.assertEqual(t_dict["planned_rr"], 3.0)
            self.assertEqual(t_dict["risk_amount"], 50.0)


if __name__ == "__main__":
    unittest.main()
