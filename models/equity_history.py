from datetime import datetime, timezone

from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class EquityHistory(db.Model):

    __tablename__ = "equity_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id"),
        nullable=False
    )

    balance = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    realized_profit = db.Column(
        db.Float,
        default=0.0
    )

    unrealized_profit = db.Column(
        db.Float,
        default=0.0
    )

    daily_profit = db.Column(
        db.Float,
        default=0.0
    )

    total_trades = db.Column(
        db.Integer,
        default=0
    )

    winning_trades = db.Column(
        db.Integer,
        default=0
    )

    losing_trades = db.Column(
        db.Integer,
        default=0
    )

    win_rate = db.Column(
        db.Float,
        default=0.0
    )

    created_at = db.Column(
        db.DateTime,
        default=_utcnow
    )

    portfolio = db.relationship(
        "Portfolio",
        backref=db.backref(
            "equity_history",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):

        return (
            f"<EquityHistory "
            f"{self.user_id} "
            f"{self.balance}>"
        )