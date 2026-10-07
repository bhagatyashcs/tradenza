"""
Import Form Module - Tradenza
Provides CSRF-protected file upload form for CSV trade history ingestion.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField


class CSVImportForm(FlaskForm):
    """Secure CSRF-protected form for uploading trade CSV files."""

    csv_file = FileField(
        "CSV File",
        validators=[
            FileRequired(message="Please choose a CSV file to upload."),
            FileAllowed(["csv"], message="Only .csv files are supported.")
        ]
    )

    submit = SubmitField("Start Import")
