from core.factory import create_app
from flask import redirect, url_for, render_template
from flask_login import current_user

app = create_app()


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("landing/index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)