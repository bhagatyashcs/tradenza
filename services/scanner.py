"""
Market Scanner Service - Tradenza
Scans market instruments using Twelve Data real-time market data API.
Provides watchlist snapshots, top movers, and asset class summaries.
"""

from typing import Any, Dict, List, Optional
from services.market_data_service import TwelveDataService


class MarketScannerService:
    """Service to scan and monitor financial instruments."""

    DEFAULT_WATCHLISTS = {
        "STOCKS": ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META", "GOOGL"],
        "FOREX": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"],
        "CRYPTO": ["BTC/USD", "ETH/USD", "SOL/USD"],
        "INDICES": ["SPX", "IXIC", "DJI"],
    }

    def __init__(self, market_data_service: Optional[TwelveDataService] = None):
        self.market_data = market_data_service or TwelveDataService()

    def scan_watchlist(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Scans a list of symbols and returns their current quotes and performance.
        """
        results = []
        for sym in symbols:
            quote = self.market_data.get_quote(sym)
            if quote.get("status") == "ok":
                results.append(quote)
            else:
                # Fallback to simple price if quote has restrictions
                price = self.market_data.get_realtime_price(sym)
                if price is not None:
                    results.append({
                        "symbol": sym,
                        "name": sym,
                        "price": price,
                        "change": 0.0,
                        "percent_change": 0.0,
                        "status": "ok",
                    })
        return results

    def get_market_overview(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns categorized market overview for major asset classes.
        """
        overview = {}
        for category, symbols in self.DEFAULT_WATCHLISTS.items():
            overview[category] = self.scan_watchlist(symbols)
        return overview

    def get_top_movers(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Computes top gainers and losers from the scanned watchlists.
        """
        all_quotes = []
        for symbols in self.DEFAULT_WATCHLISTS.values():
            all_quotes.extend(self.scan_watchlist(symbols))

        # Filter valid percent changes
        valid_quotes = [q for q in all_quotes if "percent_change" in q]
        sorted_by_change = sorted(valid_quotes, key=lambda x: x.get("percent_change", 0.0), reverse=True)

        gainers = [q for q in sorted_by_change if q.get("percent_change", 0.0) > 0][:limit]
        losers = [q for q in reversed(sorted_by_change) if q.get("percent_change", 0.0) < 0][:limit]

        return {
            "gainers": gainers,
            "losers": losers,
        }
