from flask import Blueprint, render_template
from flask_login import login_required, current_user

from services.analytics import AnalyticsService
from services.digital_twin_service import DigitalTwinService
from services.statistics_service import StatisticsService
from services.trade_service import TradeService
from services.portfolio_service import PortfolioService
from services.chart_service import ChartService
from services.aura_tools import AuraTools
from services.tradebuddy import TradeBuddyService


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():

    stats = StatisticsService.get_dashboard_stats(
        current_user
    )

    portfolio = PortfolioService.get_summary(
        current_user
    )

    recent_trades = TradeService.get_recent_trades(
        current_user,
        limit=5
    )

    charts = ChartService.get_dashboard_charts(
        current_user
    )

    # Tradenza Intelligence Pipeline
    analytics_service = AnalyticsService()

    analytics = analytics_service.get_dashboard_data(
        current_user
    )

    digital_twin = DigitalTwinService().get_twin(
        current_user,
        analytics=analytics
    )

    aura = analytics.get("aura") or {}

    aura_reflection = aura.get(
        "coaching_message"
    )

    drawdown = AuraTools.get_drawdown(current_user.id)
    cooldown_info = TradeBuddyService.check_cooldown_status(current_user)

    return render_template(
        "dashboard/dashboard.html",
        user=current_user,

        # Existing dashboard data
        stats=stats,
        portfolio=portfolio,
        recent_trades=recent_trades,
        charts=charts,

        # Intelligence data
        analytics=analytics,
        digital_twin=digital_twin,
        behavior=analytics.get("behavior"),
        genome=analytics.get("genome"),
        insights=analytics.get("insights"),
        aura=aura,
        aura_reflection=aura_reflection,
        drawdown=drawdown,
        cooldown_info=cooldown_info
    )