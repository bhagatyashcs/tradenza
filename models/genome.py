from datetime import datetime, timezone

from extensions import db

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class TraderGenome(db.Model):
    __tablename__ = "trader_genomes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    # Core Genome Scores (0 - 100)
    discipline = db.Column(db.Float, default=50.0)
    patience = db.Column(db.Float, default=50.0)
    consistency = db.Column(db.Float, default=50.0)
    aggression = db.Column(db.Float, default=50.0)
    risk_control = db.Column(db.Float, default=50.0)
    decision_speed = db.Column(db.Float, default=50.0)
    adaptability = db.Column(db.Float, default=50.0)
    confidence = db.Column(db.Float, default=50.0)
    learning_rate = db.Column(db.Float, default=50.0)

    # Overall & Archetype
    overall_score = db.Column(db.Float, default=50.0)
    archetype = db.Column(db.String(100), default="Developing Systematic Trader")

    # Sample Size & Explainability Audit
    trade_count = db.Column(db.Integer, default=0)
    confidence_tier = db.Column(db.String(50), default="INSUFFICIENT_SAMPLE")
    factor_breakdowns = db.Column(db.JSON, default=dict)

    created_at = db.Column(
        db.DateTime,
        default=_utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow
    )

    def update_from_genome(self, genome):
        """
        Update database values from GenomeEngine result.
        """
        self.discipline = genome.discipline
        self.patience = genome.patience
        self.consistency = genome.consistency
        self.aggression = genome.aggression
        self.risk_control = genome.risk_control
        self.decision_speed = genome.decision_speed
        self.adaptability = genome.adaptability
        self.confidence = genome.confidence
        self.learning_rate = genome.learning_rate
        self.overall_score = genome.overall_score
        self.archetype = genome.archetype
        self.trade_count = getattr(genome, "trade_count", 0)
        self.confidence_tier = getattr(genome, "confidence_tier", "INSUFFICIENT_SAMPLE")
        self.factor_breakdowns = getattr(genome, "factor_breakdowns", {})

    def to_dict(self):
        return {
            "discipline": round(self.discipline or 0.0, 1),
            "patience": round(self.patience or 0.0, 1),
            "consistency": round(self.consistency or 0.0, 1),
            "aggression": round(self.aggression or 0.0, 1),
            "risk_control": round(self.risk_control or 0.0, 1),
            "decision_speed": round(self.decision_speed or 0.0, 1),
            "adaptability": round(self.adaptability or 0.0, 1),
            "confidence": round(self.confidence or 0.0, 1),
            "learning_rate": round(self.learning_rate or 0.0, 1),
            "overall_score": round(self.overall_score or 0.0, 1),
            "archetype": self.archetype,
            "trade_count": self.trade_count,
            "confidence_tier": self.confidence_tier,
            "factor_breakdowns": self.factor_breakdowns or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return (
            f"<TraderGenome "
            f"user={self.user_id} "
            f"score={self.overall_score:.1f}>"
        )


class TraderGenomeHistory(db.Model):
    """
    Historical snapshot of a trader's genome for progress visualization
    and temporal behavioral trend analysis.
    """
    __tablename__ = "trader_genome_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    discipline = db.Column(db.Float, default=50.0)
    patience = db.Column(db.Float, default=50.0)
    consistency = db.Column(db.Float, default=50.0)
    aggression = db.Column(db.Float, default=50.0)
    risk_control = db.Column(db.Float, default=50.0)
    decision_speed = db.Column(db.Float, default=50.0)
    adaptability = db.Column(db.Float, default=50.0)
    confidence = db.Column(db.Float, default=50.0)
    learning_rate = db.Column(db.Float, default=50.0)

    overall_score = db.Column(db.Float, default=50.0)
    archetype = db.Column(db.String(100), default="Developing Systematic Trader")

    trade_count = db.Column(db.Integer, default=0)
    confidence_tier = db.Column(db.String(50), default="INSUFFICIENT_SAMPLE")
    factor_breakdowns = db.Column(db.JSON, default=dict)

    created_at = db.Column(
        db.DateTime,
        default=_utcnow,
        index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "discipline": round(self.discipline or 0.0, 1),
            "patience": round(self.patience or 0.0, 1),
            "consistency": round(self.consistency or 0.0, 1),
            "aggression": round(self.aggression or 0.0, 1),
            "risk_control": round(self.risk_control or 0.0, 1),
            "decision_speed": round(self.decision_speed or 0.0, 1),
            "adaptability": round(self.adaptability or 0.0, 1),
            "confidence": round(self.confidence or 0.0, 1),
            "learning_rate": round(self.learning_rate or 0.0, 1),
            "overall_score": round(self.overall_score or 0.0, 1),
            "archetype": self.archetype,
            "trade_count": self.trade_count,
            "confidence_tier": self.confidence_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return (
            f"<TraderGenomeHistory "
            f"user={self.user_id} "
            f"score={self.overall_score:.1f} "
            f"date={self.created_at}>"
        )