from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField


class SearchTradeForm(FlaskForm):

    query = StringField("Search")

    submit = SubmitField("Search")