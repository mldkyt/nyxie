import datetime
import random

from flask import Blueprint, make_response, request
from mastodon import Mastodon
from sqlalchemy import delete, select

from database import engine, gn

gn_bp = Blueprint("gn", __name__)

mastodon = Mastodon(
    client_id="data/pytooter_clientcred.secret",
    access_token="data/pytooter_usercred.secret",
)


def quick_response(msg: str, code: int):
    response = make_response(msg)
    response.status_code = code

    return response


@gn_bp.route("/api/lunamon/gn", methods=["POST"])
def post_gn():
    the_body = request.get_json()

    if "token" not in the_body:
        return quick_response("No token provided", 400)

    now = datetime.datetime.now()

    with engine.begin() as c:
        c.execute(delete(gn).where(gn.c.expiry < now))

        gn_d = c.execute(
            select(gn.c.type, gn.c.id).where((gn.c.auth_code == the_body["token"]))
        ).fetchone()

    if gn_d is None:
        return quick_response("Invalid token provided", 404)

    if gn_d[0] == "morning":
        message = random.choice(
            [
                "min" + "u" * random.randint(1, 3),
                "morni",
                "meowning",
                "morning",
                "meowning :3",
                "morning :3",
            ]
        )

        mastodon.toot(message)

    elif gn_d[0] == "evening":
        message = random.choice(
            [
                "bin" + "u" * random.randint(1, 3),
                "nin" + "i" * random.randint(1, 3),
                "nainai",
                "niniii :3",
                "night",
                "gn",
            ]
        )

        mastodon.toot(message)

    with engine.begin() as c:
        c.execute(delete(gn).where((gn.c.id == gn_d[1])))

    return quick_response("ok", 200)
