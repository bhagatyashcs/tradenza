import unittest

try:
    from core.factory import create_app
    from extensions import db
    from models.user import User
    from services.auth_service import AuthService
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@unittest.skipUnless(HAS_FLASK, "Flask and Flask-SQLAlchemy dependencies required")
class AuthTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_register_user_success(self):
        with self.app.app_context():
            success, message = AuthService.register_user("Test Trader", "trader@example.com", "securepass123")
            self.assertTrue(success)
            self.assertEqual(message, "Registration successful.")

            user = User.query.filter_by(email="trader@example.com").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.name, "Test Trader")
            self.assertIsNotNone(user.portfolio)
            self.assertEqual(user.portfolio.starting_balance, 0.0)
            self.assertEqual(user.portfolio.current_balance, 0.0)
            self.assertIsNotNone(user.genome)
            self.assertEqual(user.genome.discipline, 50.0)

    def test_register_duplicate_email(self):
        with self.app.app_context():
            AuthService.register_user("First User", "duplicate@example.com", "pass1")
            success, message = AuthService.register_user("Second User", "duplicate@example.com", "pass2")
            self.assertFalse(success)
            self.assertIn("already exists", message)

    def test_authenticate_user(self):
        with self.app.app_context():
            AuthService.register_user("Auth User", "auth@example.com", "mypassword")

            # Correct password
            user = AuthService.authenticate("auth@example.com", "mypassword")
            self.assertIsNotNone(user)
            self.assertEqual(user.email, "auth@example.com")

            # Incorrect password
            invalid_user = AuthService.authenticate("auth@example.com", "wrongpass")
            self.assertIsNone(invalid_user)

            # Non-existent email
            missing_user = AuthService.authenticate("ghost@example.com", "mypassword")
            self.assertIsNone(missing_user)

    def test_login_route_get(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login", response.data)

    def test_register_route_get(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create Account", response.data)

    def test_csrf_rejection_when_token_missing(self):
        """Verify that when WTF_CSRF_ENABLED is True, raw POST without token is rejected."""
        csrf_app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
            "SECRET_KEY": "csrf-test-secret"
        })
        csrf_client = csrf_app.test_client()
        with csrf_app.app_context():
            db.create_all()
            # Raw POST to login without CSRF token should return 400
            res = csrf_client.post("/login", data={"email": "trader@example.com", "password": "pass"})
            self.assertEqual(res.status_code, 400)
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
