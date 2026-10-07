from datetime import datetime, timezone

from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class LedgerTransaction(db.Model):
    """
    Immutable ledger entry recording external cash movements (deposits,
    withdrawals, adjustments) strictly separated from trading P/L.
    """
    __tablename__ = "ledger_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False, index=True)

    tx_type = db.Column(db.String(32), nullable=False)  # DEPOSIT, WITHDRAWAL, RESET_BALANCE, ADJUSTMENT
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "portfolio_id": self.portfolio_id,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<LedgerTransaction #{self.id} {self.tx_type} {self.amount}>"
