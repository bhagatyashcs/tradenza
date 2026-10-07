from extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    currency = db.Column(
        db.String(10),
        default="$"
    )

    max_risk_percent = db.Column(
        db.Float,
        default=2.0
    )

    daily_max_loss = db.Column(
        db.Float,
        default=500.0
    )

    ai_provider = db.Column(
        db.String(30),
        default="nvidia"
    )

    ai_model = db.Column(
        db.String(50),
        default="deepseek-ai/deepseek-v4.1-flash"
    )

    nvidia_api_key = db.Column(
        db.String(150),
        default=""
    )

    gemini_api_key = db.Column(
        db.String(150),
        default=""
    )

    openai_api_key = db.Column(
        db.String(150),
        default=""
    )

    ai_coaching_style = db.Column(
        db.String(50),
        default="socratic"
    )

    # -----------------------------
    # Relationships
    # -----------------------------

    trades = db.relationship(
        "Trade",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    portfolio = db.relationship(
        "Portfolio",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    genome = db.relationship(
        "TraderGenome",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):

        return f"<User {self.email}>"