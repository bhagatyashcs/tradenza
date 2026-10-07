from datetime import datetime, timezone

from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class Portfolio(db.Model):

    __tablename__ = "portfolios"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    transactions = db.relationship(
        "LedgerTransaction",
        backref="portfolio",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="desc(LedgerTransaction.created_at)"
    )

    starting_balance = db.Column(
        db.Float,
        default=0.0
    )

    current_balance = db.Column(
        db.Float,
        default=0.0
    )

    total_deposit = db.Column(
        db.Float,
        default=0.0
    )

    total_withdrawal = db.Column(
        db.Float,
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

    highest_balance = db.Column(
        db.Float,
        default=0.0
    )

    lowest_balance = db.Column(
        db.Float,
        default=0.0
    )

    created_at = db.Column(
        db.DateTime,
        default=_utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow
    )

    @property
    def net_profit(self):
        """Net trading performance decoupled from deposits/withdrawals."""
        return round((self.realized_profit or 0.0) + (self.unrealized_profit or 0.0), 2)

    @property
    def growth_percentage(self):
        """Pure trading ROI percentage calculated from starting capital."""
        if not self.starting_balance or self.starting_balance <= 0:
            return 0.0
        return round(((self.realized_profit or 0.0) / self.starting_balance) * 100, 2)

    @property
    def win_rate(self):

        if self.total_trades == 0:

            return 0

        return round(

            (
                self.winning_trades /
                self.total_trades
            ) * 100,

            2

        )

    def __repr__(self):

        return f"<Portfolio User {self.user_id}>"