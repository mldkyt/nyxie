from flask import Blueprint, render_template, redirect, request

from util.web_sync import get_channels, get_latest_messages, get_surrounding_messages, get_title_for_channel

messages_bp = Blueprint("messages", __name__, template_folder='templates', static_folder='static',
                        static_url_path='/static')


@messages_bp.route("/discord/explore")
def explore_index():
    channels = get_channels()
    return render_template("messages.html", messages=[], channels=channels)


@messages_bp.route("/discord/explore/<channel_id>")
def explore_channel(channel_id: str):
    if not channel_id.isnumeric():
        return redirect("/explore")

    channels = get_channels()
    title = get_title_for_channel(int(channel_id))
    if title is None:
        return redirect("/explore")

    if "m" in request.args:
        if not request.args["m"].isnumeric():
            return redirect(f"/explore/{channel_id}")

        messages = get_surrounding_messages(int(request.args["m"]))
    else:
        messages = get_latest_messages(int(channel_id))

    return render_template("messages.html", title=title, messages=messages, channels=channels)


@messages_bp.route("/discord/explore/<channel_id>/<thread_id>")
def explore_thread(channel_id: str, thread_id: str):
    if not channel_id.isnumeric():
        return redirect("/explore")
    if not thread_id.isnumeric():
        return redirect(f"/explore/{channel_id}")

    channels = get_channels()
    title = get_title_for_channel(int(thread_id))
    if title is None:
        return redirect(f"/explore/{channel_id}")

    if "m" in request.args:
        if not request.args["m"].isnumeric():
            return redirect(f"/explore/{channel_id}")

        messages = get_surrounding_messages(int(request.args["m"]))
    else:
        messages = get_latest_messages(int(thread_id))

    return render_template("messages.html", title=title, return_channel_id=channel_id, messages=messages,
                           channels=channels)
