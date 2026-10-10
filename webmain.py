import os

import sentry_sdk
from dotenv import load_dotenv
from flask import Flask

from constants import SENTRY_SDK
from web.messages import messages_bp
from web.web import web_bp
from web.yuri_api import yuri_bp

load_dotenv()

if SENTRY_SDK:
    sentry_sdk.init(
        dsn=SENTRY_SDK,
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=1,
        auto_session_tracking=False,
    )
app = Flask(__name__, static_folder="web/static", static_url_path="/static")

app.secret_key = os.getenv("WEB_SECRET", "1234")

app.register_blueprint(messages_bp)
app.register_blueprint(yuri_bp)
app.register_blueprint(web_bp)


def main():
    app.run("::", 8080)


if __name__ == "__main__":
    main()
