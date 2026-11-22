"""Controller xử lý trang Quản trị phân tích hành vi, kiểm tra tốc độ Scan và đối chiếu GoogleSQL."""

from flask import Blueprint, jsonify, render_template, request

from config import METRICS_TABLE_ID, TABLE_ID, get_connection_info
from models.bigtable_client import ensure_all_tables
from models.catalog import SAMPLE_USERS
from models.clickstream_model import benchmark_scan_comparison, get_overview_analytics
from models.metrics_model import get_daily_product_metrics

analytics_bp = Blueprint("analytics", __name__)

CONSOLE_SQL_SNIPPETS = [
    {
        "title": "Truy vấn 20 sự kiện mới nhất kèm giải mã UTF-8 (Bigtable Studio)",
        "sql": (
            f"SELECT\n"
            f"  _key,\n"
            f"  CAST(cf_event['event_type'] AS STRING) AS event_type,\n"
            f"  CAST(cf_product['product_name'] AS STRING) AS product_name,\n"
            f"  CAST(cf_product['category'] AS STRING) AS category,\n"
            f"  CAST(cf_device['device_type'] AS STRING) AS device_type,\n"
            f"  CAST(cf_device['ip_region'] AS STRING) AS ip_region\n"
            f"FROM {TABLE_ID}\n"
            f"LIMIT 20;"
        ),
    },
    {
        "title": "Lọc hành vi theo Prefix của người dùng usr_2049 (Tránh Full Table Scan)",
        "sql": (
            f"SELECT\n"
            f"  _key,\n"
            f"  CAST(cf_event['event_type'] AS STRING) AS event_type,\n"
            f"  CAST(cf_product['product_name'] AS STRING) AS product_name\n"
            f"FROM {TABLE_ID}\n"
            f"WHERE _key LIKE '9402#usr_2049#%'\n"
            f"LIMIT 10;"
        ),
    },
    {
        "title": "Thống kê tổng hợp theo loại hành vi bằng Bigtable SQL",
        "sql": (
            f"SELECT\n"
            f"  CAST(cf_event['event_type'] AS STRING) AS event_type,\n"
            f"  COUNT(*) AS total_events\n"
            f"FROM {TABLE_ID}\n"
            f"GROUP BY event_type;"
        ),
    },
    {
        "title": "Kiểm tra bộ đếm nguyên tử trong bảng thứ 2 (product_metrics)",
        "sql": (
            f"SELECT\n"
            f"  _key,\n"
            f"  cf_stats['views'] AS views_bytes,\n"
            f"  cf_stats['carts'] AS carts_bytes,\n"
            f"  cf_stats['purchases'] AS purchases_bytes\n"
            f"FROM {METRICS_TABLE_ID}\n"
            f"LIMIT 20;"
        ),
    },
]


@analytics_bp.route("/analytics")
def analytics_page():
    """Trang Dashboard Quản trị Clickstream và đối chiếu Google Cloud Bigtable Console."""
    connection = get_connection_info()
    error_message = None

    try:
        ensure_all_tables()
        overview = get_overview_analytics(sample_limit=400)
        daily_metrics = get_daily_product_metrics()
    except Exception as exc:
        error_message = str(exc)
        overview = {
            "sampled_rows": 0,
            "sample_limit": 400,
            "unique_users": 0,
            "read_latency_ms": 0.0,
            "funnel": {
                "search_keyword": 0,
                "view_product": 0,
                "add_to_cart": 0,
                "purchase_success": 0,
                "cart_rate_pct": 0.0,
                "purchase_rate_pct": 0.0,
            },
            "devices": {},
            "os": {},
            "regions": {},
            "categories": {},
            "top_keywords": [],
        }
        daily_metrics = {"available": False, "date": "", "latency_ms": 0.0, "products": []}

    return render_template(
        "analytics.html",
        active_page="analytics",
        connection=connection,
        overview=overview,
        daily_metrics=daily_metrics,
        users=SAMPLE_USERS,
        sql_snippets=CONSOLE_SQL_SNIPPETS,
        error_message=error_message,
    )


@analytics_bp.route("/api/analytics/summary", methods=["GET"])
def api_analytics_summary():
    """API trả về số liệu phễu chuyển đổi và bảng product_metrics theo thời gian thực."""
    try:
        overview = get_overview_analytics(sample_limit=400)
        daily_metrics = get_daily_product_metrics()
        return jsonify(
            {
                "status": "ok",
                "overview": overview,
                "daily_metrics": daily_metrics,
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@analytics_bp.route("/api/analytics/scan-benchmark", methods=["POST"])
def api_scan_benchmark():
    """API đo thực tế tốc độ Prefix Scan so với Full Table Scan trên dữ liệu hiện tại."""
    payload = request.get_json(silent=True) or {}
    user_id = (payload.get("user_id") or "usr_2049").strip()
    try:
        result = benchmark_scan_comparison(user_id=user_id, limit=10)
        return jsonify({"status": "ok", "benchmark": result})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
