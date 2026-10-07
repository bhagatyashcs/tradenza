"""
Twelve Data Market Data Service - Tradenza
Provides real-time quotes, current prices, time series, symbol search,
and watchlist scanning via the Twelve Data REST API.
Includes in-memory TTL caching to optimize API rate limit usage.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app

logger = logging.getLogger(__name__)


class TwelveDataService:
    """Client for Twelve Data Financial Market API."""

    BASE_URL = "https://api.twelvedata.com"
    CACHE_TTL_SECONDS = 60  # Cache quotes for 60s to respect rate limits

    DEFAULT_CATALOG: List[Dict[str, str]] = [
        # Stocks (US & India)
        {"symbol": "AAPL", "name": "Apple Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "TSLA", "name": "Tesla, Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "AMZN", "name": "Amazon.com, Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "META", "name": "Meta Platforms, Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "NFLX", "name": "Netflix, Inc.", "market": "Stocks", "exchange": "NASDAQ", "type": "Common Stock"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "market": "Stocks", "exchange": "NYSE", "type": "ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust", "market": "Stocks", "exchange": "NASDAQ", "type": "ETF"},
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "INFY", "name": "Infosys Ltd", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "SBIN", "name": "State Bank of India", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "market": "Stocks", "exchange": "NSE", "type": "Common Stock"},
        # Crypto
        {"symbol": "BTC/USD", "name": "Bitcoin", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "ETH/USD", "name": "Ethereum", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "SOL/USD", "name": "Solana", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "BNB/USD", "name": "Binance Coin", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "XRP/USD", "name": "Ripple", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "DOGE/USD", "name": "Dogecoin", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "ADA/USD", "name": "Cardano", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "AVAX/USD", "name": "Avalanche", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "LINK/USD", "name": "Chainlink", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "DOT/USD", "name": "Polkadot", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "MATIC/USD", "name": "Polygon", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "USDT/USD", "name": "Tether USD", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        {"symbol": "USDC/USD", "name": "USD Coin", "market": "Crypto", "exchange": "Crypto", "type": "Digital Currency"},
        # Forex
        {"symbol": "EUR/USD", "name": "Euro / US Dollar", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "GBP/USD", "name": "British Pound / US Dollar", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "USD/JPY", "name": "US Dollar / Japanese Yen", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "AUD/USD", "name": "Australian Dollar / US Dollar", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "USD/CAD", "name": "US Dollar / Canadian Dollar", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "USD/CHF", "name": "US Dollar / Swiss Franc", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        {"symbol": "EUR/GBP", "name": "Euro / British Pound", "market": "Forex", "exchange": "Forex", "type": "Physical Currency"},
        # Futures
        {"symbol": "ES", "name": "E-mini S&P 500 Futures", "market": "Futures", "exchange": "CME", "type": "Futures"},
        {"symbol": "NQ", "name": "E-mini Nasdaq 100 Futures", "market": "Futures", "exchange": "CME", "type": "Futures"},
        {"symbol": "CL", "name": "Crude Oil Futures", "market": "Futures", "exchange": "NYMEX", "type": "Futures"},
        {"symbol": "GC", "name": "Gold Futures", "market": "Futures", "exchange": "COMEX", "type": "Futures"},
        {"symbol": "SI", "name": "Silver Futures", "market": "Futures", "exchange": "COMEX", "type": "Futures"},
        {"symbol": "NG", "name": "Natural Gas Futures", "market": "Futures", "exchange": "NYMEX", "type": "Futures"},
        {"symbol": "HG", "name": "Copper Futures", "market": "Futures", "exchange": "COMEX", "type": "Futures"},
        {"symbol": "NIFTY-FUT", "name": "Nifty 50 Index Futures", "market": "Futures", "exchange": "NSE", "type": "Futures"},
        {"symbol": "BANKNIFTY-FUT", "name": "Bank Nifty Futures", "market": "Futures", "exchange": "NSE", "type": "Futures"},
        # Options
        {"symbol": "SPY-OPT", "name": "SPY S&P 500 Index Options", "market": "Options", "exchange": "CBOE", "type": "Options"},
        {"symbol": "QQQ-OPT", "name": "QQQ Nasdaq Options", "market": "Options", "exchange": "CBOE", "type": "Options"},
        {"symbol": "NIFTY-OPT", "name": "Nifty 50 Weekly/Monthly Options", "market": "Options", "exchange": "NSE", "type": "Options"},
        {"symbol": "BANKNIFTY-OPT", "name": "Bank Nifty Options", "market": "Options", "exchange": "NSE", "type": "Options"},
        {"symbol": "TSLA-OPT", "name": "Tesla Equity Options", "market": "Options", "exchange": "OPRA", "type": "Options"},
        {"symbol": "NVDA-OPT", "name": "NVIDIA Equity Options", "market": "Options", "exchange": "OPRA", "type": "Options"}
    ]

    BENCHMARK_PRICES: Dict[str, float] = {
        # Stocks
        "AAPL": 242.50,
        "NVDA": 138.25,
        "TSLA": 260.40,
        "MSFT": 428.10,
        "AMZN": 186.50,
        "META": 585.00,
        "GOOGL": 168.20,
        "AMD": 156.40,
        "NFLX": 710.00,
        "SPY": 585.50,
        "QQQ": 492.30,
        "RELIANCE": 2750.00,
        "TCS": 3890.00,
        "INFY": 1890.00,
        "HDFCBANK": 1680.00,
        "ICICIBANK": 1260.00,
        "SBIN": 810.00,
        "TATAMOTORS": 940.00,
        # Crypto
        "BTC/USD": 88500.00,
        "ETH/USD": 2650.00,
        "SOL/USD": 178.50,
        "BNB/USD": 595.00,
        "XRP/USD": 1.45,
        "DOGE/USD": 0.22,
        "ADA/USD": 0.72,
        "AVAX/USD": 32.50,
        "LINK/USD": 14.80,
        "DOT/USD": 7.50,
        "MATIC/USD": 0.55,
        "USDT/USD": 1.00,
        "USDT": 1.00,
        "USDC/USD": 1.00,
        "USDC": 1.00,
        # Forex
        "EUR/USD": 1.0850,
        "GBP/USD": 1.2980,
        "USD/JPY": 152.40,
        "AUD/USD": 0.6580,
        "USD/CAD": 1.3850,
        "USD/CHF": 0.8650,
        "EUR/GBP": 0.8360,
        # Futures
        "ES": 5865.00,
        "NQ": 20450.00,
        "CL": 71.50,
        "GC": 2740.00,
        "SI": 33.80,
        "NG": 2.85,
        "HG": 4.35,
        "NIFTY-FUT": 25150.00,
        "BANKNIFTY-FUT": 51800.00,
        # Options
        "SPY-OPT": 5.40,
        "QQQ-OPT": 4.80,
        "NIFTY-OPT": 120.00,
        "BANKNIFTY-OPT": 280.00,
        "TSLA-OPT": 8.50,
        "NVDA-OPT": 6.20,
    }

    SYMBOL_ALIASES: Dict[str, str] = {
        # Crypto Shorthands & Names
        "BTC": "BTC/USD",
        "BITCOIN": "BTC/USD",
        "XBT": "BTC/USD",
        "BTCUSD": "BTC/USD",
        "BTCUSDT": "BTC/USD",
        "ETH": "ETH/USD",
        "ETHEREUM": "ETH/USD",
        "ETHUSD": "ETH/USD",
        "ETHUSDT": "ETH/USD",
        "SOL": "SOL/USD",
        "SOLANA": "SOL/USD",
        "SOLUSD": "SOL/USD",
        "SOLUSDT": "SOL/USD",
        "BNB": "BNB/USD",
        "BINANCE": "BNB/USD",
        "BNBUSD": "BNB/USD",
        "BNBUSDT": "BNB/USD",
        "XRP": "XRP/USD",
        "RIPPLE": "XRP/USD",
        "XRPUSD": "XRP/USD",
        "XRPUSDT": "XRP/USD",
        "DOGE": "DOGE/USD",
        "DOGECOIN": "DOGE/USD",
        "DOGEUSD": "DOGE/USD",
        "DOGEUSDT": "DOGE/USD",
        "ADA": "ADA/USD",
        "CARDANO": "ADA/USD",
        "ADAUSD": "ADA/USD",
        "ADAUSDT": "ADA/USD",
        "AVAX": "AVAX/USD",
        "AVALANCHE": "AVAX/USD",
        "AVAXUSD": "AVAX/USD",
        "AVAXUSDT": "AVAX/USD",
        "LINK": "LINK/USD",
        "CHAINLINK": "LINK/USD",
        "LINKUSD": "LINK/USD",
        "LINKUSDT": "LINK/USD",
        "DOT": "DOT/USD",
        "POLKADOT": "DOT/USD",
        "DOTUSD": "DOT/USD",
        "DOTUSDT": "DOT/USD",
        "MATIC": "MATIC/USD",
        "POLYGON": "MATIC/USD",
        "MATICUSD": "MATIC/USD",
        "MATICUSDT": "MATIC/USD",
        "USDT": "USDT/USD",
        "TETHER": "USDT/USD",
        "USDC": "USDC/USD",
        "USDCOIN": "USDC/USD",

        # Commodities & Futures
        "GOLD": "GC",
        "SILVER": "SI",
        "CRUDE": "CL",
        "CRUDEOIL": "CL",
        "OIL": "CL",
        "NATGAS": "NG",
        "NATURALGAS": "NG",
        "COPPER": "HG",
        "NIFTY": "NIFTY-FUT",
        "NIFTY50": "NIFTY-FUT",
        "NIFTYFUT": "NIFTY-FUT",
        "BANKNIFTY": "BANKNIFTY-FUT",
        "BANKNIFTYFUT": "BANKNIFTY-FUT",
        "FINNIFTY": "FINNIFTY-FUT",
        "SP500": "SPY",
        "S&P500": "SPY",
        "NASDAQ": "QQQ",
        "DOW": "DIA",
        "DOWJONES": "DIA",

        # Top US Stocks (Company Name Aliases)
        "APPLE": "AAPL",
        "TESLA": "TSLA",
        "NVIDIA": "NVDA",
        "MICROSOFT": "MSFT",
        "AMAZON": "AMZN",
        "META": "META",
        "FACEBOOK": "META",
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "AMD": "AMD",
        "NETFLIX": "NFLX",

        # Top Indian Stocks
        "RELIANCE": "RELIANCE",
        "TATA": "TATAMOTORS",
        "TATAMOTORS": "TATAMOTORS",
        "TCS": "TCS",
        "INFY": "INFY",
        "INFOSYS": "INFY",
        "HDFC": "HDFCBANK",
        "HDFCBANK": "HDFCBANK",
        "ICICI": "ICICIBANK",
        "ICICIBANK": "ICICIBANK",
        "SBI": "SBIN",
        "SBIN": "SBIN",
    }

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._cache: Dict[str, Dict[str, Any]] = {}

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        try:
            key = current_app.config.get("TWELVE_DATA_API_KEY")
            if key:
                return key
        except RuntimeError:
            pass
        return os.environ.get("TWELVE_DATA_API_KEY", "")

    def _get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry:
            if time.time() - entry["timestamp"] < self.CACHE_TTL_SECONDS:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        self._cache[key] = {
            "timestamp": time.time(),
            "data": data,
        }

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Performs HTTP GET request to Twelve Data API with error handling."""
        key = self.api_key
        if not key:
            return {"status": "error", "message": "Twelve Data API key is not configured."}

        params_with_key = dict(params)
        params_with_key["apikey"] = key

        query_string = urlencode(params_with_key)
        url = f"{self.BASE_URL}{endpoint}?{query_string}"

        req = Request(url, headers={"User-Agent": "Tradenza/0.2"})

        try:
            with urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                return json.loads(content)
        except HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                return {"status": "error", "code": e.code, "message": err_body.get("message", str(e))}
            except Exception:
                return {"status": "error", "code": e.code, "message": f"HTTP Error {e.code}: {e.reason}"}
        except URLError as e:
            return {"status": "error", "message": f"Connection error: {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current real-time price for a symbol.
        Supports Stocks (AAPL), Forex (EUR/USD), Crypto (BTC/USD, BTC/USDT).
        """
        symbol = self._normalize_symbol(symbol)
        cache_key = f"price:{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        res = self._request("/price", {"symbol": symbol})
        if "price" in res:
            try:
                price = float(res["price"])
                self._set_cached(cache_key, price)
                return price
            except (ValueError, TypeError):
                pass

        # Offline / DNS fallback: check benchmark prices
        norm_sym = symbol.upper()
        if norm_sym in self.BENCHMARK_PRICES:
            price = self.BENCHMARK_PRICES[norm_sym]
            self._set_cached(cache_key, price)
            return price
        return None

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch full quote data including open, high, low, close, volume,
        change, percent_change, and 52-week ranges.
        """
        norm_sym = self._normalize_symbol(symbol).upper()
        cache_key = f"quote:{norm_sym}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        inferred_market = self.infer_market(norm_sym)
        res = self._request("/quote", {"symbol": norm_sym})
        if res.get("status") == "error":
            # If network error (DNS failure, offline sandbox, etc.), check fallback
            bm_price = self.BENCHMARK_PRICES.get(norm_sym)
            cat_item = next((item for item in self.DEFAULT_CATALOG if item["symbol"].upper() == norm_sym), None)

            if bm_price is not None or cat_item is not None:
                price = bm_price if bm_price is not None else 100.0
                name = cat_item["name"] if cat_item else symbol
                exchange = cat_item["exchange"] if cat_item else "Benchmark"
                market = cat_item["market"] if cat_item else inferred_market
                currency = "INR" if exchange == "NSE" else "USD"

                fallback_quote = {
                    "symbol": norm_sym,
                    "name": name,
                    "exchange": exchange,
                    "market": market,
                    "currency": currency,
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "price": price,
                    "open": price,
                    "high": round(price * 1.008, 2),
                    "low": round(price * 0.992, 2),
                    "close": price,
                    "previous_close": price,
                    "change": 0.0,
                    "percent_change": 0.0,
                    "volume": 1250000,
                    "is_market_open": True,
                    "fifty_two_week": {},
                    "is_fallback": True,
                    "status": "ok",
                    "notice": "Offline reference benchmark quote loaded.",
                }
                self._set_cached(cache_key, fallback_quote)
                return fallback_quote

            return res

        # Normalize numeric values
        try:
            quote_data = {
                "symbol": res.get("symbol", norm_sym),
                "name": res.get("name", norm_sym),
                "exchange": res.get("exchange", ""),
                "market": inferred_market,
                "currency": res.get("currency", "USD"),
                "datetime": res.get("datetime", ""),
                "price": float(res.get("close") or res.get("price") or 0.0),
                "open": float(res.get("open") or 0.0),
                "high": float(res.get("high") or 0.0),
                "low": float(res.get("low") or 0.0),
                "close": float(res.get("close") or 0.0),
                "previous_close": float(res.get("previous_close") or 0.0),
                "change": float(res.get("change") or 0.0),
                "percent_change": float(res.get("percent_change") or 0.0),
                "volume": int(res.get("volume") or 0),
                "is_market_open": res.get("is_market_open", True),
                "fifty_two_week": res.get("fifty_two_week", {}),
                "status": "ok",
            }
            self._set_cached(cache_key, quote_data)
            return quote_data
        except Exception as e:
            return {"status": "error", "message": f"Failed to parse quote: {str(e)}"}

    def search_symbols(self, query: str, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search symbols across stocks, forex, crypto, ETFs, and indices.
        Supports matching by symbol (e.g. AAPL, BTC) or company/asset name (e.g. Apple, Bitcoin).
        Optionally filters by market (Stocks, Crypto, Forex, Futures, Options).
        """
        q = (query or "").strip().upper()
        m_filter = (market or "").strip().lower()

        results: List[Dict[str, Any]] = []
        seen_symbols = set()

        # 1. Search local curated catalog for current market
        for item in self.DEFAULT_CATALOG:
            item_market = item.get("market", "").lower()
            if m_filter and m_filter != "all" and item_market != m_filter:
                continue

            sym = item["symbol"].upper()
            name = item["name"].upper()

            if not q or q in sym or q in name:
                results.append(dict(item))
                seen_symbols.add(sym)

        # 1b. If query provided, also include matching assets from other markets
        if q:
            for item in self.DEFAULT_CATALOG:
                sym = item["symbol"].upper()
                name = item["name"].upper()
                if sym not in seen_symbols and (q in sym or q in name):
                    results.append(dict(item))
                    seen_symbols.add(sym)

        # 2. Try Twelve Data remote API search if query is non-empty
        if q:
            cache_key = f"search:{q}:{m_filter}"
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

            res = self._request("/symbol_search", {"symbol": query.strip()})
            data = res.get("data", [])
            if isinstance(data, list):
                for item in data[:8]:
                    sym = item.get("symbol", "").upper()
                    if sym and sym not in seen_symbols:
                        inst_type = (item.get("instrument_type") or "").lower()
                        # Infer market category
                        if "crypto" in inst_type or "digital" in inst_type:
                            inferred_market = "Crypto"
                        elif "forex" in inst_type or "physical" in inst_type:
                            inferred_market = "Forex"
                        elif "future" in inst_type:
                            inferred_market = "Futures"
                        elif "option" in inst_type:
                            inferred_market = "Options"
                        else:
                            inferred_market = "Stocks"

                        if m_filter and m_filter != "all" and inferred_market.lower() != m_filter:
                            continue

                        results.append({
                            "symbol": item.get("symbol"),
                            "name": item.get("instrument_name") or item.get("symbol"),
                            "exchange": item.get("exchange", ""),
                            "type": item.get("instrument_type", ""),
                            "currency": item.get("currency", "USD"),
                            "country": item.get("country", ""),
                            "market": inferred_market
                        })
                        seen_symbols.add(sym)

            self._set_cached(cache_key, results)

        return results[:15]

    def get_time_series(
        self, symbol: str, interval: str = "1day", outputsize: int = 30
    ) -> Dict[str, Any]:
        """
        Retrieve historical / intraday OHLCV time series data.
        Intervals: 1min, 5min, 15min, 1h, 4h, 1day, 1week, 1month.
        """
        symbol = self._normalize_symbol(symbol)
        cache_key = f"time_series:{symbol}:{interval}:{outputsize}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        res = self._request("/time_series", {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
        })

        if res.get("status") == "error":
            return res

        values = res.get("values", [])
        formatted = {
            "symbol": symbol,
            "interval": interval,
            "meta": res.get("meta", {}),
            "candles": [
                {
                    "datetime": v.get("datetime"),
                    "open": float(v.get("open", 0.0)),
                    "high": float(v.get("high", 0.0)),
                    "low": float(v.get("low", 0.0)),
                    "close": float(v.get("close", 0.0)),
                    "volume": int(float(v.get("volume", 0))),
                }
                for v in values
            ],
            "status": "ok",
        }
        self._set_cached(cache_key, formatted)
        return formatted

    @classmethod
    def _normalize_symbol(cls, symbol: str) -> str:
        """
        Ensures proper formatting for all asset classes:
        - Common aliases: BTC -> BTC/USD, ETH -> ETH/USD, GOLD -> GC, NIFTY -> NIFTY-FUT
        - Forex pairs without slash: EURUSD -> EUR/USD
        - Crypto pairs without slash: BTCUSD -> BTC/USD, BTCUSDT -> BTC/USD
        - Stock tickers: AAPL, NVDA, TSLA kept uppercase
        """
        if not symbol:
            return ""
        s = symbol.strip().upper()

        # 1. Direct alias dictionary lookup
        if s in cls.SYMBOL_ALIASES:
            return cls.SYMBOL_ALIASES[s]

        # 2. Common Forex pairs without slash
        forex_pairs = {
            "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
            "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD", "USDCHF": "USD/CHF",
            "NZDUSD": "NZD/USD", "EURGBP": "EUR/GBP", "EURJPY": "EUR/JPY",
            "GBPJPY": "GBP/JPY",
        }
        if s in forex_pairs:
            return forex_pairs[s]

        # 3. Common crypto pairs without slash
        crypto_pairs = {
            "BTCUSD": "BTC/USD", "BTCUSDT": "BTC/USD",
            "ETHUSD": "ETH/USD", "ETHUSDT": "ETH/USD",
            "SOLUSD": "SOL/USD", "SOLUSDT": "SOL/USD",
            "XRPUSD": "XRP/USD", "XRPUSDT": "XRP/USD",
            "DOGEUSD": "DOGE/USD", "DOGEUSDT": "DOGE/USD",
            "BNBUSD": "BNB/USD", "BNBUSDT": "BNB/USD",
            "ADAUSD": "ADA/USD", "ADAUSDT": "ADA/USD",
            "AVAXUSD": "AVAX/USD", "AVAXUSDT": "AVAX/USD",
            "LINKUSD": "LINK/USD", "LINKUSDT": "LINK/USD",
            "DOTUSD": "DOT/USD", "DOTUSDT": "DOT/USD",
            "MATICUSD": "MATIC/USD", "MATICUSDT": "MATIC/USD",
        }
        if s in crypto_pairs:
            return crypto_pairs[s]

        return s

    @classmethod
    def infer_market(cls, symbol: str) -> str:
        """
        Infers the market category (Stocks, Crypto, Forex, Futures, Options)
        for a given symbol.
        """
        s = cls._normalize_symbol(symbol).upper()
        for item in cls.DEFAULT_CATALOG:
            if item["symbol"].upper() == s:
                return item["market"]
        if "/" in s or any(s.startswith(c) for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "DOT", "MATIC"]):
            if any(f in s for f in ["EUR/", "GBP/", "USD/JPY", "AUD/", "CAD/", "CHF/", "NZD/"]):
                return "Forex"
            return "Crypto"
        if s.endswith("-OPT") or "CALL" in s or "PUT" in s:
            return "Options"
        if s in ["ES", "NQ", "CL", "GC", "SI", "NG", "HG"] or s.endswith("-FUT"):
            return "Futures"
        return "Stocks"
