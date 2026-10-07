import json
import unittest
from unittest.mock import MagicMock, patch

try:
    from core.factory import create_app
    from extensions import db
    from models.user import User
    from models.trade import Trade
    from models.portfolio import Portfolio
    from services.auth_service import AuthService
    from services.ai_gateway import AIGateway
    from services.prompt_builder import PromptBuilder
    from services.aura_tools import AuraTools
    from services.aura_chat_service import AuraChatService
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@unittest.skipUnless(HAS_FLASK, "Flask dependencies required")
class AIGatewayAndIntelligenceTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            AuthService.register_user("AI Trader", "aitrader@example.com", "securepass123")
            self.user = User.query.filter_by(email="aitrader@example.com").first()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _login(self):
        return self.client.post("/login", data={
            "email": "aitrader@example.com",
            "password": "securepass123"
        }, follow_redirects=True)

    # ------------------------------------------------------------------
    # 1. AuraTools Testing
    # ------------------------------------------------------------------

    def test_aura_tools_position_sizing(self):
        # 10,000 balance, 2% risk = $200 risk. Entry 100, SL 95 (dist = 5). Shares = 200/5 = 40.
        calc = AuraTools.calculate_position_size(
            account_balance=10000.0,
            risk_percent=2.0,
            entry_price=100.0,
            stop_loss=95.0
        )
        self.assertNotIn("error", calc)
        self.assertEqual(calc["risk_capital"], 200.0)
        self.assertEqual(calc["stop_distance"], 5.0)
        self.assertEqual(calc["recommended_quantity"], 40.0)
        self.assertEqual(calc["position_notional_value"], 4000.0)

    def test_aura_tools_position_sizing_invalid(self):
        # Equal entry and stop loss
        calc = AuraTools.calculate_position_size(
            account_balance=10000.0,
            risk_percent=2.0,
            entry_price=100.0,
            stop_loss=100.0
        )
        self.assertIn("error", calc)

    def test_aura_tools_live_quote(self):
        quote = AuraTools.get_live_market_quote("AAPL")
        self.assertEqual(quote["symbol"], "AAPL")
        self.assertIn("price", quote)
        self.assertGreater(quote["price"], 0)

    # ------------------------------------------------------------------
    # 2. PromptBuilder Context Grounding
    # ------------------------------------------------------------------

    def test_prompt_builder_grounded_facts(self):
        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            u.currency = "₹"
            u.max_risk_percent = 1.5
            u.ai_coaching_style = "disciplined"

            # Add a trade
            t = Trade(
                user_id=u.id,
                market="Stocks",
                symbol="TCS",
                trade_type="BUY",
                entry_price=3500.0,
                exit_price=3600.0,
                quantity=10.0,
                status="CLOSED",
                profit_loss=1000.0
            )
            db.session.add(t)
            db.session.commit()

            prompt = PromptBuilder.build_system_prompt(u)

            # Grounded assertions
            self.assertIn("AI Trader", prompt)
            self.assertIn("₹", prompt)
            self.assertIn("1.5%", prompt)
            self.assertIn("TCS", prompt)
            self.assertTrue("Developing" in prompt or "Trader" in prompt)
            self.assertIn("military-grade risk manager", prompt)

    # ------------------------------------------------------------------
    # 3. AIGateway Mocked Provider Calls
    # ------------------------------------------------------------------

    def test_ai_gateway_offline_mode(self):
        success, msg = AIGateway.generate_chat_response(
            provider="offline",
            api_key="",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertFalse(success)
        self.assertIn("Offline mode", msg)

    def test_ai_gateway_missing_api_key(self):
        success, msg = AIGateway.generate_chat_response(
            provider="gemini",
            api_key="",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertFalse(success)
        self.assertIn("API key is not configured", msg)

    @patch("urllib.request.urlopen")
    def test_ai_gateway_gemini_success(self, mock_urlopen):
        # Mock Gemini response
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "candidates": [{
                "content": {
                    "parts": [{"text": "You followed your trading plan with A+ discipline."}]
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        messages = [
            {"role": "system", "content": "You are Aura."},
            {"role": "user", "content": "How was my trade?"}
        ]
        success, reply = AIGateway.generate_chat_response(
            provider="gemini",
            api_key="fake-gemini-key",
            messages=messages
        )
        self.assertTrue(success)
        self.assertEqual(reply, "You followed your trading plan with A+ discipline.")

    @patch("urllib.request.urlopen")
    def test_ai_gateway_openai_success(self, mock_urlopen):
        # Mock OpenAI response
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{
                "message": {"content": "Your risk-to-reward ratio was 1:2.5, which is mathematically sound."}
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        messages = [
            {"role": "system", "content": "You are Aura."},
            {"role": "user", "content": "Analyze my risk."}
        ]
        success, reply = AIGateway.generate_chat_response(
            provider="openai",
            api_key="sk-fake-openai-key",
            messages=messages
        )
        self.assertTrue(success)
        self.assertEqual(reply, "Your risk-to-reward ratio was 1:2.5, which is mathematically sound.")

    @patch("urllib.request.urlopen")
    def test_ai_gateway_nvidia_success(self, mock_urlopen):
        # Mock NVIDIA NIM DeepSeek response
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{
                "message": {"content": "DeepSeek analysis: High conviction breakout with 72% analogue win rate."}
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        messages = [
            {"role": "system", "content": "You are Aura with DeepSeek."},
            {"role": "user", "content": "Analyze my setup."}
        ]
        success, reply = AIGateway.generate_chat_response(
            provider="nvidia",
            api_key="nvapi-fake-test-key",
            messages=messages,
            model="deepseek-ai/deepseek-v4.1-flash"
        )
        self.assertTrue(success)
        self.assertEqual(reply, "DeepSeek analysis: High conviction breakout with 72% analogue win rate.")

    def test_ai_gateway_nvidia_missing_key(self):
        success, msg = AIGateway.generate_chat_response(
            provider="nvidia",
            api_key="",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertFalse(success)
        self.assertIn("NVIDIA NIM API key is not configured", msg)

    # ------------------------------------------------------------------
    # 4. AuraChatService Hybrid & Fallback Execution
    # ------------------------------------------------------------------

    def test_aura_chat_service_fallback_to_heuristic(self):
        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            u.ai_provider = "offline"

            chat_service = AuraChatService()
            res = chat_service.process_message(u, "Am I on tilt right now?")

            self.assertEqual(res["source"], "heuristic_engine")
            self.assertEqual(res["intent"], "tilt_check")
            self.assertIn("reply", res)
            self.assertGreater(len(res["followup_chips"]), 0)

    @patch("services.ai_gateway.AIGateway.generate_chat_response")
    def test_aura_chat_service_nvidia_execution(self, mock_llm):
        mock_llm.return_value = (True, "DeepSeek Coach: Edge requires patience. Wait for the retest.")

        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            u.ai_provider = "nvidia"
            u.nvidia_api_key = "nvapi-valid-test-key"

            chat_service = AuraChatService()
            res = chat_service.process_message(u, "Should I enter AAPL here?")

            self.assertEqual(res["source"], "llm_nvidia")
            self.assertIn("DeepSeek Coach", res["reply"])
            self.assertEqual(res["orb_state"], "speaking")

    @patch("services.ai_gateway.AIGateway.generate_chat_response")
    def test_aura_chat_service_hybrid_llm_execution(self, mock_llm):
        mock_llm.return_value = (True, "Aura LLM: Great question! Probabilistic thinking requires accepting random outcomes.")

        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            u.ai_provider = "gemini"
            u.gemini_api_key = "valid-test-key"

            chat_service = AuraChatService()
            res = chat_service.process_message(u, "How do I become consistent?")

            self.assertEqual(res["source"], "llm_gemini")
            self.assertIn("Aura LLM", res["reply"])
            self.assertEqual(res["orb_state"], "speaking")

    # ------------------------------------------------------------------
    # 5. Settings Route POST Action='ai'
    # ------------------------------------------------------------------

    def test_settings_save_ai_parameters(self):
        self._login()

        res = self.client.post("/settings/", data={
            "action": "ai",
            "ai_provider": "nvidia",
            "ai_model": "deepseek-ai/deepseek-v4.1-flash",
            "ai_coaching_style": "disciplined",
            "nvidia_api_key": "nvapi-TestKey123",
            "gemini_api_key": "AIzaSyTestKey123",
            "openai_api_key": "sk-TestOpenAiKey456"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            self.assertEqual(u.ai_provider, "nvidia")
            self.assertEqual(u.ai_model, "deepseek-ai/deepseek-v4.1-flash")
            self.assertEqual(u.ai_coaching_style, "disciplined")
            self.assertEqual(u.nvidia_api_key, "nvapi-TestKey123")
            self.assertEqual(u.gemini_api_key, "AIzaSyTestKey123")
            self.assertEqual(u.openai_api_key, "sk-TestOpenAiKey456")

    def test_evidence_board_frontier_reasoning(self):
        from services.evidence_board import EvidenceBoardService

        with self.app.app_context():
            u = User.query.filter_by(email="aitrader@example.com").first()
            res = EvidenceBoardService.synthesize_evidence_board(
                user=u,
                symbol="NVDA",
                setup_type="Breakout",
                entry_price=120.0
            )

            self.assertIn("frontier_reasoning", res)
            self.assertIn("verdict", res["frontier_reasoning"])
            self.assertTrue(res["frontier_reasoning"]["success"])


if __name__ == "__main__":
    unittest.main()
