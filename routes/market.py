from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from services.market_data_service import TwelveDataService
from services.scanner import MarketScannerService

market_bp = Blueprint("market", __name__, url_prefix="/market")


@market_bp.route("/price")
def get_price():
    """
    Returns current real-time price for a symbol.
    Example: GET /market/price?symbol=AAPL or ?symbol=BTC/USD
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"status": "error", "message": "Symbol parameter is required."}), 400

    service = TwelveDataService()
    norm_symbol = service._normalize_symbol(symbol)
    price = service.get_realtime_price(norm_symbol)
    if price is not None:
        return jsonify({
            "status": "ok",
            "symbol": norm_symbol.upper(),
            "query": symbol,
            "price": price,
            "market": service.infer_market(norm_symbol)
        })
    return jsonify({"status": "error", "message": f"Could not fetch price for symbol: {symbol}"}), 404


@market_bp.route("/quote")
def get_quote():
    """
    Returns complete quote snapshot for a symbol.
    Example: GET /market/quote?symbol=NVDA
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"status": "error", "message": "Symbol parameter is required."}), 400

    service = TwelveDataService()
    quote = service.get_quote(symbol)
    if quote.get("status") == "error":
        raw_msg = str(quote.get("message", ""))
        if "Connection error" in raw_msg or "name resolution" in raw_msg or "URLError" in raw_msg:
            quote["message"] = f"Market feed unreachable for {symbol}. Please enter price manually or select an instrument from the catalog."
        return jsonify(quote), 400
    return jsonify(quote)


@market_bp.route("/search")
def search_symbols():
    """
    Symbol autocomplete and lookup across financial exchanges.
    Example: GET /market/search?query=Apple&market=Stocks
    """
    query = request.args.get("query", "").strip()
    market = request.args.get("market", "").strip()

    service = TwelveDataService()
    results = service.search_symbols(query, market=market)
    return jsonify(results)


@market_bp.route("/catalog")
def get_catalog():
    """
    Returns curated instrument catalog grouped by market.
    """
    service = TwelveDataService()
    return jsonify(service.DEFAULT_CATALOG)


@market_bp.route("/history")
def get_history():
    """
    Returns historical candlestick OHLCV data.
    Example: GET /market/history?symbol=AAPL&interval=1day&outputsize=30
    """
    symbol = request.args.get("symbol", "").strip()
    interval = request.args.get("interval", "1day").strip()
    outputsize = request.args.get("outputsize", 30, type=int)

    if not symbol:
        return jsonify({"status": "error", "message": "Symbol parameter is required."}), 400

    service = TwelveDataService()
    series = service.get_time_series(symbol, interval=interval, outputsize=outputsize)
    if series.get("status") == "error":
        return jsonify(series), 400
    return jsonify(series)


@market_bp.route("/scanner")
@login_required
def scanner():
    """
    Renders interactive Market Scanner overview.
    """
    scanner_service = MarketScannerService()
    overview = scanner_service.get_market_overview()
    movers = scanner_service.get_top_movers(limit=5)

    return render_template(
        "market/scanner.html",
        overview=overview,
        movers=movers
    )

@market_bp.route('/terminal')
@login_required
def pro_terminal():
    return render_template('market/terminal.html')

