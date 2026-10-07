import unittest
from unittest.mock import patch, MagicMock

from core.factory import create_app
from extensions import db
from services.market_data_service import TwelveDataService
from services.scanner import MarketScannerService


class MarketDataTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "TWELVE_DATA_API_KEY": "test-mock-api-key",
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_symbol_normalization(self):
        self.assertEqual(TwelveDataService._normalize_symbol("eurusd"), "EUR/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("GBPUSD"), "GBP/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("btcusd"), "BTC/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("btcusdt"), "BTC/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("btc"), "BTC/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("ETH"), "ETH/USD")
        self.assertEqual(TwelveDataService._normalize_symbol("gold"), "GC")
        self.assertEqual(TwelveDataService._normalize_symbol("nifty"), "NIFTY-FUT")
        self.assertEqual(TwelveDataService._normalize_symbol("apple"), "AAPL")
        self.assertEqual(TwelveDataService._normalize_symbol("tesla"), "TSLA")
        self.assertEqual(TwelveDataService._normalize_symbol("AAPL"), "AAPL")
        self.assertEqual(TwelveDataService._normalize_symbol("nvda "), "NVDA")

        # Test market inference
        self.assertEqual(TwelveDataService.infer_market("AAPL"), "Stocks")
        self.assertEqual(TwelveDataService.infer_market("BTC"), "Crypto")
        self.assertEqual(TwelveDataService.infer_market("EURUSD"), "Forex")
        self.assertEqual(TwelveDataService.infer_market("GOLD"), "Futures")
        self.assertEqual(TwelveDataService.infer_market("SPY-OPT"), "Options")

    def test_cache_mechanism(self):
        service = TwelveDataService(api_key="dummy")
        service._set_cached("test_key", {"price": 150.0})

        cached = service._get_cached("test_key")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["price"], 150.0)

        # Non-existent key
        self.assertIsNone(service._get_cached("missing_key"))

    @patch.object(TwelveDataService, "_request")
    def test_get_realtime_price(self, mock_request):
        mock_request.return_value = {"price": "245.50"}

        service = TwelveDataService(api_key="mock-key")
        price = service.get_realtime_price("AAPL")

        self.assertEqual(price, 245.50)
        mock_request.assert_called_once_with("/price", {"symbol": "AAPL"})

    @patch.object(TwelveDataService, "_request")
    def test_get_quote(self, mock_request):
        mock_request.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "close": "250.00",
            "open": "248.00",
            "high": "252.00",
            "low": "247.00",
            "change": "2.00",
            "percent_change": "0.80",
            "volume": "50000000",
            "status": "ok"
        }

        service = TwelveDataService(api_key="mock-key")
        quote = service.get_quote("AAPL")

        self.assertEqual(quote["status"], "ok")
        self.assertEqual(quote["symbol"], "AAPL")
        self.assertEqual(quote["price"], 250.00)
        self.assertEqual(quote["percent_change"], 0.80)

    @patch.object(TwelveDataService, "get_quote")
    def test_market_scanner_top_movers(self, mock_quote):
        def side_effect(symbol):
            data = {
                "AAPL": {"symbol": "AAPL", "name": "Apple", "price": 200.0, "percent_change": 3.5, "status": "ok"},
                "NVDA": {"symbol": "NVDA", "name": "Nvidia", "price": 120.0, "percent_change": -4.2, "status": "ok"},
                "EUR/USD": {"symbol": "EUR/USD", "name": "Euro", "price": 1.08, "percent_change": 0.2, "status": "ok"},
            }
            return data.get(symbol, {"symbol": symbol, "name": symbol, "price": 100.0, "percent_change": 0.0, "status": "ok"})

        mock_quote.side_effect = side_effect
        scanner = MarketScannerService()
        scanner.DEFAULT_WATCHLISTS = {
            "STOCKS": ["AAPL", "NVDA"],
            "FOREX": ["EUR/USD"]
        }

        movers = scanner.get_top_movers(limit=2)
        self.assertIn("gainers", movers)
        self.assertIn("losers", movers)
        self.assertTrue(len(movers["gainers"]) > 0)
        self.assertEqual(movers["gainers"][0]["symbol"], "AAPL")
        self.assertEqual(movers["losers"][0]["symbol"], "NVDA")

    @patch.object(TwelveDataService, "get_realtime_price")
    def test_route_market_price(self, mock_price):
        mock_price.return_value = 195.50

        response = self.client.get("/market/price?symbol=AAPL")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["status"], "ok")
        self.assertEqual(json_data["price"], 195.50)

    def test_route_market_price_missing_symbol(self):
        response = self.client.get("/market/price")
        self.assertEqual(response.status_code, 400)

    @patch.object(TwelveDataService, "_request")
    def test_get_quote_offline_benchmark_fallback(self, mock_request):
        mock_request.return_value = {"status": "error", "message": "Connection error: [Errno -3] Temporary failure in name resolution"}

        service = TwelveDataService(api_key="mock-key")
        quote = service.get_quote("AAPL")

        self.assertEqual(quote["status"], "ok")
        self.assertTrue(quote["is_fallback"])
        self.assertEqual(quote["symbol"], "AAPL")
        self.assertEqual(quote["price"], TwelveDataService.BENCHMARK_PRICES["AAPL"])

    @patch.object(TwelveDataService, "_request")
    def test_route_quote_offline_benchmark_fallback(self, mock_request):
        mock_request.return_value = {"status": "error", "message": "Connection error: [Errno -3] Temporary failure in name resolution"}

        response = self.client.get("/market/quote?symbol=AAPL")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data.get("is_fallback"))
        self.assertEqual(data["symbol"], "AAPL")

    @patch.object(TwelveDataService, "_request")
    def test_route_market_price_shorthand_alias(self, mock_request):
        mock_request.return_value = {"status": "error", "message": "Offline"}

        response = self.client.get("/market/price?symbol=btc")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["symbol"], "BTC/USD")
        self.assertEqual(data["market"], "Crypto")
        self.assertEqual(data["price"], TwelveDataService.BENCHMARK_PRICES["BTC/USD"])

    @patch.object(TwelveDataService, "_request")
    def test_route_quote_shorthand_alias(self, mock_request):
        mock_request.return_value = {"status": "error", "message": "Offline"}

        response = self.client.get("/market/quote?symbol=gold")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["symbol"], "GC")
        self.assertEqual(data["market"], "Futures")
        self.assertEqual(data["price"], TwelveDataService.BENCHMARK_PRICES["GC"])

    def test_search_symbols_cross_market(self):
        service = TwelveDataService(api_key="test-key")
        # Search for btc should find Bitcoin in Crypto even if filtered under Stocks
        results = service.search_symbols("btc", market="Stocks")
        self.assertTrue(any(r["symbol"] == "BTC/USD" for r in results))

        # Search for gold should find Gold Futures
        results_gold = service.search_symbols("gold")
        self.assertTrue(any(r["symbol"] == "GC" for r in results_gold))


if __name__ == "__main__":
    unittest.main()
