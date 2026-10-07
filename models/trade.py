from datetime import datetime, timezone

from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class Trade(db.Model):

    __tablename__ = "trades"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    market = db.Column(
        db.String(30),
        nullable=False
    )

    symbol = db.Column(
        db.String(30),
        nullable=False
    )

    trade_type = db.Column(
        db.String(10),
        nullable=False
    )

    entry_price = db.Column(
        db.Float,
        nullable=False
    )

    exit_price = db.Column(
        db.Float
    )

    quantity = db.Column(
        db.Float,
        nullable=False
    )

    strategy = db.Column(
        db.String(100)
    )

    timeframe = db.Column(
        db.String(30)
    )

    stop_loss = db.Column(
        db.Float
    )

    target = db.Column(
        db.Float
    )

    emotion_before = db.Column(
        db.String(50)
    )

    emotion_after = db.Column(
        db.String(50)
    )

    confidence = db.Column(
        db.Integer
    )

    notes = db.Column(
        db.Text
    )

    # Performance
    profit_loss = db.Column(
        db.Float
    )

    status = db.Column(
        db.String(20),
        default="OPEN"
    )

    # ---------- Images ----------

    chart_before = db.Column(
        db.String(255)
    )

    chart_after = db.Column(
        db.String(255)
    )

    setup_image = db.Column(
        db.String(255)
    )

    # ---------- Future ----------

    tags = db.Column(
        db.String(255)
    )

    review_score = db.Column(
        db.Integer
    )

    ai_reviewed = db.Column(
        db.Boolean,
        default=False
    )

    # Quantitative Risk & Execution Architecture
    risk_amount = db.Column(
        db.Float,
        nullable=True
    )

    risk_percent = db.Column(
        db.Float,
        nullable=True
    )

    planned_rr = db.Column(
        db.Float,
        nullable=True
    )

    realized_r = db.Column(
        db.Float,
        nullable=True
    )

    exit_reason = db.Column(
        db.String(50),
        nullable=True
    )

    entry_thesis = db.Column(
        db.Text,
        nullable=True
    )

    exit_thesis = db.Column(
        db.Text,
        nullable=True
    )

    entry_time = db.Column(
        db.DateTime,
        default=_utcnow
    )

    exit_time = db.Column(
        db.DateTime,
        nullable=True
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

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "market": self.market,
            "symbol": self.symbol,
            "trade_type": self.trade_type,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "strategy": self.strategy,
            "timeframe": self.timeframe,
            "profit_loss": self.profit_loss,
            "status": self.status,
            "risk_amount": self.risk_amount,
            "risk_percent": self.risk_percent,
            "planned_rr": self.planned_rr,
            "realized_r": self.realized_r,
            "exit_reason": self.exit_reason,
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after,
            "confidence": self.confidence,
            "notes": self.notes,
            "entry_thesis": self.entry_thesis,
            "exit_thesis": self.exit_thesis,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):

        return (
            f"<Trade {self.symbol} | "
            f"{self.trade_type}>"
        )