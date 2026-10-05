import base64
import logging
import mimetypes
import os
import sys

import flask
from flask import Blueprint, Response, flash, redirect, render_template, request
from sqlalchemy import delete, insert, select, update
from sqlalchemy.sql.functions import max
from werkzeug.utils import secure_filename

from constants import VERSION, WEB_TOKEN
from database import alt_text_suggestions, cw_suggestions, engine, yaoi_db, yuri_db
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

    return render_template(
        "yuri_form.html",
        yuri="yuri",
        version=VERSION,
        python_ver=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        flask_ver=flask.__version__,
    )


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

    return render_template(
        "yuri_form.html",
        yuri="yaoi",
        version=VERSION,
        python_ver=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        flask_ver=flask.__version__,
    )


@yuri_bp.route("/nyxie/review", methods=["GET", "POST"])
def review_posts():
    if not WEB_TOKEN or len(WEB_TOKEN) == 0:
        return "No WEB_TOKEN set set one for dev purposes"

    auth = request.authorization  # Flask parses Basic Authorization header for you
    if not auth or auth.username != "mldkyt" or auth.password != WEB_TOKEN:
        return Response(
            "Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Log in"'}
        )

    with engine.begin() as c:
        # Yuri posts
        yuri_post = c.execute(
            select(
                yuri_db.c.filename,
                yuri_db.c.source,
                yuri_db.c.cw,
                yuri_db.c.alt,
                yuri_db.c.id,
            ).where(yuri_db.c.approved == False)
        ).fetchone()

        if yuri_post:
            cw = yuri_post[2]
            alt = yuri_post[3]
            source = yuri_post[1]

            if request.method == "POST":
                if "cw" in request.form:
                    c.execute(
                        update(yuri_db)
                        .where(yuri_db.c.id == yuri_post[4])
                        .values(cw=request.form["cw"])
                    )
                    cw = request.form["cw"]
                if "alt" in request.form:
                    c.execute(
                        update(yuri_db)
                        .where(yuri_db.c.id == yuri_post[4])
                        .values(alt=request.form["alt"])
                    )
                    alt = request.form["alt"]
                if "source" in request.form:
                    c.execute(
                        update(yuri_db)
                        .where(yuri_db.c.id == yuri_post[4])
                        .values(source=request.form["source"])
                    )
                    source = request.form["source"]
                if "approve" in request.form:
                    c.execute(
                        update(yuri_db)
                        .where(yuri_db.c.id == yuri_post[4])
                        .values(approved=True)
                    )

                    return review_posts()
                if "delete" in request.form:
                    c.execute(delete(yuri_db).where(yuri_db.c.id == yuri_post[4]))
                    os.unlink(yuri_post[0])

                    return review_posts()

            with open(yuri_post[0], "rb") as f:
                data = f.read()

            b64 = base64.b64encode(data).decode("ascii")
            return render_template(
                "review.html",
                mime=mimetypes.guess_type(yuri_post[0])[0],
                img=b64,
                alt=alt,
                cw=cw,
                source=source,
                version=VERSION,
                python_ver=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                flask_ver=flask.__version__,
            )

        # Yaoi posts
        yaoi_post = c.execute(
            select(
                yaoi_db.c.filename,
                yaoi_db.c.source,
                yaoi_db.c.cw,
                yaoi_db.c.alt,
                yaoi_db.c.id,
            ).where(yaoi_db.c.approved == False)
        ).fetchone()

        if yaoi_post:
            cw = yaoi_post[2]
            alt = yaoi_post[3]
            source = yaoi_post[1]

            if request.method == "POST":
                if "cw" in request.form:
                    c.execute(
                        update(yaoi_db)
                        .where(yaoi_db.c.id == yaoi_post[4])
                        .values(cw=request.form["cw"])
                    )
                    cw = request.form["cw"]
                if "alt" in request.form:
                    c.execute(
                        update(yaoi_db)
                        .where(yaoi_db.c.id == yaoi_post[4])
                        .values(alt=request.form["alt"])
                    )
                    alt = request.form["alt"]
                if "source" in request.form:
                    c.execute(
                        update(yaoi_db)
                        .where(yaoi_db.c.id == yaoi_post[4])
                        .values(source=request.form["source"])
                    )
                    source = request.form["source"]
                if "approve" in request.form:
                    c.execute(
                        update(yaoi_db)
                        .where(yaoi_db.c.id == yaoi_post[4])
                        .values(approved=True)
                    )

                    return review_posts()
                if "delete" in request.form:
                    c.execute(delete(yaoi_db).where(yaoi_db.c.id == yaoi_post[4]))
                    os.unlink(yaoi_post[0])

                    return review_posts()

            with open(yaoi_post[0], "rb") as f:
                data = f.read()

            b64 = base64.b64encode(data).decode("ascii")
            return render_template(
                "review.html",
                mime=mimetypes.guess_type(yaoi_post[0])[0],
                img=b64,
                alt=alt,
                cw=cw,
                source=source,
                version=VERSION,
                python_ver=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                flask_ver=flask.__version__,
            )

    return "No posts to review"


@yuri_bp.route("/nyxie/info", methods=["GET", "POST"])
def info():
    if "t" not in request.args or request.args["t"] not in ["yuri", "yaoi"]:
        return quick_response("Not found", 404)

    if "id" not in request.args or not request.args["id"].isnumeric():
        return quick_response("Not found", 404)

    type = request.args["t"]
    db = yuri_db if type == "yuri" else yaoi_db

    with engine.begin() as c:
        yuri = c.execute(
            select(db.c.filename, db.c.source, db.c.cw, db.c.alt).where(
                (db.c.id == int(request.args["id"])) & (db.c.approved == True)
            )
        ).fetchone()

    if yuri is None:
        return quick_response("Not found", 404)

    # Suggest CW and alt text
    if request.method == "POST":
        if "alt" in request.form:
            if len(yuri[3]) == 0:
                with engine.begin() as c:
                    suggestion = c.execute(
                        select(alt_text_suggestions).where(
                            alt_text_suggestions.c.fid == int(request.args["id"])
                        )
                    ).fetchone()

                    if suggestion is None:
                        c.execute(
                            insert(alt_text_suggestions).values(
                                fid=int(request.args["id"]),
                                type=type,
                                alt=request.form["alt"],
                            )
                        )

                        flash("Alt text suggestion was sent successfully")
                    else:
                        flash("Alt text suggestion already pending")

            else:
                flash("Alt text already exists")
        elif "cw" in request.form:
            with engine.begin() as c:
                c.execute(
                    insert(cw_suggestions).values(
                        fid=int(request.args["id"]), type=type, cw=request.form["cw"]
                    )
                )

            flash("CW suggestion was sent successfully")

    with open(yuri[0], "rb") as f:
        data = f.read()

    b64 = base64.b64encode(data).decode("ascii")

    return render_template(
        "info.html",
        yuri=type,
        cw=yuri[2],
        source=yuri[1],
        id=int(request.args["id"]),
        alt=yuri[3],
        img=b64,
        mime=mimetypes.guess_type(yuri[0])[0],
    )


@yuri_bp.route("/nyxie/review_suggestions", methods=["GET", "POST"])
def review_suggestions():
    if not WEB_TOKEN or len(WEB_TOKEN) == 0:
        return "No WEB_TOKEN set set one for dev purposes"

    auth = request.authorization  # Flask parses Basic Authorization header for you
    if not auth or auth.username != "mldkyt" or auth.password != WEB_TOKEN:
        return Response(
            "Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Log in"'}
        )

    with engine.begin() as c:
        # Alt texts
        alt_text_suggestion = c.execute(
            select(
                alt_text_suggestions.c.id,
                alt_text_suggestions.c.fid,
                alt_text_suggestions.c.type,
                alt_text_suggestions.c.alt,
            )
        ).fetchone()

        if alt_text_suggestion is not None:
            db = yuri_db if alt_text_suggestion[2] == "yuri" else yaoi_db

            if request.method == "POST":
                if "approve" in request.form:
                    c.execute(
                        update(db)
                        .values(alt=alt_text_suggestion[3])
                        .where(db.c.id == alt_text_suggestion[1])
                    )

                    c.execute(
                        delete(alt_text_suggestions).where(
                            alt_text_suggestions.c.id == alt_text_suggestion[0]
                        )
                    )

                    return redirect("/nyxie/review_suggestions", 303)
                elif "decline" in request.form:
                    c.execute(
                        delete(alt_text_suggestions).where(
                            alt_text_suggestions.c.id == alt_text_suggestion[0]
                        )
                    )

                    return redirect("/nyxie/review_suggestions", 303)

            yuri = c.execute(
                select(db.c.filename).where(db.c.id == alt_text_suggestion[1])
            ).fetchone()

            if yuri is None:
                c.execute(
                    delete(alt_text_suggestions).where(
                        alt_text_suggestions.c.id == alt_text_suggestion[0]
                    )
                )

                return review_suggestions()

            with open(yuri[0], "rb") as f:
                data = f.read()

            b64 = base64.b64encode(data).decode("ascii")

            return render_template(
                "review_suggestions.html",
                type=alt_text_suggestion[2],
                mime=mimetypes.guess_type(yuri[0])[0],
                img=b64,
                alt=alt_text_suggestion[3],
                suggestion="Alt text: " + alt_text_suggestion[3],
                id=alt_text_suggestion[0],
            )

        # CWs
        cw_suggestion = c.execute(
            select(
                cw_suggestions.c.id,
                cw_suggestions.c.fid,
                cw_suggestions.c.type,
                cw_suggestions.c.cw,
            )
        ).fetchone()

        if cw_suggestion is not None:
            db = yuri_db if cw_suggestion[2] == "yuri" else yaoi_db

            if request.method == "POST":
                if "approve" in request.form:
                    c.execute(
                        update(db)
                        .values(cw=cw_suggestion[3])
                        .where(db.c.id == cw_suggestion[1])
                    )

                    c.execute(
                        delete(cw_suggestions).where(
                            cw_suggestions.c.id == cw_suggestion[0]
                        )
                    )

                    return redirect("/nyxie/review_suggestions", 303)
                elif "decline" in request.form:
                    c.execute(
                        delete(cw_suggestions).where(
                            cw_suggestions.c.id == cw_suggestion[0]
                        )
                    )

                    return redirect("/nyxie/review_suggestions", 303)

            yuri = c.execute(
                select(db.c.filename).where(db.c.id == cw_suggestion[1])
            ).fetchone()

            if yuri is None:
                c.execute(
                    delete(cw_suggestions).where(
                        cw_suggestions.c.id == cw_suggestion[0]
                    )
                )

                return review_suggestions()

            with open(yuri[0], "rb") as f:
                data = f.read()

            b64 = base64.b64encode(data).decode("ascii")

            return render_template(
                "review_suggestions.html",
                type=cw_suggestion[2],
                mime=mimetypes.guess_type(yuri[0])[0],
                img=b64,
                alt=cw_suggestion[3],
                suggestion="CW: " + cw_suggestion[3],
                id=cw_suggestion[0],
            )

    return "Nothing to approve"
