from flask import Blueprint, render_template
from flask_login import login_required, current_user

learn_bp = Blueprint("learn", __name__, url_prefix="/learn")


@learn_bp.route("/")
@login_required
def learn():
    return render_template(
        "learn/learn.html",
        user=current_user
    )
