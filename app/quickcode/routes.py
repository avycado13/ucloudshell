from app.quickcode import bp
from flask import render_template, flash


@bp.route("/")
def test():
    return render_template("errors/500.html"), 500
