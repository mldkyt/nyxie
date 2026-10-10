from flask import Blueprint, redirect

web_bp = Blueprint("web", __name__, template_folder='templates', static_folder='../data/attachments',
                   static_url_path='/discord/explore/attachments')


@web_bp.route("/")
def index():
    return redirect("https://discord.gg/aE2MXH5Qp6", 303)
