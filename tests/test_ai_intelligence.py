"""
Unit Tests for Tradenza AI Intelligence System:
- Aura Conversational AI Coach (AuraChatService & CoachMessage)
- AI Trade Post-Mortem Auditor & Execution Alpha Score (AiTradeAuditor)
- Counterfactual Digital Twin Leak Eliminator Simulator (TwinSimulator)
"""

import unittest
from datetime import datetime, timedelta, timezone
from core.factory import create_app
from extensions import db
from models.user import User
from models.trade import Trade
from models.coach_message import CoachMessage
from services.aura_chat_service import AuraChatService
from services.ai_trade_auditor import AiTradeAuditor
from services.twin_simulator import TwinSimulator


class AiIntelligenceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed test user
        self.user = User(
            name="AlphaTrader",
            email="alphatrader@example.com",
            password="hashed_password",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    # =========================================================================
    # 1. AI Trade Auditor & Execution Alpha Tests
    # =========================================================================

    def test_auditor_target_achieved(self):
        """Test clean target achieved execution gives A+ grade and high alpha."""
        trade = Trade(
            user_id=self.user.id,
            symbol="AAPL",
            trade_type="BUY",
            entry_price=150.0,
            exit_price=160.0,
            stop_loss=145.0,
            target=160.0,
            quantity=10.0,
            profit_loss=100.0,
            status="CLOSED",
            strategy="Breakout",
            emotion_before="Calm",
            emotion_after="Disciplined",
            notes="Executed cleanly according to daily plan."
        )
        audit = AiTradeAuditor.audit_trade(trade)

        self.assertGreaterEqual(audit["execution_alpha_score"], 85)
        self.assertEqual(audit["exit_quality"], "TARGET_ACHIEVED")
        self.assertEqual(audit["planned_rr"], 2.0)  # (160-150)/(150-145) = 10/5 = 2.0
        self.assertEqual(audit["realized_r"], 2.0)
        self.assertEqual(audit["r_efficiency_pct"], 100.0)
        self.assertIn("Flawless plan execution", audit["takeaway"])

    def test_auditor_disciplined_stop(self):
        """Test disciplined stop hit is rewarded for risk adherence."""
        trade = Trade(
            user_id=self.user.id,
            symbol="NVDA",
            trade_type="BUY",
            entry_price=100.0,
            exit_price=95.0,
            stop_loss=95.0,
            target=115.0,
            quantity=5.0,
            profit_loss=-25.0,
            status="CLOSED",
            strategy="Pullback",
            emotion_before="Calm",
            emotion_after="Acceptance",
            notes="Stop hit as planned. Small loss accepted."
        )
        audit = AiTradeAuditor.audit_trade(trade)

        self.assertIn(audit["exit_quality"], ("DISCIPLINED_STOP", "STOPPED_OUT"))
        self.assertGreaterEqual(audit["execution_alpha_score"], 65)
        self.assertEqual(audit["realized_r"], -1.0)
        self.assertIn("Textbook risk preservation", audit["takeaway"])

    def test_auditor_stop_violation(self):
        """Test severe penalty when loss is allowed to run past stop loss."""
        trade = Trade(
            user_id=self.user.id,
            symbol="TSLA",
            trade_type="BUY",
            entry_price=200.0,
            exit_price=170.0,  # Far past SL of 190
            stop_loss=190.0,
            target=230.0,
            quantity=2.0,
            profit_loss=-60.0,
            status="CLOSED"
        )
        audit = AiTradeAuditor.audit_trade(trade)

        self.assertEqual(audit["exit_quality"], "STOP_VIOLATION")
        self.assertLessEqual(audit["execution_alpha_score"], 45)
        self.assertEqual(audit["grade"], "D")
        self.assertIn("Critical risk violation", audit["takeaway"])

    def test_auditor_premature_exit(self):
        """Test detection of premature profit taking before planned target."""
        trade = Trade(
            user_id=self.user.id,
            symbol="MSFT",
            trade_type="BUY",
            entry_price=300.0,
            exit_price=305.0,  # Only +$5 when target was +$30
            stop_loss=290.0,
            target=330.0,
            quantity=4.0,
            profit_loss=20.0,
            status="CLOSED",
            notes="Got nervous and closed early."
        )
        audit = AiTradeAuditor.audit_trade(trade)

        self.assertEqual(audit["exit_quality"], "PREMATURE_EXIT")
        self.assertIn("Edge leakage detected", audit["takeaway"])

    # =========================================================================
    # 2. Counterfactual Digital Twin Simulator Tests
    # =========================================================================

    def test_twin_simulator_empty_trades(self):
        """Test simulator handles zero trades cleanly."""
        result = TwinSimulator.simulate(self.user, trades=[])
        self.assertFalse(result["has_data"])
        self.assertEqual(result["total_leaked_capital"], 0.0)

    def test_twin_simulator_identifies_tilt_and_stop_leaks(self):
        """Test counterfactual simulator quantifies tilt & stop loss leakage."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        t1 = Trade(
            id=1,
            user_id=self.user.id,
            symbol="AAPL",
            trade_type="BUY",
            entry_price=100.0,
            exit_price=90.0,
            stop_loss=95.0,  # Runaway loss: lost 10 per share instead of 5
            quantity=10.0,
            profit_loss=-100.0,
            status="CLOSED",
            created_at=now - timedelta(hours=2),
            exit_time=now - timedelta(hours=1, minutes=50)
        )
        # Revenge trade taken 5 mins after losing trade
        t2 = Trade(
            id=2,
            user_id=self.user.id,
            symbol="TSLA",
            trade_type="BUY",
            entry_price=200.0,
            exit_price=180.0,
            stop_loss=190.0,
            quantity=5.0,
            profit_loss=-100.0,
            status="CLOSED",
            emotion_before="Revenge",
            created_at=now - timedelta(hours=1, minutes=45),
            exit_time=now - timedelta(hours=1, minutes=30)
        )
        # Clean winning trade
        t3 = Trade(
            id=3,
            user_id=self.user.id,
            symbol="NVDA",
            trade_type="BUY",
            entry_price=100.0,
            exit_price=120.0,
            stop_loss=95.0,
            target=120.0,
            quantity=10.0,
            profit_loss=200.0,
            status="CLOSED",
            created_at=now - timedelta(minutes=30),
            exit_time=now - timedelta(minutes=10)
        )

        trades = [t1, t2, t3]
        result = TwinSimulator.simulate(self.user, trades=trades)

        self.assertTrue(result["has_data"])
        self.assertEqual(result["actual_pnl"], 0.0)  # -100 -100 + 200 = 0
        self.assertGreater(result["tilt_leak_cost"], 0.0)
        self.assertGreater(result["total_leaked_capital"], 0.0)
        self.assertGreater(result["potential_pnl"], result["actual_pnl"])
        self.assertEqual(result["tilt_trades_count"], 1)

    # =========================================================================
    # 3. Aura Conversational AI Coach Tests
    # =========================================================================

    def test_aura_chat_process_message_and_persistence(self):
        """Test Aura processes intent, grounds in trade data, and persists history."""
        # Create a closed trade for ground truth
        trade = Trade(
            user_id=self.user.id,
            market="Crypto",
            symbol="BTC/USD",
            trade_type="BUY",
            entry_price=60000.0,
            exit_price=64000.0,
            quantity=0.1,
            profit_loss=400.0,
            status="CLOSED",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(trade)
        db.session.commit()

        service = AuraChatService()
        res = service.process_message(self.user, "Review my last trade please")

        self.assertIn("reply", res)
        self.assertIn("BTC/USD", res["reply"])
        self.assertIn("followup_chips", res)
        self.assertGreater(len(res["followup_chips"]), 0)

        # Verify DB persistence
        messages = CoachMessage.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(messages), 2)  # 1 user + 1 aura

        # Verify history retrieval
        history = service.get_conversation_history(self.user)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "aura")

        # Verify clear history
        cleared = service.clear_conversation_history(self.user)
        self.assertTrue(cleared)
        self.assertEqual(len(service.get_conversation_history(self.user)), 0)

    def test_aura_chat_tilt_and_leaks_intents(self):
        """Test Aura's intent classifier and diagnostic responses."""
        service = AuraChatService()

        # Leak diagnosis
        res_leak = service.process_message(self.user, "What is my primary behavioral leak?")
        self.assertIn("reply", res_leak)
        self.assertIn("followup_chips", res_leak)

        # Risk sizing
        res_risk = service.process_message(self.user, "Am I respecting my risk parameters?")
        self.assertIn("reply", res_risk)

        # Session prep
        res_prep = service.process_message(self.user, "Help me plan my next trading session")
        self.assertIn("reply", res_prep)
        self.assertIn("Battle Plan", res_prep["reply"])


if __name__ == "__main__":
    unittest.main()
