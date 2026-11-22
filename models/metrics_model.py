"""Model quản lý bảng tổng hợp product_metrics dùng bộ đếm nguyên tử ReadModifyWrite."""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

from config import METRICS_COLUMN_FAMILIES, METRICS_TABLE_ID
from models.bigtable_client import get_table
from models.catalog import PRODUCTS_BY_ID, SAMPLE_PRODUCTS

_EVENT_TO_METRIC_COL = {
    "view_product": "views",
    "add_to_cart": "carts",
    "purchase_success": "purchases",
}


def build_metric_row_key(product_id: str, date_str: Optional[str] = None) -> str:
    """Tạo Row Key [product_id]#[YYYYMMDD] cho bảng thống kê sản phẩm theo ngày."""
    day = date_str or datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
    return f"{product_id}#{day}"


def increment_product_metric(
    product_id: str,
    event_type: str,
    price: int = 0,
    timestamp_ms: Optional[int] = None,
) -> bool:
    """Tăng bộ đếm nguyên tử (ReadModifyWrite) cho sản phẩm trong bảng product_metrics."""
    metric_col = _EVENT_TO_METRIC_COL.get(event_type)
    if not product_id or not metric_col:
        return False

    table = get_table(
        table_id=METRICS_TABLE_ID,
        column_families=METRICS_COLUMN_FAMILIES,
    )
    if table is None:
        return False

    if timestamp_ms is not None:
        day = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).astimezone().strftime("%Y%m%d")
    else:
        day = None

    row_key = build_metric_row_key(product_id, day)
    append_row = table.append_row(row_key)
    append_row.increment_cell_value("cf_stats", metric_col, 1)
    if event_type == "purchase_success" and int(price or 0) > 0:
        append_row.increment_cell_value("cf_stats", "revenue", int(price))
    append_row.commit()
    return True


def _decode_int64(raw_bytes: bytes) -> int:
    if len(raw_bytes) == 8:
        return int.from_bytes(raw_bytes, byteorder="big", signed=True)
    return int(raw_bytes.decode("utf-8", errors="ignore") or 0)


def get_daily_product_metrics(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Đọc bảng product_metrics theo ngày mà không cần quét bảng ecommerce_clickstream."""
    day = date_str or datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
    table = get_table(
        table_id=METRICS_TABLE_ID,
        column_families=METRICS_COLUMN_FAMILIES,
    )
    if table is None:
        return {
            "available": False,
            "date": day,
            "latency_ms": 0.0,
            "products": [],
        }

    start_ns = time.perf_counter_ns()
    rows = list(table.read_rows(limit=200))
    latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

    stats_by_product: Dict[str, Dict[str, int]] = {
        p["product_id"]: {"views": 0, "carts": 0, "purchases": 0, "revenue": 0}
        for p in SAMPLE_PRODUCTS
    }

    for row in rows:
        rk = row.row_key.decode("utf-8", errors="replace")
        parts = rk.split("#", 1)
        if len(parts) != 2 or parts[1] != day:
            continue
        pid = parts[0]
        if pid not in stats_by_product:
            continue
        cf = row.cells.get("cf_stats", {})
        for col_name in ("views", "carts", "purchases", "revenue"):
            cell_list = cf.get(col_name.encode("utf-8"))
            if cell_list:
                stats_by_product[pid][col_name] = _decode_int64(cell_list[0].value)

    ranked: List[Dict[str, Any]] = []
    for pid, st in stats_by_product.items():
        product = PRODUCTS_BY_ID[pid]
        score = st["views"] + st["carts"] * 3 + st["purchases"] * 5
        conversion_pct = (
            round((st["purchases"] / st["views"]) * 100.0, 1)
            if st["views"] > 0
            else 0.0
        )
        ranked.append(
            {
                "product_id": pid,
                "product_name": product["product_name"],
                "category": product["category"],
                "price": product["price"],
                "views": st["views"],
                "carts": st["carts"],
                "purchases": st["purchases"],
                "revenue": st["revenue"],
                "score": score,
                "conversion_pct": conversion_pct,
            }
        )

    ranked.sort(key=lambda item: (item["score"], item["purchases"], item["views"]), reverse=True)
    return {
        "available": True,
        "date": day,
        "latency_ms": round(latency_ms, 2),
        "products": ranked,
    }
