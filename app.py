"""Điểm khởi chạy ứng dụng Flask theo kiến trúc MVC."""

import os

from flask import Flask

from controllers import register_blueprints


def create_app() -> Flask:
    """Khởi tạo Flask App và đăng ký toàn bộ Blueprint tầng Controller."""
    flask_app = Flask(__name__)
    register_blueprints(flask_app)
    return flask_app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
