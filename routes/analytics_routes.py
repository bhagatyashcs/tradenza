from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models.trade import Trade
from services.statistics_service import StatisticsService
from services.analytics import AnalyticsService

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def analytics_dashboard():
    trades = (
        Trade.query.filter_by(user_id=current_user.id, status="CLOSED")
        .order_by(Trade.created_at.asc())
        .all()
    )

    stats = StatisticsService.get_dashboard_stats(current_user)
    analytics_service = AnalyticsService()
    dash_data = analytics_service.get_dashboard_data(current_user)
    genome = dash_data.get("genome") or {}

    # 1. Strategy Performance Breakdown
    strategy_groups = defaultdict(list)
    for t in trades:
        strat = t.strategy or "Uncategorized"
        strategy_groups[strat].append(t)

    strategy_stats = []
    for strat, str_trades in strategy_groups.items():
        wins = [t for t in str_trades if (t.profit_loss or 0) > 0]
        losses = [t for t in str_trades if (t.profit_loss or 0) < 0]
        tot = len(str_trades)
        wr = round((len(wins) / tot) * 100, 1) if tot > 0 else 0.0
        net_pnl = sum((t.profit_loss or 0.0) for t in str_trades)
        gross_win = sum((t.profit_loss or 0.0) for t in wins)
        gross_loss = abs(sum((t.profit_loss or 0.0) for t in losses))
        pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (round(gross_win, 2) if gross_win > 0 else 0.0)

        strategy_stats.append({
            "strategy": strat,
            "count": tot,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": wr,
            "net_pnl": round(net_pnl, 2),
            "profit_factor": pf,
        })
    strategy_stats.sort(key=lambda x: x["net_pnl"], reverse=True)

    # 2. Market Breakdown
    market_groups = defaultdict(list)
    for t in trades:
        m = t.market or "Stocks"
        market_groups[m].append(t)

    market_stats = []
    for m, m_trades in market_groups.items():
        wins = [t for t in m_trades if (t.profit_loss or 0) > 0]
        tot = len(m_trades)
        wr = round((len(wins) / tot) * 100, 1) if tot > 0 else 0.0
        net = sum((t.profit_loss or 0.0) for t in m_trades)
        market_stats.append({
            "market": m,
            "count": tot,
            "win_rate": wr,
            "net_pnl": round(net, 2)
        })
    market_stats.sort(key=lambda x: x["count"], reverse=True)

    # 3. Day of Week Breakdown
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_groups = defaultdict(list)
    for t in trades:
        dt = t.entry_time or t.created_at
        if dt:
            day_groups[dt.weekday()].append(t)

    day_stats = []
    for d_idx in range(5):  # Mon - Fri primarily
        d_trades = day_groups.get(d_idx, [])
        tot = len(d_trades)
        wins = [t for t in d_trades if (t.profit_loss or 0) > 0]
        wr = round((len(wins) / tot) * 100, 1) if tot > 0 else 0.0
        net = sum((t.profit_loss or 0.0) for t in d_trades)
        day_stats.append({
            "day": day_names[d_idx],
            "count": tot,
            "win_rate": wr,
            "net_pnl": round(net, 2)
        })

    # 4. Expectancy calculation
    win_rate_dec = (stats.get("win_rate", 0) or 0) / 100.0
    loss_rate_dec = 1.0 - win_rate_dec
    avg_win = stats.get("average_win", 0) or 0
    avg_loss = abs(stats.get("average_loss", 0) or 0)
    expectancy = round((win_rate_dec * avg_win) - (loss_rate_dec * avg_loss), 2)

    return render_template(
        "analytics/analytics.html",
        user=current_user,
        stats=stats,
        genome=genome,
        strategy_stats=strategy_stats,
        market_stats=market_stats,
        day_stats=day_stats,
        expectancy=expectancy,
        total_closed=len(trades)
    )
