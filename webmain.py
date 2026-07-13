import os

from dotenv import load_dotenv
from flask import Flask

from web.gn_api import gn_bp
from web.messages import messages_bp

load_dotenv()

app = Flask(__name__, static_folder="web/static", static_url_path="/static")

app.secret_key = os.getenv("WEB_SECRET", "1234")

app.register_blueprint(messages_bp)
app.register_blueprint(gn_bp)


def main():
    app.run("::", 8080)


if __name__ == "__main__":
    main()
