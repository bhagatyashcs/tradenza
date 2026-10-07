from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import User
from models.portfolio import Portfolio
from services.portfolio_service import PortfolioService

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def settings():
    portfolio = PortfolioService.get_or_create_portfolio(current_user)

    if request.method == "POST":
        action = request.form.get("action", "preferences")

        if action == "preferences":
            # Profile & Risk Parameters
            name = request.form.get("name", "").strip()
            currency = request.form.get("currency", "$").strip()
            try:
                max_risk = float(request.form.get("max_risk_percent", 2.0))
            except ValueError:
                max_risk = 2.0

            try:
                daily_loss = float(request.form.get("daily_max_loss", 500.0))
            except ValueError:
                daily_loss = 500.0

            try:
                starting_balance = float(request.form.get("starting_balance", portfolio.starting_balance or 10000.0))
                if starting_balance > 0 and starting_balance != portfolio.starting_balance:
                    portfolio.starting_balance = starting_balance
                    # Also update current balance if never traded
                    if portfolio.total_trades == 0:
                        portfolio.current_balance = starting_balance
            except ValueError:
                pass

            if name:
                current_user.name = name
            current_user.currency = currency
            current_user.max_risk_percent = max(0.25, min(10.0, max_risk))
            current_user.daily_max_loss = max(10.0, daily_loss)

            db.session.commit()
            flash("Trading preferences & risk guardrails saved successfully!", "success")
            return redirect(url_for("settings.settings"))

        elif action == "password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not check_password_hash(current_user.password, current_pw):
                flash("Incorrect current password.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters long.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            else:
                current_user.password = generate_password_hash(new_pw)
                db.session.commit()
                flash("Password updated successfully!", "success")
        elif action == "ai":
            ai_provider = request.form.get("ai_provider", "nvidia").strip().lower()
            nvidia_key = request.form.get("nvidia_api_key", "").strip()
            gemini_key = request.form.get("gemini_api_key", "").strip()
            openai_key = request.form.get("openai_api_key", "").strip()
            ai_model = request.form.get("ai_model", "").strip()
            coaching_style = request.form.get("ai_coaching_style", "socratic").strip()

            current_user.ai_provider = ai_provider
            if ai_model:
                current_user.ai_model = ai_model
            current_user.ai_coaching_style = coaching_style
            if nvidia_key:
                current_user.nvidia_api_key = nvidia_key
            if gemini_key:
                current_user.gemini_api_key = gemini_key
            if openai_key:
                current_user.openai_api_key = openai_key

            db.session.commit()
            flash("Aura AI Coach intelligence settings saved successfully!", "success")
            return redirect(url_for("settings.settings"))

    return render_template(
        "settings/settings.html",
        user=current_user,
        portfolio=portfolio
    )
