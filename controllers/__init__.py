"""Đăng ký các Blueprint tầng Controller theo mô hình MVC."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Đăng ký Blueprint cho Cửa hàng, Quản trị Analytics và Trình giả lập Traffic."""
    from controllers.analytics_controller import analytics_bp
    from controllers.shop_controller import shop_bp
    from controllers.simulator_controller import simulator_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(simulator_bp)
