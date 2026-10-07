from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import (
    StringField,
    FloatField,
    IntegerField,
    SelectField,
    TextAreaField,
    SubmitField
)

from wtforms.validators import DataRequired, Optional, NumberRange


class TradeForm(FlaskForm):

    market = SelectField(
        "Market",
        choices=[
            ("Stocks", "Stocks"),
            ("Options", "Options"),
            ("Futures", "Futures"),
            ("Crypto", "Crypto"),
            ("Forex", "Forex")
        ],
        validators=[DataRequired()]
    )

    symbol = StringField(
        "Symbol",
        validators=[DataRequired()]
    )

    trade_type = SelectField(
        "Trade Type",
        choices=[
            ("BUY", "BUY"),
            ("SELL", "SELL")
        ],
        validators=[DataRequired()]
    )

    entry_price = FloatField(
        "Entry Price",
        validators=[DataRequired()]
    )

    exit_price = FloatField(
        "Exit Price",
        validators=[Optional()]
    )

    quantity = FloatField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=0.000001, message="Quantity must be greater than 0.")]
    )

    strategy = StringField(
        "Strategy",
        validators=[Optional()]
    )

    timeframe = StringField(
        "Timeframe",
        validators=[Optional()]
    )

    stop_loss = FloatField(
        "Stop Loss",
        validators=[Optional()]
    )

    target = FloatField(
        "Target",
        validators=[Optional()]
    )

    emotion_before = SelectField(
        "Emotion Before",
        choices=[
            ("", "Select"),
            ("Calm", "Calm"),
            ("Confident", "Confident"),
            ("Fear", "Fear"),
            ("Greed", "Greed"),
            ("FOMO", "FOMO")
        ],
        validators=[Optional()]
    )

    emotion_after = SelectField(
        "Emotion After Exit",
        choices=[
            ("", "Select"),
            ("Satisfied", "Satisfied"),
            ("Relieved", "Relieved"),
            ("Neutral", "Neutral"),
            ("Frustrated", "Frustrated"),
            ("Regretful", "Regretful"),
            ("Anxious", "Anxious")
        ],
        validators=[Optional()]
    )

    confidence = IntegerField(
        "Confidence (1-10)",
        validators=[Optional()]
    )

    notes = TextAreaField(
        "Notes",
        validators=[Optional()]
    )

    # -------------------------
    # Quantitative Risk & Journal Architecture
    # -------------------------

    entry_time = StringField(
        "Entry Date & Time",
        validators=[Optional()]
    )

    exit_time = StringField(
        "Exit Date & Time",
        validators=[Optional()]
    )

    planned_rr = FloatField(
        "Planned Risk:Reward (R:R)",
        validators=[Optional()]
    )

    risk_amount = FloatField(
        "Planned Risk Amount",
        validators=[Optional()]
    )

    risk_percent = FloatField(
        "Risk % of Capital",
        validators=[Optional()]
    )

    entry_thesis = TextAreaField(
        "Entry Hypothesis & Setup Invalidation Criteria",
        validators=[Optional()]
    )

    exit_thesis = TextAreaField(
        "Exit Post-Mortem & Execution Lessons",
        validators=[Optional()]
    )

    exit_reason = SelectField(
        "Exit Reason",
        choices=[
            ("", "Select Exit Reason"),
            ("TARGET_HIT", "Target Hit (Take Profit)"),
            ("STOPPED_OUT", "Stopped Out (Stop Loss)"),
            ("MANUAL_EARLY", "Manual Early Exit"),
            ("TRAILING_STOP", "Trailing Stop Hit"),
            ("INVALIDATION", "Technical Invalidation"),
            ("PANIC_EXIT", "Emotional / Panic Exit"),
            ("TIME_STOP", "Session / Time Expiry")
        ],
        validators=[Optional()]
    )

    # -------------------------
    # Images
    # -------------------------

    chart_before = FileField(
        "Chart Before Entry",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Images only!"
            )
        ]
    )

    chart_after = FileField(
        "Chart After Exit",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Images only!"
            )
        ]
    )

    setup_image = FileField(
        "Setup Screenshot",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Images only!"
            )
        ]
    )

    submit = SubmitField(
        "Save Trade"
    )


class CloseTradeForm(FlaskForm):
    """Quick form to close an open trade."""

    exit_price = FloatField(
        "Exit Price",
        validators=[DataRequired()]
    )

    exit_time = StringField(
        "Exit Date & Time",
        validators=[Optional()]
    )

    exit_reason = SelectField(
        "Exit Reason",
        choices=[
            ("", "Select Exit Reason"),
            ("TARGET_HIT", "Target Hit (Take Profit)"),
            ("STOPPED_OUT", "Stopped Out (Stop Loss)"),
            ("MANUAL_EARLY", "Manual Early Exit"),
            ("TRAILING_STOP", "Trailing Stop Hit"),
            ("INVALIDATION", "Technical Invalidation"),
            ("PANIC_EXIT", "Emotional / Panic Exit"),
            ("TIME_STOP", "Session / Time Expiry")
        ],
        validators=[Optional()]
    )

    emotion_after = SelectField(
        "Emotion After Exit",
        choices=[
            ("", "Select Emotion"),
            ("Satisfied", "Satisfied"),
            ("Relieved", "Relieved"),
            ("Neutral", "Neutral"),
            ("Frustrated", "Frustrated"),
            ("Regretful", "Regretful"),
            ("Anxious", "Anxious")
        ],
        validators=[Optional()]
    )

    exit_thesis = TextAreaField(
        "Exit Analysis & Reflection",
        validators=[Optional()]
    )

    notes = TextAreaField(
        "Closing Notes & Takeaways",
        validators=[Optional()]
    )

    submit = SubmitField(
        "Confirm Close Trade"
    )