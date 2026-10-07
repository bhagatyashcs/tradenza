"""
Unit Tests for Institutional Trade Planner & Active Trade Pilot - Tradenza
Verifies 10-year veteran quantitative & behavioral decision engine:
- Confluence scoring (0-100)
- Mathematical Expected Value (EV)
- Half-Kelly volatility-adjusted sizing
- 3-Tier target ladders & invalidation levels
- DeepSeek Devil's Advocate pre-mortem stress test
- Active in-trade pilot telemetry and tactical advice
- API endpoints: /trades/institutional_blueprint and /trades/<id>/pilot_telemetry
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from core.factory import create_app
from extensions import db
from models.user import User
from models.trade import Trade
from models.portfolio import Portfolio
from engines.quant_feature_engine import SetupFeatureVector
from engines.institutional_trade_planner import InstitutionalTradePlanner
from services.active_trade_pilot import ActiveTradePilot


class InstitutionalPlannerAndPilotTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
            "TWELVE_DATA_API_KEY": "fake-twelve-key",
            "NVIDIA_API_KEY": "nvapi-fake-test-key",
            "AI_PROVIDER": "nvidia",
            "AI_MODEL": "deepseek-ai/deepseek-v4.1-flash"
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            user = User(
                name="VeteranTrader",
                email="veteran@example.com",
                password="pbkdf2:sha256:dummy",
                currency="$",
                max_risk_percent=2.0,
                daily_max_loss=500.0,
                ai_provider="nvidia",
                ai_model="deepseek-ai/deepseek-v4.1-flash",
                nvidia_api_key="nvapi-fake-test-key"
            )
            db.session.add(user)
            db.session.commit()

            portfolio = Portfolio(
                user_id=user.id,
                starting_balance=10000.0,
                current_balance=10000.0
            )
            db.session.add(portfolio)

            # Seed an open trade
            open_trade = Trade(
                user_id=user.id,
                symbol="AAPL",
                market="Stocks",
                trade_type="BUY",
                entry_price=100.0,
                stop_loss=95.0,
                target=115.0,
                quantity=10.0,
                status="OPEN"
            )
            db.session.add(open_trade)

            # Seed a closed trade
            closed_trade = Trade(
                user_id=user.id,
                symbol="NVDA",
                market="Stocks",
                trade_type="BUY",
                entry_price=120.0,
                exit_price=135.0,
                stop_loss=115.0,
                target=135.0,
                quantity=20.0,
                profit_loss=300.0,
                status="CLOSED"
            )
            db.session.add(closed_trade)
            db.session.commit()

            self.user_id = user.id
            self.open_trade_id = open_trade.id
            self.closed_trade_id = closed_trade.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(self.user_id)
            sess["_fresh"] = True

    # ------------------------------------------------------------------
    # 1. Confluence Scoring
    # ------------------------------------------------------------------

    def test_confluence_scoring_high_quality(self):
        vec = SetupFeatureVector(
            symbol="AAPL",
            market="Stocks",
            rsi=58.0,
            atr_pct=2.4,
            volume_ratio=1.8,
            ema_spread_pct=3.5,
            dist_high_pct=-4.0,
            roc_5d=4.2,
            regime="BULLISH_TREND",
            sector_strength=1.5
        )
        news = {"sentiment_score": 0.45, "sentiment_label": "BULLISH"}

        res = InstitutionalTradePlanner.calculate_confluence_score(
            feature_vector=vec,
            news_data=news,
            planned_rr=2.5,
            analogue_win_rate=65.0
        )

        self.assertGreaterEqual(res["score"], 80.0)
        self.assertEqual(res["rating"], "INSTITUTIONAL_GRADE")
        self.assertEqual(res["passed_factors_count"], 5)

    def test_confluence_scoring_low_quality(self):
        vec = SetupFeatureVector(
            symbol="DODGY",
            market="Stocks",
            rsi=85.0,
            atr_pct=6.5,
            volume_ratio=0.6,
            ema_spread_pct=-2.0,
            dist_high_pct=-35.0,
            roc_5d=-5.0,
            regime="BEARISH_EXPANSION",
            sector_strength=-1.2
        )
        news = {"sentiment_score": -0.6, "sentiment_label": "BEARISH"}

        res = InstitutionalTradePlanner.calculate_confluence_score(
            feature_vector=vec,
            news_data=news,
            planned_rr=1.1,
            analogue_win_rate=35.0
        )

        self.assertLess(res["score"], 60.0)
        self.assertEqual(res["rating"], "SUB_THRESHOLD")

    # ------------------------------------------------------------------
    # 2. Expected Value (EV)
    # ------------------------------------------------------------------

    def test_expected_value_positive(self):
        ev = InstitutionalTradePlanner.calculate_expected_value(
            win_rate_pct=60.0,
            planned_risk_per_unit=5.0,
            planned_reward_per_unit=12.5,
            planned_rr=2.5
        )
        self.assertTrue(ev["is_positive"])
        self.assertGreater(ev["ev_r"], 0.5)
        self.assertIn("High Positive Expectancy", ev["verdict"])

    def test_expected_value_negative(self):
        ev = InstitutionalTradePlanner.calculate_expected_value(
            win_rate_pct=30.0,
            planned_risk_per_unit=10.0,
            planned_reward_per_unit=10.0,
            planned_rr=1.0
        )
        self.assertFalse(ev["is_positive"])
        self.assertLess(ev["ev_r"], 0)
        self.assertIn("Negative Expectancy", ev["verdict"])

    # ------------------------------------------------------------------
    # 3. Half-Kelly Position Sizing
    # ------------------------------------------------------------------

    def test_half_kelly_sizing_within_risk_cap(self):
        sz = InstitutionalTradePlanner.calculate_half_kelly_size(
            balance=10000.0,
            max_risk_pct=2.0,
            win_rate_pct=60.0,
            entry_price=100.0,
            stop_loss=95.0,
            planned_rr=2.0
        )
        # Max risk is $200 (2.0% of $10000)
        self.assertLessEqual(sz["allocated_risk_dollars"], 200.0)
        self.assertGreaterEqual(sz["suggested_quantity"], 1)
        self.assertEqual(sz["risk_per_share"], 5.0)
        # 200 / 5 = 40 shares
        self.assertEqual(sz["suggested_quantity"], 40)

    # ------------------------------------------------------------------
    # 4. Target Ladder Calculation (BUY & SELL)
    # ------------------------------------------------------------------

    def test_target_ladder_buy(self):
        lad = InstitutionalTradePlanner.calculate_target_ladder(
            entry_price=100.0,
            stop_loss=90.0,
            trade_type="BUY"
        )
        # 1R = 10.0
        self.assertEqual(lad["r_unit"], 10.0)
        # TP1 = 100 + 1.1*10 = 111.0
        self.assertEqual(lad["tiers"][0]["price"], 111.0)
        # TP2 = 100 + 2.2*10 = 122.0
        self.assertEqual(lad["tiers"][1]["price"], 122.0)
        # Invalidation = 90 - 0.5 = 89.5
        self.assertEqual(lad["invalidation_price"], 89.5)

    def test_target_ladder_sell(self):
        lad = InstitutionalTradePlanner.calculate_target_ladder(
            entry_price=100.0,
            stop_loss=110.0,
            trade_type="SELL"
        )
        self.assertEqual(lad["r_unit"], 10.0)
        # TP1 = 100 - 11 = 89.0
        self.assertEqual(lad["tiers"][0]["price"], 89.0)
        # Invalidation = 110 + 0.5 = 110.5
        self.assertEqual(lad["invalidation_price"], 110.5)

    # ------------------------------------------------------------------
    # 5. Active Trade Pilot Telemetry
    # ------------------------------------------------------------------

    def test_active_pilot_open_trade_in_profit(self):
        with self.app.app_context():
            trade = db.session.get(Trade, self.open_trade_id)
            # Entry 100.0, SL 95.0, Target 115.0 -> Risk = 5.0
            # Test at price 106.0 -> +6.0 profit -> +1.2R
            telemetry = ActiveTradePilot.evaluate_open_position(trade, current_price=106.0)

            self.assertEqual(telemetry["current_r"], 1.2)
            self.assertEqual(telemetry["floating_pnl_dollar"], 60.0)
            self.assertEqual(telemetry["stage_code"], "DE_RISK_OPPORTUNITY")
            self.assertIn("Breakeven", telemetry["trailing_rule"])

    def test_active_pilot_open_trade_in_drawdown(self):
        with self.app.app_context():
            trade = db.session.get(Trade, self.open_trade_id)
            # Test at price 95.2 -> Loss -4.8 -> -0.96R
            telemetry = ActiveTradePilot.evaluate_open_position(trade, current_price=95.2)

            self.assertLess(telemetry["current_r"], -0.85)
            self.assertEqual(telemetry["stage_code"], "CRITICAL_STOP_ZONE")
            self.assertIn("Do not move", telemetry["directive"])

    # ------------------------------------------------------------------
    # 6. API Endpoints
    # ------------------------------------------------------------------

    def test_institutional_blueprint_endpoint(self):
        self._login()
        res = self.client.get(
            "/trades/institutional_blueprint?symbol=AAPL&strategy=Breakout&price=200.0&stop_loss=190.0&target=225.0&type=BUY"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("confluence", data)
        self.assertIn("expected_value", data)
        self.assertIn("sizing", data)
        self.assertIn("target_ladder", data)
        self.assertIn("devils_advocate", data)
        self.assertEqual(data["symbol"], "AAPL")

    def test_pilot_telemetry_endpoint(self):
        self._login()
        res = self.client.get(f"/trades/{self.open_trade_id}/pilot_telemetry?price=108.0&consult_ai=false")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["symbol"], "AAPL")
        self.assertEqual(data["current_r"], 1.6)
        self.assertIn("stage_code", data)

    def test_trade_details_closed_trade_post_mortem(self):
        self._login()
        res = self.client.get(f"/trades/{self.closed_trade_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn("Forensic AI Post-Mortem Audit", html)
        self.assertIn("Execution Alpha", html)


if __name__ == "__main__":
    unittest.main()
