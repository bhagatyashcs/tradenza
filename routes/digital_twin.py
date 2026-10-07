from flask import Blueprint, render_template
from flask_login import login_required, current_user

from services.digital_twin_service import DigitalTwinService


digital_twin_bp = Blueprint(
    "digital_twin",
    __name__,
    url_prefix="/digital-twin"
)


@digital_twin_bp.route("/")
@login_required
def digital_twin():
    twin = DigitalTwinService().get_twin(
        current_user
    )

    return render_template(
        "digital_twin/digital_twin.html",
        twin=twin
    )