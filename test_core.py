import sys
import os
import traceback

# Add current directory to path so we can import app modules
sys.path.insert(0, os.path.abspath('.'))

try:
    from app import app
    from extensions import db
    from models.user import User
    from models.trade import Trade
    from models.portfolio import Portfolio
    from services.analytics import AnalyticsService
    from services.trade_service import TradeService
    from services.digital_twin_service import DigitalTwinService
    from services.portfolio_service import PortfolioService
    
    with app.app_context():
        # Get a user
        user = User.query.first()
        if not user:
            print("No users found.")
            sys.exit(0)
            
        print(f"Testing for user: {user.name} ({user.id})")
        
        try:
            print("Testing Analytics...")
            AnalyticsService().get_dashboard_data(user)
            print("Analytics OK.")
        except Exception as e:
            print(f"Analytics FAILED: {e}")
            traceback.print_exc()

        try:
            print("Testing Trade Service...")
            TradeService.get_user_trades(user)
            print("Trade Service OK.")
        except Exception as e:
            print(f"Trade Service FAILED: {e}")
            traceback.print_exc()
            
        try:
            print("Testing Digital Twin Service...")
            DigitalTwinService().get_twin(user)
            print("Digital Twin Service OK.")
        except Exception as e:
            print(f"Digital Twin Service FAILED: {e}")
            traceback.print_exc()
            
        try:
            print("Testing Portfolio Service...")
            PortfolioService.get_or_create_portfolio(user)
            print("Portfolio Service OK.")
        except Exception as e:
            print(f"Portfolio Service FAILED: {e}")
            traceback.print_exc()

except Exception as e:
    print(f"Initialization FAILED: {e}")
    traceback.print_exc()
