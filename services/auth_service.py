from werkzeug.security import generate_password_hash, check_password_hash

from models import User
from models.portfolio import Portfolio
from models.genome import TraderGenome
from extensions import db


class AuthService:

    @staticmethod
    def register_user(name, email, password):

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return False, "Email already exists."

        hashed_password = generate_password_hash(password)

        user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(user)
        db.session.flush()

        # Initialize portfolio ledger baseline
        portfolio = Portfolio(
            user_id=user.id,
            starting_balance=0.0,
            current_balance=0.0,
            highest_balance=0.0,
            lowest_balance=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            realized_profit=0.0,
            total_deposit=0.0,
            total_withdrawal=0.0
        )
        db.session.add(portfolio)

        # Initialize baseline TraderGenome record
        genome = TraderGenome(
            user_id=user.id,
            discipline=50.0,
            patience=50.0,
            consistency=50.0,
            aggression=50.0,
            risk_control=50.0,
            decision_speed=50.0,
            adaptability=50.0,
            confidence=50.0,
            learning_rate=50.0,
            overall_score=50.0,
            archetype="Developing Trader"
        )
        db.session.add(genome)

        db.session.commit()

        return True, "Registration successful."

    @staticmethod
    def authenticate(email, password):

        user = User.query.filter_by(email=email).first()

        if not user:
            return None

        if check_password_hash(user.password, password):
            return user

        return None