from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from services.portfolio_service import PortfolioService
from services.equity_service import EquityService
from models.equity_history import EquityHistory

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")


@portfolio_bp.route("/")
@login_required
def portfolio():
    summary = PortfolioService.get_summary(current_user)
    portfolio_record = PortfolioService.get_or_create_portfolio(current_user)

    snapshots = (
        EquityHistory.query.filter_by(user_id=current_user.id)
        .order_by(EquityHistory.created_at.desc())
        .limit(15)
        .all()
    )

    transactions = PortfolioService.get_ledger_transactions(current_user, limit=50)

    return render_template(
        "portfolio/portfolio.html",
        user=current_user,
        portfolio=summary,
        portfolio_record=portfolio_record,
        snapshots=snapshots,
        transactions=transactions
    )


@portfolio_bp.route("/transaction", methods=["POST"])
@login_required
def transaction():
    tx_type = request.form.get("tx_type", "").strip().lower()
    notes = request.form.get("notes", "").strip() or None
    try:
        amount = abs(float(request.form.get("amount", 0.0)))
    except (ValueError, TypeError):
        amount = 0.0

    if amount <= 0:
        flash("Please enter a valid amount greater than 0.", "danger")
        return redirect(url_for("portfolio.portfolio"))

    port = PortfolioService.get_or_create_portfolio(current_user)

    if tx_type == "deposit":
        PortfolioService.deposit(current_user, amount, notes=notes)
        flash(f"Successfully deposited {current_user.currency or '$'}{amount:.2f} into trading account.", "success")

    elif tx_type == "withdrawal":
        current_bal = port.current_balance or 0.0
        if amount > current_bal:
            flash(f"Withdrawal amount exceeds available balance ({current_user.currency or '$'}{current_bal:.2f}).", "danger")
            return redirect(url_for("portfolio.portfolio"))

        PortfolioService.withdraw(current_user, amount, notes=notes)
        flash(f"Successfully recorded withdrawal of {current_user.currency or '$'}{amount:.2f}.", "success")

    elif tx_type == "reset_balance":
        port.total_deposit = 0.0
        port.total_withdrawal = 0.0
        db.session.commit()
        PortfolioService.set_starting_balance(current_user, amount, notes=notes or "Re-anchored starting balance")
        flash(f"Starting equity re-anchored to {current_user.currency or '$'}{amount:.2f}.", "success")

    return redirect(url_for("portfolio.portfolio"))
