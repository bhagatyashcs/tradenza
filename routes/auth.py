from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user

from forms.auth_forms import RegisterForm, LoginForm
from services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():

        success, message = AuthService.register_user(
            form.name.data,
            form.email.data,
            form.password.data
        )

        flash(message)

        if success:
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()

    if form.validate_on_submit():

        user = AuthService.authenticate(
            form.email.data,
            form.password.data
        )

        if user:
            login_user(user)

            flash("Welcome back!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(url_for("dashboard.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():

    logout_user()

    flash("Logged out successfully.", "info")

    return redirect(url_for("auth.login"))