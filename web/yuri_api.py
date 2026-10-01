import os

from flask import Blueprint, render_template, request
from sqlalchemy import insert, select
from sqlalchemy.sql.functions import max
from werkzeug.utils import secure_filename

from database import engine, yaoi_db, yuri_db
from web.util import quick_response

yuri_bp = Blueprint("yuri", __name__)


@yuri_bp.route("/nyxie/yuri", methods=["GET", "POST"])
def yuri_post_route():
    if request.method == "POST":
        if not os.path.exists("data/yuri"):
            os.makedirs("data/yuri")

        source = request.form.get("source")
        if not source or len(source.strip()) == 0:
            return "No source"

        cw = request.form.get("cw", "")
        alt = request.form.get("alt", "")

        # Save file
        file = request.files.get("file")

        if not file or not file.filename:
            return quick_response("No file added", 400)

        filename = f"data/yuri/{secure_filename(file.filename)}"
        if not os.path.exists(filename):
            file.save(filename)

        with engine.begin() as c:
            top_priority = c.execute(
                select(max(yuri_db.c.priority)).where(yuri_db.c.approved == True)
            ).fetchone()
            if top_priority is None or top_priority[0] is None:
                top_priority = [10000]
            top_priority = top_priority[0]

            existing = c.execute(
                select(yuri_db.c.id).where(yuri_db.c.filename == filename)
            ).fetchone()
            if not existing:
                c.execute(
                    insert(yuri_db).values(
                        filename=filename,
                        source=source,
                        priority=top_priority,
                        cw=cw,
                        alt=alt,
                    )
                )
            else:
                return "Already exists, OK"

        return "Added yuri OK"

    return render_template("yuri_form.html", yuri="yuri")


@yuri_bp.route("/nyxie/yaoi", methods=["GET", "POST"])
def yaoi_post_route():
    if request.method == "POST":
        if not os.path.exists("data/yaoi"):
            os.makedirs("data/yaoi")

        source = request.form.get("source")
        if not source or len(source.strip()) == 0:
            return "No source"

        cw = request.form.get("cw", "")
        alt = request.form.get("alt", "")

        # Save file
        file = request.files.get("file")

        if not file or not file.filename:
            return quick_response("No file added", 400)

        filename = f"data/yaoi/{secure_filename(file.filename)}"
        if not os.path.exists(filename):
            file.save(filename)

        with engine.begin() as c:
            top_priority = c.execute(
                select(max(yaoi_db.c.priority)).where(yaoi_db.c.approved == True)
            ).fetchone()
            if top_priority is None or top_priority[0] is None:
                top_priority = [10000]
            top_priority = top_priority[0]

            existing = c.execute(
                select(yaoi_db.c.id).where(yaoi_db.c.filename == filename)
            ).fetchone()
            if not existing:
                c.execute(
                    insert(yaoi_db).values(
                        filename=filename,
                        source=source,
                        priority=top_priority,
                        cw=cw,
                        alt=alt,
                    )
                )
            else:
                return "Already exists, OK"

        return "Added yaoi OK"

    return render_template("yuri_form.html", yuri="yaoi")
