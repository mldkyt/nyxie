from idlelib.rpc import request_queue

from flask import Blueprint, render_template, redirect, request, session

from util.web_sync import get_channels, get_latest_messages, get_surrounding_messages, get_title_for_channel, \
    process_preferences, get_pinned_messages, search_messages, get_reply_thread

messages_bp = Blueprint("messages", __name__, template_folder='templates', static_folder='static',
                        static_url_path='/static')


@messages_bp.route("/discord/explore", methods=["GET", "POST"])
def explore_index():
    if request.method == "POST":
        process_preferences()
        return redirect("/discord/explore", 303)

    channels = get_channels()

    if "q" in request.args:
        messages = search_messages(request.args["q"])
        return render_template("messages.html", messages=messages, channels=channels)

    return render_template("messages.html", messages=[], channels=channels, preferences=True)


@messages_bp.route("/discord/explore/<channel_id>")
def explore_channel(channel_id: str):
    if not channel_id.isnumeric():
        return redirect("/discord/explore")

    channels = get_channels()
    title = get_title_for_channel(int(channel_id))
    if title is None:
        return redirect("/discord/explore")

    show_more = "more" in session and session["more"] == "1"

    if "p" in request.args and request.args["p"] == "1":
        messages = get_pinned_messages(int(channel_id))
        return render_template("messages.html", title=f"Pinned messages in {title}", messages=messages, channels=channels, show_more=show_more)

    if "m" in request.args:
        if not request.args["m"].isnumeric():
            return redirect(f"/discord/explore/{channel_id}")

        messages = get_surrounding_messages(int(request.args["m"]), show_more=show_more)
    elif "t" in request.args:
        if not request.args["t"].isnumeric():
            return redirect(f"/discord/explore/{channel_id}")

        messages = get_reply_thread(int(request.args["t"]))
    else:
        messages = get_latest_messages(int(channel_id), show_more=show_more)

    return render_template("messages.html", title=title, messages=messages, channels=channels, show_more=show_more)


@messages_bp.route("/discord/explore/<channel_id>/<thread_id>")
def explore_thread(channel_id: str, thread_id: str):
    if not channel_id.isnumeric():
        return redirect("/discord/explore")
    if not thread_id.isnumeric():
        return redirect(f"/discord/explore/{channel_id}")

    channels = get_channels()
    title = get_title_for_channel(int(thread_id))
    if title is None:
        return redirect(f"/discord/explore/{channel_id}")

    show_more = "more" in session and session["more"] == "1"

    if "m" in request.args:
        if not request.args["m"].isnumeric():
            return redirect(f"/discord/explore/{channel_id}")

        messages = get_surrounding_messages(int(request.args["m"]), show_more=show_more)
    elif "t" in request.args:
        if not request.args["t"].isnumeric():
            return redirect(f"/discord/explore/{channel_id}")

        messages = get_reply_thread(int(request.args["m"]))
    else:
        messages = get_latest_messages(int(thread_id), show_more=show_more)

    return render_template("messages.html", title=title, return_channel_id=channel_id, messages=messages,
                           channels=channels, show_more=show_more)
