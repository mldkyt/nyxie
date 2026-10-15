from flask import Blueprint, redirect, render_template

from constants import GUILD
from database import engine
from util.web_sync import kv_member_count, kv_online_count

web_bp = Blueprint("web", __name__, template_folder='templates', static_folder='../data/attachments',
                   static_url_path='/discord/explore/attachments')

@web_bp.route("/")
def index():
    with engine.begin() as c:
        member_count = kv_member_count.get(c, int(GUILD))
        online_count = kv_online_count.get(c, int(GUILD))

    return render_template("web_index.html", members=member_count, online=online_count)
