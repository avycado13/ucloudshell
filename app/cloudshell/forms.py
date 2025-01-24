from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class ContainerForm(FlaskForm):
    container_id = StringField(
        "Container ID",
        validators=[DataRequired()],
        render_kw={"placeholder": "Enter container id"},
    )
    shell_submit = SubmitField("Web Shell")
    delete_submit = SubmitField("Delete container")
    stop_submit = SubmitField("Stop container")
    start_submit = SubmitField("Start container")
    wireguard_submit = SubmitField("Setup WireGuard")
