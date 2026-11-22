"""Controller xử lý giao diện sàn thương mại điện tử và API ghi/lọc Clickstream."""

import time
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

from config import COLUMN_FAMILIES, get_connection_info
from models.bigtable_client import ensure_table_exists
from models.catalog import (
    CATEGORIES,
    CATEGORY_BANNERS,
    PRODUCTS_BY_ID,
    QUICK_KEYWORDS,
    SAMPLE_PRODUCTS,
    SAMPLE_USERS,
    USER_PROFILES,
)
from models.clickstream_model import (
    detect_user_anomaly,
    get_weighted_recommendations,
    log_clickstream_event,
    query_user_events,
    reverse_user_id,
)

shop_bp = Blueprint("shop", __name__)


def _detect_device_info(user_agent: str) -> Tuple[str, str]:
    """Phân tích User-Agent để xác định loại thiết bị và hệ điều hành."""
    ua = (user_agent or "").lower()
    if any(token in ua for token in ("mobile", "iphone", "android")):
        device_type = "Mobile"
    elif "ipad" in ua or "tablet" in ua:
        device_type = "Tablet"
    else:
        device_type = "Desktop"

    if "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown"

    return device_type, os_name


def _parse_time_range(range_minutes_raw: str) -> Tuple[Optional[int], Optional[int]]:
    """Chuyển tham số số phút gần nhất sang cặp (start_ms, end_ms) cho Time-Range Scan."""
    if not range_minutes_raw or range_minutes_raw == "all":
        return None, None
    try:
        minutes = int(range_minutes_raw)
    except ValueError:
        return None, None
    if minutes <= 0:
        return None, None
    now_ms = int(time.time() * 1000)
    return now_ms - minutes * 60 * 1000, now_ms


def _parse_families(families_raw: str) -> Optional[Tuple[str, ...]]:
    if not families_raw:
        return None
    parts = tuple(p.strip() for p in families_raw.split(",") if p.strip() in COLUMN_FAMILIES)
    return parts or None


def _fetch_user_dashboard(
    user_id: str,
    limit: int = 10,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
    event_type: str = "",
    families: Optional[Tuple[str, ...]] = None,
) -> Dict[str, Any]:
    """Lấy đồng bộ nhật ký hành vi, gợi ý có trọng số và sản phẩm vừa xem cho user."""
    recent = query_user_events(
        user_id=user_id,
        limit=limit,
        start_ms=start_ms,
        end_ms=end_ms,
        event_type=event_type,
        families=families,
    )
    recommendations = get_weighted_recommendations(user_id=user_id, limit=4)
    fraud_status = detect_user_anomaly(user_id=user_id, window_seconds=10, threshold=8)
    profile = USER_PROFILES.get(
        user_id,
        {
            "user_id": user_id,
            "name": user_id,
            "segment": "Khách hàng",
            "avatar": "KH",
            "default_region": "VN-HCM",
        },
    )
    return {
        "user_profile": profile,
        "recent": recent,
        "recommendations": recommendations,
        "fraud_status": fraud_status,
    }


@shop_bp.route("/")
def shop_page():
    """Trang chủ sàn thương mại điện tử cá nhân hóa và bảng nhật ký Bigtable thời gian thực."""
    selected_user = request.args.get("user_id", "usr_2049")
    if selected_user not in SAMPLE_USERS:
        selected_user = "usr_2049"

    user_profiles = [
        {
            "user_id": uid,
            "reversed_prefix": reverse_user_id(uid),
            **USER_PROFILES.get(uid, {}),
        }
        for uid in SAMPLE_USERS
    ]
    connection = get_connection_info()
    error_message = None

    try:
        ensure_table_exists()
        dashboard = _fetch_user_dashboard(selected_user, limit=10)
    except Exception as exc:
        error_message = str(exc)
        dashboard = {
            "user_profile": USER_PROFILES.get(selected_user, {}),
            "recent": {
                "user_id": selected_user,
                "prefix": f"{reverse_user_id(selected_user)}#{selected_user}#",
                "scan_mode": "Prefix Scan",
                "filter_applied": "Không dùng Filter",
                "limit": 10,
                "latency_ms": 0.0,
                "events": [],
            },
            "recommendations": {
                "user_id": selected_user,
                "target_category": "Nổi bật",
                "category_scores": {},
                "dynamic_banner": CATEGORY_BANNERS["Nổi bật"],
                "recently_viewed": [],
                "analyzed_events_count": 0,
                "reason": "Chưa kết nối được Bigtable, hiển thị sản phẩm mặc định",
                "query_latency_ms": 0.0,
                "recommendations": SAMPLE_PRODUCTS[:4],
            },
            "fraud_status": {
                "user_id": selected_user,
                "risk_level": "NORMAL",
                "label": "An toàn",
                "message": "Chưa có dữ liệu giám sát.",
                "events_in_window": 0,
                "purchases_in_window": 0,
                "window_seconds": 10,
                "threshold": 8,
                "latency_ms": 0.0,
            },
        }

    return render_template(
        "shop.html",
        active_page="shop",
        products=SAMPLE_PRODUCTS,
        categories=CATEGORIES,
        quick_keywords=QUICK_KEYWORDS,
        users=user_profiles,
        user_profiles_map=USER_PROFILES,
        selected_user=selected_user,
        connection=connection,
        dashboard=dashboard,
        error_message=error_message,
    )


@shop_bp.route("/api/clickstream", methods=["GET"])
def api_clickstream():
    """API truy vấn nhật ký hành vi với Time-Range Scan và Server-side RowFilter."""
    user_id = (request.args.get("user_id") or "usr_2049").strip()
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    range_minutes = (request.args.get("range_minutes") or "all").strip()
    event_type = (request.args.get("event_type") or "").strip()
    families = _parse_families((request.args.get("families") or "").strip())
    start_ms, end_ms = _parse_time_range(range_minutes)

    try:
        dashboard = _fetch_user_dashboard(
            user_id=user_id,
            limit=limit,
            start_ms=start_ms,
            end_ms=end_ms,
            event_type=event_type,
            families=families,
        )
        return jsonify({"status": "ok", "connection": get_connection_info(), **dashboard})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@shop_bp.route("/api/event", methods=["POST"])
def api_log_event():
    """API ghi sự kiện từ giao diện web vào Bigtable và cập nhật bảng thống kê."""
    payload = request.get_json(silent=True) or {}
    user_id = (payload.get("user_id") or "usr_2049").strip()
    event_type = (payload.get("event_type") or "").strip()
    session_id = (payload.get("session_id") or f"sess_{user_id}").strip()
    page_url = (payload.get("page_url") or "/").strip()
    product_id = (payload.get("product_id") or "").strip()
    search_keyword = (payload.get("search_keyword") or "").strip()
    ip_region = (payload.get("ip_region") or "VN-HCM").strip()

    range_minutes = (payload.get("range_minutes") or "all").strip()
    filter_event_type = (payload.get("filter_event_type") or "").strip()
    families = _parse_families((payload.get("families") or "").strip())
    start_ms, end_ms = _parse_time_range(range_minutes)

    product = PRODUCTS_BY_ID.get(product_id) if product_id else None
    product_name = payload.get("product_name") or (product["product_name"] if product else "")
    category = payload.get("category") or (product["category"] if product else "")
    price = payload.get("price") if payload.get("price") is not None else (product["price"] if product else 0)

    device_type, os_name = _detect_device_info(request.headers.get("User-Agent", ""))
    if payload.get("device_type"):
        device_type = str(payload["device_type"])

    try:
        logged = log_clickstream_event(
            user_id=user_id,
            event_type=event_type,
            session_id=session_id,
            page_url=page_url,
            product_id=product_id,
            product_name=product_name,
            category=category,
            price=price,
            search_keyword=search_keyword,
            device_type=device_type,
            os=os_name,
            ip_region=ip_region,
        )
        dashboard = _fetch_user_dashboard(
            user_id=user_id,
            limit=10,
            start_ms=start_ms,
            end_ms=end_ms,
            event_type=filter_event_type,
            families=families,
        )
        return jsonify({"status": "ok", "logged_event": logged, **dashboard})
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
