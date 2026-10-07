from flask_wtf import FlaskForm
from wtforms import SelectField


class FilterTradeForm(FlaskForm):

    market = SelectField(
        "Market",
        choices=[
            ("", "All Markets"),
            ("Stocks", "Stocks"),
            ("Crypto", "Crypto"),
            ("Forex", "Forex"),
            ("Options", "Options"),
        ],
    )

    trade_type = SelectField(
        "Trade Type",
        choices=[
            ("", "All Types"),
            ("BUY", "BUY"),
            ("SELL", "SELL"),
        ],
    )

    status = SelectField(
        "Status",
        choices=[
            ("", "All Status"),
            ("OPEN", "OPEN"),
            ("CLOSED", "CLOSED"),
        ],
    )