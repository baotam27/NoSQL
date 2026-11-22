"""Lớp facade giữ tương thích giao diện hàm cũ và ủy quyền về tầng models MVC."""

from config import COLUMN_FAMILIES, TABLE_ID
from models.bigtable_client import ensure_all_tables, ensure_table_exists, get_table
from models.catalog import (
    CATEGORIES,
    EVENT_WEIGHTS,
    MAX_INT64,
    PRODUCTS_BY_ID,
    SAMPLE_PRODUCTS,
    SAMPLE_USERS,
    VALID_EVENT_TYPES,
)
from models.clickstream_model import (
    benchmark_scan_comparison,
    build_hotspot_row_key,
    build_row_key,
    detect_user_anomaly,
    get_overview_analytics,
    get_weighted_recommendations,
    log_clickstream_batch,
    log_clickstream_event,
    query_user_events,
    reverse_user_id,
)
from models.metrics_model import get_daily_product_metrics, increment_product_metric


def get_recent_user_events(user_id: str, limit: int = 10):
    """Truy xuất N hành vi gần nhất của user bằng Prefix Scan."""
    return query_user_events(user_id=user_id, limit=limit)


def get_realtime_recommendations(user_id: str, limit: int = 4):
    """Gợi ý sản phẩm theo trọng số hành vi gần nhất của user."""
    return get_weighted_recommendations(user_id=user_id, limit=limit)


__all__ = [
    "CATEGORIES",
    "COLUMN_FAMILIES",
    "EVENT_WEIGHTS",
    "MAX_INT64",
    "PRODUCTS_BY_ID",
    "SAMPLE_PRODUCTS",
    "SAMPLE_USERS",
    "TABLE_ID",
    "VALID_EVENT_TYPES",
    "benchmark_scan_comparison",
    "build_hotspot_row_key",
    "build_row_key",
    "ensure_all_tables",
    "ensure_table_exists",
    "get_daily_product_metrics",
    "get_overview_analytics",
    "get_realtime_recommendations",
    "get_recent_user_events",
    "get_table",
    "get_weighted_recommendations",
    "increment_product_metric",
    "log_clickstream_batch",
    "log_clickstream_event",
    "query_user_events",
    "reverse_user_id",
]
