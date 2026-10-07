import unittest

try:
    from core.factory import create_app
    from extensions import db
    from models.user import User
    from models.trade import Trade
    from services.auth_service import AuthService
    from services.analytics import AnalyticsService
    from services.digital_twin_service import DigitalTwinService
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@unittest.skipUnless(HAS_FLASK, "Flask and Flask-SQLAlchemy dependencies required")
class DashboardAndPipelineTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            AuthService.register_user("Pipeline User", "pipeline@example.com", "secret123")
            self.user = User.query.filter_by(email="pipeline@example.com").first()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_pipeline_refresh_user(self):
        with self.app.app_context():
            user = User.query.filter_by(email="pipeline@example.com").first()

            # Add a trade
            trade = Trade(
                user_id=user.id,
                market="CRYPTO",
                symbol="BTCUSDT",
                trade_type="BUY",
                entry_price=50000.0,
                exit_price=52000.0,
                quantity=1.0,
                stop_loss=49000.0,
                target=53000.0,
                profit_loss=2000.0,
                status="CLOSED",
                confidence=8
            )
            db.session.add(trade)
            db.session.commit()

            analytics_service = AnalyticsService()
            result = analytics_service.refresh_user(user)

            self.assertIn("behavior", result)
            self.assertIn("genome", result)
            self.assertIn("insights", result)
            self.assertIn("aura", result)
            self.assertEqual(result["trade_count"], 1)

    def test_digital_twin_generation(self):
        with self.app.app_context():
            user = User.query.filter_by(email="pipeline@example.com").first()
            twin = DigitalTwinService().get_twin(user)

            self.assertIn("identity", twin)
            self.assertIn("personality", twin)
            self.assertIn("risk_profile", twin)
            self.assertIn("decision_profile", twin)
            self.assertIn("evolution", twin)

    def test_dashboard_authenticated_render_with_hud(self):
        with self.client:
            # Login as test user
            self.client.post("/login", data={
                "email": "pipeline@example.com",
                "password": "secret123"
            })
            response = self.client.get("/dashboard")
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("Trader Quality", html)
            self.assertIn("High-Water Mark", html)
            self.assertIn("Portfolio Overview", html)


if __name__ == "__main__":
    unittest.main()
