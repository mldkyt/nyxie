import json
import os
from pprint import pprint

from flask import Blueprint, request
from sqlalchemy import insert, select
from werkzeug.utils import secure_filename

from constants import WEB_TOKEN
from database import engine, yuri_db
from web.gn_api import quick_response

yuri_bp = Blueprint("yuri", __name__)


@yuri_bp.route("/api/yuri", methods=["POST"])
def yuri_post_route():
    # Verify WEB_TOKEN exists
    if not WEB_TOKEN:
        raise ValueError("WEB_TOKEN should have been set when this module is loaded!")

    # Verify request
    if request.headers.get("Authorization", "") != WEB_TOKEN:
        return quick_response("Unauthorized", 403)

    if not os.path.exists("data/yuri"):
        os.makedirs("data/yuri")

    # Get metadata
    metadata = request.form.get("json")
    if not metadata:
        return quick_response("No JSON data", 400)

    metadata = json.loads(metadata)
    if not metadata.get("source"):
        return quick_response("No source", 400)

    # Save file
    file = request.files.get("file")

    if not file or not file.filename:
        return quick_response("No file added", 400)

    filename = f"data/yuri/{secure_filename(file.filename)}"
    if not os.path.exists(filename):
        file.save(filename)

    with engine.begin() as c:
        existing = c.execute(
            select(yuri_db.c.id).where(yuri_db.c.filename == filename)
        ).fetchone()
        if not existing:
            c.execute(
                insert(yuri_db).values(
                    filename=filename,
                    source=metadata.get("source"),
                )
            )
        else:
            return "Already exists, OK"

    return "Added yuri OK"
