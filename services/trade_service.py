import os
import time
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy import or_

from services.analytics import AnalyticsService
from extensions import db
from models.trade import Trade
from services.portfolio_service import PortfolioService


class TradeService:

    @staticmethod
    def _parse_datetime(val):
        """Helper to parse varied date/time inputs safely into naive UTC datetime."""
        if not val:
            return None
        if isinstance(val, datetime):
            return val.replace(tzinfo=None) if val.tzinfo else val
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d",
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y"
            ):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
            try:
                dt = datetime.fromisoformat(val)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except Exception:
                pass
        return None

    @staticmethod
    def _save_uploaded_file(file_storage):
        if not file_storage or not getattr(file_storage, "filename", None):
            return None
        filename = secure_filename(file_storage.filename)
        if not filename:
            return None
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            return None
        unique_name = f"{int(time.time())}_{filename}"
        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "trades")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, unique_name)
        file_storage.save(filepath)
        return f"uploads/trades/{unique_name}"

    @staticmethod
    def _refresh_user_data(user):
        """
        Refresh derived portfolio and analytics data after
        a trade mutation.
        """
        PortfolioService.update_portfolio(user)

        analytics = AnalyticsService()
        analytics.refresh_user(user)

    @staticmethod
    def create_trade(user, form):
        raw_qty = form.quantity.data
        try:
            clean_qty = abs(float(raw_qty)) if raw_qty is not None else 1.0
        except (ValueError, TypeError):
            clean_qty = 1.0

        trade = Trade(
            user_id=user.id,
            market=form.market.data,
            symbol=form.symbol.data.upper(),
            trade_type=form.trade_type.data,
            entry_price=form.entry_price.data,
            exit_price=form.exit_price.data,
            quantity=clean_qty,
            strategy=form.strategy.data,
            timeframe=form.timeframe.data,
            stop_loss=form.stop_loss.data,
            target=form.target.data,
            emotion_before=form.emotion_before.data,
            confidence=form.confidence.data,
            notes=form.notes.data
        )

        # Parse & set entry timestamp
        if hasattr(form, "entry_time") and form.entry_time.data:
            trade.entry_time = TradeService._parse_datetime(form.entry_time.data) or datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            trade.entry_time = datetime.now(timezone.utc).replace(tzinfo=None)

        if hasattr(form, "emotion_after") and form.emotion_after.data:
            trade.emotion_after = form.emotion_after.data

        if hasattr(form, "entry_thesis") and form.entry_thesis.data:
            trade.entry_thesis = form.entry_thesis.data

        if hasattr(form, "exit_thesis") and form.exit_thesis.data:
            trade.exit_thesis = form.exit_thesis.data

        if hasattr(form, "exit_reason") and form.exit_reason.data:
            trade.exit_reason = form.exit_reason.data

        # Calculate planned risk amount
        if trade.stop_loss is not None and trade.entry_price is not None and clean_qty > 0:
            trade.risk_amount = round(abs(trade.entry_price - trade.stop_loss) * clean_qty, 2)
        elif hasattr(form, "risk_amount") and form.risk_amount.data:
            trade.risk_amount = round(float(form.risk_amount.data), 2)

        # Calculate planned risk:reward ratio
        if trade.target is not None and trade.stop_loss is not None and trade.entry_price is not None:
            risk_ps = abs(trade.entry_price - trade.stop_loss)
            reward_ps = abs(trade.target - trade.entry_price)
            if risk_ps > 0:
                trade.planned_rr = round(reward_ps / risk_ps, 2)
        elif hasattr(form, "planned_rr") and form.planned_rr.data:
            trade.planned_rr = round(float(form.planned_rr.data), 2)

        # Calculate planned risk % of user portfolio balance
        portfolio = PortfolioService.get_or_create_portfolio(user)
        current_bal = portfolio.current_balance or portfolio.starting_balance or 0.0
        if trade.risk_amount and current_bal > 0:
            trade.risk_percent = round((trade.risk_amount / current_bal) * 100, 2)
        elif hasattr(form, "risk_percent") and form.risk_percent.data:
            trade.risk_percent = round(float(form.risk_percent.data), 2)

        # Handle Chart Image Uploads
        if hasattr(form, "setup_image") and form.setup_image.data:
            saved = TradeService._save_uploaded_file(form.setup_image.data)
            if saved:
                trade.setup_image = saved
        if hasattr(form, "chart_before") and form.chart_before.data:
            saved = TradeService._save_uploaded_file(form.chart_before.data)
            if saved:
                trade.chart_before = saved

        if trade.exit_price:
            trade.profit_loss = TradeService.calculate_profit(trade)
            trade.status = "CLOSED"
            if hasattr(form, "exit_time") and form.exit_time.data:
                trade.exit_time = TradeService._parse_datetime(form.exit_time.data) or datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                trade.exit_time = datetime.now(timezone.utc).replace(tzinfo=None)

            if trade.risk_amount and trade.risk_amount > 0:
                trade.realized_r = round(trade.profit_loss / trade.risk_amount, 2)
        else:
            trade.profit_loss = None
            trade.status = "OPEN"
            trade.exit_time = None

        db.session.add(trade)
        db.session.commit()

        # New unified refresh flow
        TradeService._refresh_user_data(user)

        return trade

    @staticmethod
    def get_user_trades(user, page=1, per_page=10):
        return (
            Trade.query
            .filter_by(user_id=user.id)
            .order_by(Trade.created_at.desc())
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

    @staticmethod
    def get_recent_trades(user, limit=5):
        return (
            Trade.query
            .filter_by(user_id=user.id)
            .order_by(Trade.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def search_trades(user, query, page=1, per_page=10):
        return (
            Trade.query
            .filter(
                Trade.user_id == user.id,
                or_(
                    Trade.symbol.ilike(f"%{query}%"),
                    Trade.market.ilike(f"%{query}%"),
                    Trade.strategy.ilike(f"%{query}%")
                )
            )
            .order_by(Trade.created_at.desc())
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

    @staticmethod
    def filter_trades(user, filters, page=1, per_page=10):
        query = Trade.query.filter_by(user_id=user.id)

        if filters.get("market"):
            query = query.filter(Trade.market == filters["market"])

        if filters.get("trade_type"):
            query = query.filter(Trade.trade_type == filters["trade_type"])

        if filters.get("status"):
            query = query.filter(Trade.status == filters["status"])

        return (
            query
            .order_by(Trade.created_at.desc())
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

    @staticmethod
    def get_trade(trade_id, user):
        return (
            Trade.query
            .filter_by(
                id=trade_id,
                user_id=user.id
            )
            .first()
        )

    @staticmethod
    def update_trade(trade, form):
        user = trade.user

        trade.market = form.market.data
        trade.symbol = form.symbol.data.upper()
        trade.trade_type = form.trade_type.data
        trade.entry_price = form.entry_price.data
        trade.exit_price = form.exit_price.data
        raw_qty = form.quantity.data
        try:
            trade.quantity = abs(float(raw_qty)) if raw_qty is not None else 1.0
        except (ValueError, TypeError):
            trade.quantity = 1.0
        trade.strategy = form.strategy.data
        trade.timeframe = form.timeframe.data
        trade.stop_loss = form.stop_loss.data
        trade.target = form.target.data
        trade.emotion_before = form.emotion_before.data
        if hasattr(form, "emotion_after") and form.emotion_after.data:
            trade.emotion_after = form.emotion_after.data
        trade.confidence = form.confidence.data
        trade.notes = form.notes.data

        if hasattr(form, "entry_time") and form.entry_time.data:
            parsed_entry = TradeService._parse_datetime(form.entry_time.data)
            if parsed_entry:
                trade.entry_time = parsed_entry

        if hasattr(form, "entry_thesis") and form.entry_thesis.data:
            trade.entry_thesis = form.entry_thesis.data

        if hasattr(form, "exit_thesis") and form.exit_thesis.data:
            trade.exit_thesis = form.exit_thesis.data

        if hasattr(form, "exit_reason") and form.exit_reason.data:
            trade.exit_reason = form.exit_reason.data

        # Recalculate planned risk metrics
        if trade.stop_loss is not None and trade.entry_price is not None and trade.quantity > 0:
            trade.risk_amount = round(abs(trade.entry_price - trade.stop_loss) * trade.quantity, 2)
        elif hasattr(form, "risk_amount") and form.risk_amount.data:
            trade.risk_amount = round(float(form.risk_amount.data), 2)

        if trade.target is not None and trade.stop_loss is not None and trade.entry_price is not None:
            risk_ps = abs(trade.entry_price - trade.stop_loss)
            reward_ps = abs(trade.target - trade.entry_price)
            if risk_ps > 0:
                trade.planned_rr = round(reward_ps / risk_ps, 2)
        elif hasattr(form, "planned_rr") and form.planned_rr.data:
            trade.planned_rr = round(float(form.planned_rr.data), 2)

        portfolio = PortfolioService.get_or_create_portfolio(user)
        current_bal = portfolio.current_balance or portfolio.starting_balance or 0.0
        if trade.risk_amount and current_bal > 0:
            trade.risk_percent = round((trade.risk_amount / current_bal) * 100, 2)

        # Handle Chart Image Uploads in Edit
        if hasattr(form, "setup_image") and form.setup_image.data:
            saved = TradeService._save_uploaded_file(form.setup_image.data)
            if saved:
                trade.setup_image = saved
        if hasattr(form, "chart_before") and form.chart_before.data:
            saved = TradeService._save_uploaded_file(form.chart_before.data)
            if saved:
                trade.chart_before = saved

        if trade.exit_price:
            trade.profit_loss = TradeService.calculate_profit(trade)
            trade.status = "CLOSED"
            if hasattr(form, "exit_time") and form.exit_time.data:
                parsed_exit = TradeService._parse_datetime(form.exit_time.data)
                if parsed_exit:
                    trade.exit_time = parsed_exit
            if not trade.exit_time:
                trade.exit_time = datetime.now(timezone.utc).replace(tzinfo=None)

            if trade.risk_amount and trade.risk_amount > 0:
                trade.realized_r = round(trade.profit_loss / trade.risk_amount, 2)
        else:
            trade.profit_loss = None
            trade.status = "OPEN"
            trade.exit_time = None

        db.session.commit()

        # New unified refresh flow
        TradeService._refresh_user_data(user)

        return trade

    @staticmethod
    def close_trade(trade, exit_price, emotion_after=None, notes=None, exit_time=None, exit_reason=None, exit_thesis=None):
        """
        Fast dedicated method to close an open trade.
        """
        user = trade.user
        trade.exit_price = float(exit_price)
        trade.quantity = abs(float(trade.quantity or 1.0))
        trade.profit_loss = TradeService.calculate_profit(trade)
        trade.status = "CLOSED"

        parsed_exit = TradeService._parse_datetime(exit_time) if isinstance(exit_time, str) else exit_time
        trade.exit_time = parsed_exit or datetime.now(timezone.utc).replace(tzinfo=None)

        # Calculate realized R-multiple
        if trade.risk_amount and trade.risk_amount > 0:
            trade.realized_r = round(trade.profit_loss / trade.risk_amount, 2)
        elif trade.stop_loss and trade.entry_price:
            calc_risk = abs(trade.entry_price - trade.stop_loss) * trade.quantity
            if calc_risk > 0:
                trade.risk_amount = round(calc_risk, 2)
                trade.realized_r = round(trade.profit_loss / trade.risk_amount, 2)

        if emotion_after:
            trade.emotion_after = emotion_after

        if exit_reason:
            trade.exit_reason = exit_reason

        if exit_thesis:
            trade.exit_thesis = exit_thesis

        if notes:
            if trade.notes:
                trade.notes += f"\n\n[Closing Notes]: {notes}"
            else:
                trade.notes = f"[Closing Notes]: {notes}"

        db.session.commit()
        TradeService._refresh_user_data(user)
        return trade

    @staticmethod
    def delete_trade(trade):
        user = trade.user

        db.session.delete(trade)
        db.session.commit()

        # New unified refresh flow
        TradeService._refresh_user_data(user)

    @staticmethod
    def calculate_profit(trade):
        if trade.exit_price is None:
            return None

        qty = abs(float(trade.quantity or 1.0))
        if trade.trade_type == "BUY":
            return round((trade.exit_price - trade.entry_price) * qty, 2)

        return round((trade.entry_price - trade.exit_price) * qty, 2)