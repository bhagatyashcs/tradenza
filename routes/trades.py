from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    make_response,
    current_app
)

from flask_login import (
    login_required,
    current_user
)

from forms.trade_forms import TradeForm, CloseTradeForm
from forms.search_forms import SearchTradeForm
from forms.filter_form import FilterTradeForm
from forms.import_form import CSVImportForm

from services.trade_service import TradeService
from services.tradebuddy import TradeBuddyService
from services.portfolio_service import PortfolioService
from services.review_service import ReviewService

from utils.csv_export import export_trades_to_csv
from utils.csv_import import parse_trades_csv
from models.trade import Trade
from extensions import db


trade_bp = Blueprint(
    "trade",
    __name__,
    url_prefix="/trades"
)


@trade_bp.route("/")
@login_required
def trade_history():

    search_form = SearchTradeForm()
    filter_form = FilterTradeForm()

    page = request.args.get(
        "page",
        1,
        type=int
    )

    query = request.args.get(
        "query",
        ""
    ).strip()

    filters = {
        "market": request.args.get("market", ""),
        "trade_type": request.args.get("trade_type", ""),
        "status": request.args.get("status", "")
    }

    if any(filters.values()):

        trades = TradeService.filter_trades(
            current_user,
            filters,
            page=page,
            per_page=10
        )

    elif query:

        trades = TradeService.search_trades(
            current_user,
            query,
            page=page,
            per_page=10
        )

    else:

        trades = TradeService.get_user_trades(
            current_user,
            page=page,
            per_page=10
        )

    filter_form.market.data = filters["market"]
    filter_form.trade_type.data = filters["trade_type"]
    filter_form.status.data = filters["status"]

    return render_template(
        "trade/history.html",
        trades=trades,
        search_form=search_form,
        filter_form=filter_form,
        query=query
    )


@trade_bp.route("/export")
@login_required
def export_trades():

    trades = TradeService.get_recent_trades(
        current_user,
        limit=100000
    )

    csv_data = export_trades_to_csv(trades)

    response = make_response(csv_data)

    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=trades.csv"

    response.headers[
        "Content-Type"
    ] = "text/csv"

    return response


@trade_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_trades():
    form = CSVImportForm()
    if form.validate_on_submit():
        file = form.csv_file.data
        if not file or not file.filename:
            flash("Please choose a CSV file to upload.", "danger")
            return redirect(url_for("trade.import_trades"))

        if not file.filename.lower().endswith(".csv"):
            flash("Only .csv files are supported.", "danger")
            return redirect(url_for("trade.import_trades"))

        parsed, errors = parse_trades_csv(file.stream)
        if not parsed:
            err_msg = " | ".join(errors[:3]) if errors else "No valid trades found in file."
            flash(f"Import failed: {err_msg}", "danger")
            return redirect(url_for("trade.import_trades"))

        imported_count = 0
        for item in parsed:
            t = Trade(
                user_id=current_user.id,
                market=item["market"],
                symbol=item["symbol"],
                trade_type=item["trade_type"],
                entry_price=item["entry_price"],
                exit_price=item["exit_price"],
                quantity=item["quantity"],
                stop_loss=item.get("stop_loss"),
                target=item.get("target"),
                strategy=item.get("strategy"),
                notes=item.get("notes"),
                status=item["status"],
                profit_loss=item.get("profit_loss"),
                created_at=item["created_at"],
                entry_time=item["entry_time"],
                exit_time=item.get("exit_time"),
            )
            db.session.add(t)
            imported_count += 1

        db.session.commit()
        TradeService._refresh_user_data(current_user)

        flash(f"Successfully imported {imported_count} trades into your journal!", "success")
        return redirect(url_for("trade.trade_history"))
    elif request.method == "POST" and form.errors:
        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{err}", "danger")

    return render_template("trade/import_trades.html", form=form)


@trade_bp.route("/evidence_board")
@login_required
def evidence_board():
    from services.evidence_board import EvidenceBoardService
    from flask import jsonify

    symbol = request.args.get("symbol", "AAPL")
    strategy = request.args.get("strategy") or request.args.get("setup") or "Breakout"
    try:
        price = float(request.args.get("price", 100.0))
    except (ValueError, TypeError):
        price = 100.0
    try:
        sl = float(request.args.get("stop_loss")) if request.args.get("stop_loss") else None
    except (ValueError, TypeError):
        sl = None
    try:
        target = float(request.args.get("target")) if request.args.get("target") else None
    except (ValueError, TypeError):
        target = None

    board_data = EvidenceBoardService.synthesize_evidence_board(
        user=current_user,
        symbol=symbol,
        setup_type=strategy,
        entry_price=price,
        stop_loss=sl,
        target=target
    )
    return jsonify(board_data)


@trade_bp.route("/institutional_blueprint")
@login_required
def institutional_blueprint():
    from engines.institutional_trade_planner import InstitutionalTradePlanner
    from flask import jsonify

    symbol = request.args.get("symbol", "AAPL")
    strategy = request.args.get("strategy") or request.args.get("setup") or "Breakout"
    trade_type = request.args.get("type") or request.args.get("trade_type") or "BUY"
    try:
        price = float(request.args.get("price", 100.0))
    except (ValueError, TypeError):
        price = 100.0
    try:
        sl = float(request.args.get("stop_loss")) if request.args.get("stop_loss") else None
    except (ValueError, TypeError):
        sl = None
    try:
        target = float(request.args.get("target")) if request.args.get("target") else None
    except (ValueError, TypeError):
        target = None

    blueprint = InstitutionalTradePlanner.build_institutional_blueprint(
        user=current_user,
        symbol=symbol,
        setup_type=strategy,
        entry_price=price,
        stop_loss=sl,
        target=target,
        trade_type=trade_type
    )
    return jsonify(blueprint)


@trade_bp.route("/<int:trade_id>/pilot_telemetry")
@login_required
def pilot_telemetry(trade_id):
    from services.active_trade_pilot import ActiveTradePilot
    from flask import jsonify

    trade = TradeService.get_trade(trade_id, current_user)
    if not trade:
        return jsonify({"error": "Trade not found"}), 404

    price_str = request.args.get("price")
    if price_str:
        try:
            current_price = float(price_str)
        except (ValueError, TypeError):
            current_price = float(trade.entry_price or 100.0)
    else:
        from services.market_data_service import TwelveDataService
        quote = TwelveDataService().get_quote(trade.symbol)
        current_price = float(quote.get("price") or trade.entry_price or 100.0)

    telemetry = ActiveTradePilot.evaluate_open_position(trade, current_price)

    consult_ai = request.args.get("consult_ai") == "true"
    if consult_ai:
        ai_advice = ActiveTradePilot.consult_active_pilot_ai(current_user, trade, telemetry)
        telemetry["ai_advice"] = ai_advice

    return jsonify(telemetry)


@trade_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_trade():

    form = TradeForm()

    if request.method == "GET":
        symbol_param = request.args.get("symbol")
        price_param = request.args.get("price")
        market_param = request.args.get("market")
        type_param = request.args.get("type") or request.args.get("trade_type")

        if symbol_param:
            form.symbol.data = symbol_param
        if price_param:
            try:
                form.entry_price.data = float(price_param)
            except (ValueError, TypeError):
                pass
        if market_param:
            form.market.data = market_param
        if type_param and type_param.upper() in ["BUY", "SELL"]:
            form.trade_type.data = type_param.upper()

    if form.validate_on_submit():

        TradeService.create_trade(
            current_user,
            form
        )

        flash(
            "Trade saved successfully!",
            "success"
        )

        return redirect(
            url_for("trade.trade_history")
        )

    cooldown = TradeBuddyService.check_cooldown_status(current_user)
    portfolio = PortfolioService.get_or_create_portfolio(current_user)
    account_balance = portfolio.current_balance or portfolio.starting_balance or 10000.0

    return render_template(
        "trade/new_trade.html",
        form=form,
        cooldown=cooldown,
        account_balance=account_balance,
        api_key=current_app.config.get("TWELVE_DATA_API_KEY", "")
    )


@trade_bp.route("/<int:trade_id>")
@login_required
def trade_details(trade_id):

    trade = TradeService.get_trade(
        trade_id,
        current_user
    )

    if trade is None:

        flash(
            "Trade not found.",
            "danger"
        )

        return redirect(
            url_for("trade.trade_history")
        )

    review = ReviewService.generate_review(
        trade
    )

    post_mortem = None
    pilot_telemetry_data = None
    target_ladder_data = None

    if trade.status == "CLOSED":
        from services.ai_trade_auditor import AiTradeAuditor
        post_mortem = AiTradeAuditor.audit_trade(trade)
        post_mortem = AiTradeAuditor.enrich_with_deepseek_audit(trade, post_mortem, current_user)
    else:
        from services.active_trade_pilot import ActiveTradePilot
        from engines.institutional_trade_planner import InstitutionalTradePlanner
        pilot_telemetry_data = ActiveTradePilot.evaluate_open_position(trade, float(trade.entry_price or 100.0))
        target_ladder_data = InstitutionalTradePlanner.calculate_target_ladder(
            entry_price=float(trade.entry_price or 100.0),
            stop_loss=float(trade.stop_loss or (trade.entry_price * 0.97)),
            trade_type=trade.trade_type or "BUY"
        )

    api_key = current_app.config.get("TWELVE_DATA_API_KEY", "")

    return render_template(
        "trade/details.html",
        trade=trade,
        review=review,
        post_mortem=post_mortem,
        pilot_telemetry=pilot_telemetry_data,
        target_ladder=target_ladder_data,
        api_key=api_key
    )


@trade_bp.route("/<int:trade_id>/edit", methods=["GET", "POST"])
@login_required
def edit_trade(trade_id):

    trade = TradeService.get_trade(
        trade_id,
        current_user
    )

    if trade is None:

        flash(
            "Trade not found.",
            "danger"
        )

        return redirect(
            url_for("trade.trade_history")
        )

    form = TradeForm(obj=trade)

    if form.validate_on_submit():

        TradeService.update_trade(
            trade,
            form
        )

        flash(
            "Trade updated successfully!",
            "success"
        )

        return redirect(
            url_for(
                "trade.trade_details",
                trade_id=trade.id
            )
        )

    portfolio = PortfolioService.get_or_create_portfolio(current_user)
    account_balance = portfolio.current_balance or portfolio.starting_balance or 10000.0

    return render_template(
        "trade/edit_trade.html",
        form=form,
        trade=trade,
        account_balance=account_balance
    )


@trade_bp.route("/<int:trade_id>/delete", methods=["POST"])
@login_required
def delete_trade(trade_id):

    trade = TradeService.get_trade(
        trade_id,
        current_user
    )

    if trade is None:

        flash(
            "Trade not found.",
            "danger"
        )

        return redirect(
            url_for("trade.trade_history")
        )

    TradeService.delete_trade(
        trade
    )

    flash(
        "Trade deleted successfully!",
        "success"
    )

    return redirect(
        url_for("trade.trade_history")
    )


@trade_bp.route("/<int:trade_id>/close", methods=["GET", "POST"])
@login_required
def close_trade(trade_id):

    trade = TradeService.get_trade(
        trade_id,
        current_user
    )

    if trade is None:
        flash(
            "Trade not found.",
            "danger"
        )
        return redirect(
            url_for("trade.trade_history")
        )

    if trade.status == "CLOSED":
        flash(
            f"Trade #{trade.id} ({trade.symbol}) is already closed.",
            "info"
        )
        return redirect(
            url_for(
                "trade.trade_details",
                trade_id=trade.id
            )
        )

    form = CloseTradeForm()

    if form.validate_on_submit():
        TradeService.close_trade(
            trade=trade,
            exit_price=form.exit_price.data,
            emotion_after=form.emotion_after.data,
            notes=form.notes.data,
            exit_time=form.exit_time.data if hasattr(form, "exit_time") else None,
            exit_reason=form.exit_reason.data if hasattr(form, "exit_reason") else None,
            exit_thesis=form.exit_thesis.data if hasattr(form, "exit_thesis") else None,
        )

        pnl_str = f"+${trade.profit_loss:.2f}" if (trade.profit_loss or 0) >= 0 else f"-${abs(trade.profit_loss):.2f}"
        flash(
            f"Trade #{trade.id} ({trade.symbol}) closed successfully! Final P/L: {pnl_str}",
            "success"
        )

        return redirect(
            url_for(
                "trade.trade_details",
                trade_id=trade.id
            )
        )

    return render_template(
        "trade/close_trade.html",
        form=form,
        trade=trade
    )