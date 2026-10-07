import unittest
from datetime import datetime, timedelta, timezone
from engines.behavior_engine import BehaviorEngine
from engines.genome_engine import GenomeEngine, TraderGenomeScore
from core.factory import create_app
from extensions import db
from models.user import User
from models.trade import Trade
from models.genome import TraderGenome, TraderGenomeHistory
from services.auth_service import AuthService
from services.analytics import AnalyticsService


class GenomeIntelligenceTestCase(unittest.TestCase):

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

        _, _ = AuthService.register_user("Genome Tester", "genome@tradenza.test", "SecurePass123!")
        self.user = User.query.filter_by(email="genome@tradenza.test").first()
        self.engine = GenomeEngine()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def test_no_compounding_degradation_bug(self):
        """
        Verify that re-evaluating the genome repeatedly with previous_genome
        does NOT cause scores to degrade exponentially toward zero.
        """
        t1 = datetime(2026, 1, 10, 10, 0, 0)
        t2 = datetime(2026, 1, 10, 10, 10, 0)

        # Revenge trade scenario
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
                "confidence": 5,
            },
            {
                "id": 2,
                "entry_time": t2,
                "exit_time": t2 + timedelta(minutes=5),
                "entry_price": 95.0,
                "exit_price": 90.0,
                "stop_loss": 90.0,
                "target": 105.0,
                "quantity": 2.0,  # Double size revenge
                "pnl": -10.0,
                "confidence": 4,
            }
        ]

        # First calculation
        g1 = self.engine.calculate_genome(trades)
        d1 = g1.discipline

        # Second calculation passing g1 as previous_genome
        g2 = self.engine.calculate_genome(trades, previous_genome=g1)
        d2 = g2.discipline

        # Third calculation passing g2 as previous_genome
        g3 = self.engine.calculate_genome(trades, previous_genome=g2)
        d3 = g3.discipline

        # In the buggy version, d1 > d2 > d3 down toward 0.
        # In the fixed version, the score is calculated fresh and stable.
        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)
        self.assertEqual(g3.dimension_deltas["discipline"], 0.0)

    def test_explainability_factor_breakdowns(self):
        """
        Verify that factor breakdowns explain exact score contributions.
        """
        t1 = datetime(2026, 1, 10, 10, 0, 0)
        trades = [
            {
                "id": 1,
                "entry_time": t1,
                "exit_time": t1 + timedelta(minutes=30),
                "entry_price": 100.0,
                "exit_price": 120.0,
                "stop_loss": 95.0,
                "target": 115.0,
                "planned_rr": 3.0,
                "quantity": 1.0,
                "pnl": 20.0,
                "confidence": 8,
            }
        ]

        genome = self.engine.calculate_genome(trades)
        factors = genome.factor_breakdowns

        self.assertIn("discipline", factors)
        self.assertIn("risk_control", factors)
        self.assertTrue(len(factors["discipline"]) >= 1)
        self.assertEqual(factors["discipline"][0]["factor"], "Baseline Calibrated Value")

        # Explainability items have factor description and numeric impact
        for item in factors["discipline"]:
            self.assertIn("factor", item)
            self.assertIn("impact", item)

    def test_sample_size_confidence_tiers(self):
        """
        Verify confidence tiers: INSUFFICIENT (<5), EMERGING (5-14), ESTABLISHED (15-49), MATURE (50+)
        """
        # 2 trades -> INSUFFICIENT_SAMPLE
        g_small = self.engine.calculate_genome([{"id": 1, "pnl": 5.0}, {"id": 2, "pnl": -5.0}])
        self.assertEqual(g_small.confidence_tier, "INSUFFICIENT_SAMPLE")
        self.assertIn("Insufficient evidence", g_small.confidence_message)

        # 8 trades -> EMERGING
        trades_8 = [{"id": i, "pnl": 5.0} for i in range(8)]
        g_emerging = self.engine.calculate_genome(trades_8)
        self.assertEqual(g_emerging.confidence_tier, "EMERGING")

        # 20 trades -> ESTABLISHED
        trades_20 = [{"id": i, "pnl": 5.0} for i in range(20)]
        g_established = self.engine.calculate_genome(trades_20)
        self.assertEqual(g_established.confidence_tier, "ESTABLISHED")

        # 55 trades -> MATURE
        trades_55 = [{"id": i, "pnl": 5.0} for i in range(55)]
        g_mature = self.engine.calculate_genome(trades_55)
        self.assertEqual(g_mature.confidence_tier, "MATURE")

    def test_analytics_refresh_records_genome_history(self):
        """
        Verify that AnalyticsService.refresh_user() persists both TraderGenome
        and appends a TraderGenomeHistory record.
        """
        trade = Trade(
            user_id=self.user.id,
            market="Crypto",
            symbol="ETHUSDT",
            trade_type="BUY",
            entry_price=2000.0,
            exit_price=2200.0,
            quantity=1.0,
            profit_loss=200.0,
            status="CLOSED"
        )
        db.session.add(trade)
        db.session.commit()

        analytics_service = AnalyticsService()
        result = analytics_service.refresh_user(self.user)

        self.assertIn("genome", result)
        self.assertEqual(result["genome"].trade_count, 1)

        # Verify database history snapshot
        history = TraderGenomeHistory.query.filter_by(user_id=self.user.id).all()
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0].confidence_tier, "INSUFFICIENT_SAMPLE")


if __name__ == "__main__":
    unittest.main()
