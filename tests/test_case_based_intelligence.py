import unittest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models.user import User
from models.trade import Trade
from engines.quant_feature_engine import QuantFeatureEngine, SetupFeatureVector
from engines.similarity_engine import QuantSimilarityEngine
from memory.event_memory import MarketEventMemory
from memory.episodic_memory import EpisodicMemory
from memory.semantic_memory import SemanticMemory
from knowledge.company_graph import CompanyGraph
from services.evidence_board import EvidenceBoardService


class TestCaseBasedIntelligence(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            from services.auth_service import AuthService
            AuthService.register_user("Test Quant Trader", "quant@example.com", "password123")
            self.user = User.query.filter_by(email="quant@example.com").first()
            self.user_id = self.user.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_quant_feature_vector_extraction(self):
        """Test standard 8-dimensional feature vectorization from trade inputs."""
        vec = QuantFeatureEngine.extract_from_trade_input(
            symbol="TATAMOTORS",
            entry_price=940.0,
            stop_loss=920.0,
            target=980.0,
            strategy="Breakout",
            raw_rsi=64.0,
            raw_volume_ratio=1.9
        )
        self.assertIsInstance(vec, SetupFeatureVector)
        self.assertEqual(vec.symbol, "TATAMOTORS")
        self.assertEqual(vec.strategy, "Breakout")
        self.assertAlmostEqual(vec.rsi, 64.0)
        self.assertAlmostEqual(vec.volume_ratio, 1.9)
        self.assertGreater(vec.rr_ratio, 1.5)

        # Test normalization
        norm_v = QuantFeatureEngine.normalize_vector(vec)
        self.assertEqual(len(norm_v), 8)
        for val in norm_v:
            self.assertGreaterEqual(val, -3.0)
            self.assertLessEqual(val, 3.0)

    def test_quant_similarity_engine_retrieval(self):
        """Test K-NN weighted distance matching and empirical statistics."""
        engine = QuantSimilarityEngine()
        query_vec = QuantFeatureEngine.extract_from_trade_input(
            symbol="TATAMOTORS",
            entry_price=940.0,
            stop_loss=920.0,
            target=980.0,
            strategy="Breakout"
        )
        result = engine.find_similar_setups(query_vec, top_k=5)

        self.assertIn("total_analogues_found", result)
        self.assertGreaterEqual(result["total_analogues_found"], 1)
        self.assertIn("win_rate_pct", result)
        self.assertIn("median_5d_return_pct", result)
        self.assertIn("analogue_profit_factor", result)
        self.assertIsInstance(result["top_historical_cases"], list)
        self.assertGreater(len(result["top_historical_cases"]), 0)

        # Verify distance ordering (first case should have highest similarity score)
        top_cases = result["top_historical_cases"]
        if len(top_cases) >= 2:
            self.assertGreaterEqual(top_cases[0]["similarity_pct"], top_cases[1]["similarity_pct"])

    def test_market_event_memory_temporal_anti_lookahead(self):
        """Test point-in-time temporal filtering to prevent future data leakage."""
        # Query with decision time in Jan 2024
        past_decision_time = "2024-01-01"
        events = MarketEventMemory.retrieve_events(
            sectors=["Semiconductors & AI Hardware", "Broad Market"],
            decision_time=past_decision_time,
            limit=10
        )
        for ev in events:
            # All returned events must have occurred on or before 2024-01-01
            self.assertLessEqual(ev["date"], past_decision_time)

        # Query with current/future decision time
        future_decision = "2026-12-31"
        all_events = MarketEventMemory.retrieve_events(
            sectors=["Semiconductors & AI Hardware"],
            decision_time=future_decision,
            limit=10
        )
        self.assertGreaterEqual(len(all_events), len(events))

    def test_company_graph_network(self):
        """Test directional corporate and macro dependency network."""
        graph = CompanyGraph.get_relationship_network("TATAMOTORS")
        self.assertEqual(graph["symbol"], "TATAMOTORS")
        self.assertEqual(graph["sector"], "Auto / Commercial & Passenger Vehicles")
        self.assertTrue(any("Steel" in cost for cost in graph["input_costs"]))
        self.assertTrue(any("interest rate" in s.lower() for s in graph["macro_sensitivities"]))

        # Test US tech stock
        nvda_graph = CompanyGraph.get_relationship_network("NVDA")
        self.assertEqual(nvda_graph["sector"], "Semiconductors & AI Hardware")
        self.assertTrue(any("TSMC" in cost for cost in nvda_graph["input_costs"]))

    def test_episodic_memory_analysis(self):
        """Test personal execution record retrieval and premature exit detection."""
        with self.app.app_context():
            # Add closed trades for the user
            t1 = Trade(
                user_id=self.user_id,
                symbol="TATAMOTORS",
                market="Stocks",
                trade_type="BUY",
                entry_price=900.0,
                exit_price=915.0, # Target was 950, so gain is 15 vs 50 target dist (<60%, premature exit)
                target=950.0,
                stop_loss=880.0,
                quantity=10.0,
                profit_loss=150.0,
                strategy="Breakout",
                status="CLOSED"
            )
            t2 = Trade(
                user_id=self.user_id,
                symbol="TATAMOTORS",
                market="Stocks",
                trade_type="BUY",
                entry_price=910.0,
                exit_price=918.0, # Premature cut again
                target=960.0,
                stop_loss=890.0,
                quantity=10.0,
                profit_loss=80.0,
                strategy="Breakout",
                status="CLOSED"
            )
            db.session.add_all([t1, t2])
            db.session.commit()

            user = db.session.get(User, self.user_id)
            episodes = EpisodicMemory.get_user_setup_episodes(
                user=user,
                setup_type="Breakout",
                symbol="TATAMOTORS"
            )
            self.assertEqual(episodes["total_user_episodes"], 2)
            self.assertEqual(episodes["user_setup_win_rate"], 100.0)
            self.assertEqual(episodes["premature_exit_count"], 2)
            self.assertIn("cut winning setups prematurely", episodes["personal_verdict"])

    def test_evidence_board_synthesis_and_dual_scores(self):
        """Test holistic evidence board synthesis and dual-score diagnostics."""
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            board = EvidenceBoardService.synthesize_evidence_board(
                user=user,
                symbol="TATAMOTORS",
                setup_type="Breakout",
                entry_price=940.0,
                stop_loss=920.0,
                target=980.0
            )

            self.assertIn("market_opportunity_score", board)
            self.assertIn("personal_fit_score", board)
            self.assertIn("avoidance_zone_triggered", board)
            self.assertIn("analogue_data", board)
            self.assertIn("markdown_board", board)

            # Market Opportunity should be positive and bounded [15, 95]
            self.assertGreaterEqual(board["market_opportunity_score"], 15.0)
            self.assertLessEqual(board["market_opportunity_score"], 95.0)

            # Markdown board contains all 6 fact sections
            md = board["markdown_board"]
            self.assertIn("EVIDENCE BOARD", md)
            self.assertIn("Dual Diagnostic Scores", md)
            self.assertIn("Quantitative Market State", md)
            self.assertIn("Company & Sector Relationship Network", md)

    def test_evidence_board_api_endpoint(self):
        """Test GET /trades/evidence_board authenticated endpoint."""
        with self.client:
            # Login
            self.client.post("/login", data={
                "email": "quant@example.com",
                "password": "password123"
            })

            response = self.client.get("/trades/evidence_board?symbol=TATAMOTORS&strategy=Breakout&price=940.0")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["symbol"], "TATAMOTORS")
            self.assertIn("market_opportunity_score", data)
            self.assertIn("personal_fit_score", data)
            self.assertIn("analogue_data", data)
            self.assertIn("news_data", data)
            self.assertGreater(data["analogue_data"]["total_analogues_found"], 0)
            self.assertGreater(len(data["news_data"]["articles"]), 0)

    def test_news_service_and_sentiment(self):
        """Test real-time news retrieval, fallback resilience, and sentiment scoring."""
        from services.news_service import NewsService
        news = NewsService.get_company_news("TATAMOTORS")
        self.assertEqual(news["symbol"], "TATAMOTORS")
        self.assertIn("sentiment_score", news)
        self.assertIn("sentiment_label", news)
        self.assertGreater(len(news["articles"]), 0)

        # Test sentiment calculation explicitly
        mock_articles = [
            {"headline": "Company reports record profit and revenue beat", "summary": "Growth surge"},
            {"headline": "New product launch drives volume expansion", "summary": "Rally continues"}
        ]
        sentiment = NewsService._calculate_sentiment(mock_articles)
        self.assertEqual(sentiment["label"], "BULLISH")
        self.assertGreater(sentiment["score"], 0.0)

        mock_bearish = [
            {"headline": "Company suffers massive drop and miss", "summary": "Regulatory probe and lawsuit"}
        ]
        bear_sentiment = NewsService._calculate_sentiment(mock_bearish)
        self.assertEqual(bear_sentiment["label"], "BEARISH")
        self.assertLess(bear_sentiment["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
