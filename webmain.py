import os

from dotenv import load_dotenv
from flask import Flask

from constants import WEB_TOKEN
from web.messages import messages_bp
from web.yuri_api import yuri_bp

load_dotenv()

app = Flask(__name__, static_folder="web/static", static_url_path="/static")

app.secret_key = os.getenv("WEB_SECRET", "1234")

app.register_blueprint(messages_bp)
if WEB_TOKEN and len(WEB_TOKEN.strip()) > 0:
    app.register_blueprint(yuri_bp)


def main():
    app.run("::", 8080)


if __name__ == "__main__":
    main()
