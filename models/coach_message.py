from datetime import datetime, timezone
from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class CoachMessage(db.Model):
    """
    Persisted conversation turn between the trader and Aura AI Coach.
    """
    __tablename__ = "coach_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'aura'
    content = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), nullable=True)  # detected intent e.g. 'review_last_trade'
    meta_json = db.Column(db.Text, nullable=True)     # optional serialized payload (chips, stats)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    user = db.relationship("User", backref=db.backref("coach_messages", lazy=True, cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "time": self.created_at.strftime("%H:%M") if self.created_at else "",
            "date": self.created_at.strftime("%Y-%m-%d") if self.created_at else ""
        }
