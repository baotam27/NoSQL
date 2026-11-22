"""Model thao tác bảng ecommerce_clickstream: Row Key, Time-Range Scan, RowFilter và gợi ý có trọng số."""

from collections import Counter
from datetime import datetime, timezone
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from google.cloud.bigtable.row_filters import (
    ColumnQualifierRegexFilter,
    ConditionalRowFilter,
    FamilyNameRegexFilter,
    PassAllFilter,
    RowFilterChain,
    ValueRegexFilter,
)
from google.cloud.bigtable.row_set import RowSet

from config import COLUMN_FAMILIES, TABLE_ID
from models.bigtable_client import get_table
from models.catalog import (
    CATEGORY_BANNERS,
    EVENT_WEIGHTS,
    MAX_INT64,
    PRODUCTS_BY_ID,
    SAMPLE_PRODUCTS,
    VALID_EVENT_TYPES,
    infer_category_from_keyword,
)
from models.metrics_model import increment_product_metric


def reverse_user_id(user_id: str) -> str:
    """Đảo ngược phần định danh sau dấu '_' (hoặc toàn bộ chuỗi) để tránh Hotspotting."""
    clean_id = (user_id or "guest").strip()
    if "_" in clean_id:
        suffix = clean_id.rsplit("_", 1)[-1]
        if suffix:
            return suffix[::-1]
    return clean_id[::-1]


def build_row_key(
    user_id: str, timestamp_ms: Optional[int] = None
) -> Tuple[str, int]:
    """Tạo Row Key chuẩn chống Hotspotting: [reversed_user_id]#[user_id]#[reverse_timestamp]."""
    ts_ms = int(timestamp_ms if timestamp_ms is not None else time.time() * 1000)
    reversed_uid = reverse_user_id(user_id)
    reverse_ts = MAX_INT64 - ts_ms
    row_key = f"{reversed_uid}#{user_id}#{reverse_ts:019d}"
    return row_key, ts_ms


def split_row_key_parts(row_key: str) -> Dict[str, str]:
    """Tách Row Key thành 3 thành phần để hiển thị giải phẫu khóa trên giao diện."""
    parts = (row_key or "").split("#")
    if len(parts) == 3:
        return {
            "reversed_uid": parts[0],
            "user_id": parts[1],
            "reverse_ts": parts[2],
            "is_optimal": "true",
        }
    if len(parts) == 2:
        return {
            "reversed_uid": "HOTSPOT",
            "user_id": parts[1],
            "reverse_ts": parts[0],
            "is_optimal": "false",
        }
    return {
        "reversed_uid": "",
        "user_id": row_key,
        "reverse_ts": "",
        "is_optimal": "false",
    }


def build_hotspot_row_key(user_id: str, timestamp_ms: int) -> str:
    """Tạo Row Key tuần tự theo thời gian dùng để mô phỏng lỗi Hotspotting."""
    return f"{timestamp_ms}#{user_id}"


def _ms_to_utc_datetime(timestamp_ms: int) -> datetime:
    """Chuyển timestamp mili-giây sang datetime UTC theo độ phân giải mili-giây của Bigtable."""
    seconds, millis = divmod(int(timestamp_ms), 1000)
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
        microsecond=millis * 1000
    )


def _decode_bytes(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def build_direct_row(
    table,
    user_id: str,
    event_type: str,
    session_id: str = "",
    page_url: str = "/",
    product_id: str = "",
    product_name: str = "",
    category: str = "",
    price: Any = 0,
    search_keyword: str = "",
    device_type: str = "Desktop",
    os: str = "Windows",
    ip_region: str = "VN-HCM",
    timestamp_ms: Optional[int] = None,
    row_key_override: Optional[str] = None,
):
    """Tạo đối tượng DirectRow chứa dữ liệu 3 Column Families cho thao tác ghi đơn hoặc ghi lô."""
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"event_type không hợp lệ: {event_type}")

    if row_key_override is not None:
        ts_ms = int(timestamp_ms if timestamp_ms is not None else time.time() * 1000)
        row_key = row_key_override
    else:
        row_key, ts_ms = build_row_key(user_id=user_id, timestamp_ms=timestamp_ms)

    resolved_category = category or infer_category_from_keyword(search_keyword)
    cell_timestamp = _ms_to_utc_datetime(ts_ms)

    cf_event_data = {
        "event_type": str(event_type),
        "session_id": str(session_id),
        "page_url": str(page_url),
    }
    cf_product_data = {
        "product_id": str(product_id),
        "product_name": str(product_name),
        "category": str(resolved_category),
        "price": str(price if price is not None else 0),
        "search_keyword": str(search_keyword),
    }
    cf_device_data = {
        "device_type": str(device_type),
        "os": str(os),
        "ip_region": str(ip_region),
    }

    row = table.direct_row(row_key)
    for col, val in cf_event_data.items():
        row.set_cell("cf_event", col, val.encode("utf-8"), timestamp=cell_timestamp)
    for col, val in cf_product_data.items():
        row.set_cell("cf_product", col, val.encode("utf-8"), timestamp=cell_timestamp)
    for col, val in cf_device_data.items():
        row.set_cell("cf_device", col, val.encode("utf-8"), timestamp=cell_timestamp)

    metadata = {
        "row_key": row_key,
        "row_key_parts": split_row_key_parts(row_key),
        "user_id": user_id,
        "timestamp_ms": ts_ms,
        "cf_event": cf_event_data,
        "cf_product": cf_product_data,
        "cf_device": cf_device_data,
    }
    return row, metadata


def log_clickstream_event(
    user_id: str,
    event_type: str,
    session_id: str = "",
    page_url: str = "/",
    product_id: str = "",
    product_name: str = "",
    category: str = "",
    price: Any = 0,
    search_keyword: str = "",
    device_type: str = "Desktop",
    os: str = "Windows",
    ip_region: str = "VN-HCM",
    timestamp_ms: Optional[int] = None,
    row_key_override: Optional[str] = None,
    update_metrics: bool = True,
) -> Dict[str, Any]:
    """Ghi một sự kiện Clickstream vào bảng chính và cập nhật bộ đếm nguyên tử nếu có sản phẩm."""
    table = get_table(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)
    row, metadata = build_direct_row(
        table=table,
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
        os=os,
        ip_region=ip_region,
        timestamp_ms=timestamp_ms,
        row_key_override=row_key_override,
    )

    start_ns = time.perf_counter_ns()
    row.commit()
    latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    metadata["write_latency_ms"] = round(latency_ms, 2)

    if update_metrics and product_id and product_id in PRODUCTS_BY_ID:
        try:
            increment_product_metric(
                product_id=product_id,
                event_type=event_type,
                price=int(price or 0),
                timestamp_ms=metadata["timestamp_ms"],
            )
        except Exception:
            pass

    return metadata


def log_clickstream_batch(events: Iterable[Dict[str, Any]], chunk_size: int = 250) -> Dict[str, Any]:
    """Ghi lô nhiều sự kiện cùng lúc qua mutate_rows để đạt thông lượng cao."""
    table = get_table(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)
    rows = []
    for ev in events:
        row, _ = build_direct_row(table=table, **ev)
        rows.append(row)

    total = len(rows)
    failed = 0
    batch_latencies_ms: List[float] = []

    overall_start = time.perf_counter()
    for offset in range(0, total, chunk_size):
        chunk = rows[offset : offset + chunk_size]
        t0 = time.perf_counter_ns()
        statuses = table.mutate_rows(chunk)
        batch_latencies_ms.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        for st in statuses:
            if st.code != 0:
                failed += 1

    total_time_sec = time.perf_counter() - overall_start
    return {
        "total": total,
        "succeeded": total - failed,
        "failed": failed,
        "total_time_sec": total_time_sec,
        "batch_latencies_ms": batch_latencies_ms,
    }


def _parse_timestamp_from_row(row_key: str, cells: Dict[str, Any]) -> int:
    """Trích xuất timestamp mili-giây từ Row Key đảo ngược hoặc từ metadata cell."""
    parts = row_key.split("#")
    if len(parts) == 3 and parts[2].isdigit():
        return MAX_INT64 - int(parts[2])
    if len(parts) == 2 and parts[0].isdigit():
        return int(parts[0])

    for family_cols in cells.values():
        for cell_list in family_cols.values():
            if cell_list:
                return int(cell_list[0].timestamp.timestamp() * 1000)
    return 0


def _decode_row(row) -> Dict[str, Any]:
    """Giải mã một PartialRowData thành cấu trúc từ điển phục vụ Controller và View."""
    row_key_str = _decode_bytes(row.row_key)
    parsed_families: Dict[str, Dict[str, str]] = {}
    for family in COLUMN_FAMILIES:
        col_map = row.cells.get(family, {})
        parsed_families[family] = {
            _decode_bytes(col_bytes): _decode_bytes(cell_list[0].value)
            for col_bytes, cell_list in col_map.items()
            if cell_list
        }

    ts_ms = _parse_timestamp_from_row(row_key_str, row.cells)
    time_display = (
        datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        .astimezone()
        .strftime("%H:%M:%S %d/%m/%Y")
        if ts_ms > 0
        else ""
    )

    return {
        "row_key": row_key_str,
        "row_key_parts": split_row_key_parts(row_key_str),
        "timestamp_ms": ts_ms,
        "time_display": time_display,
        "cf_event": parsed_families["cf_event"],
        "cf_product": parsed_families["cf_product"],
        "cf_device": parsed_families["cf_device"],
    }


def _build_server_filter(
    event_type: str = "",
    families: Optional[Tuple[str, ...]] = None,
):
    """Tạo Bigtable RowFilter phía server cho lọc event_type và giới hạn Column Family."""
    projection_filter = PassAllFilter(True)
    if families:
        cleaned = [f for f in families if f in COLUMN_FAMILIES]
        if cleaned and len(cleaned) < len(COLUMN_FAMILIES):
            pattern = "^(" + "|".join(re.escape(f) for f in cleaned) + ")$"
            projection_filter = FamilyNameRegexFilter(pattern.encode("utf-8"))

    if event_type and event_type in VALID_EVENT_TYPES:
        predicate = RowFilterChain(
            filters=[
                FamilyNameRegexFilter(b"^cf_event$"),
                ColumnQualifierRegexFilter(b"^event_type$"),
                ValueRegexFilter(f"^{re.escape(event_type)}$".encode("utf-8")),
            ]
        )
        return ConditionalRowFilter(base_filter=predicate, true_filter=projection_filter)

    return projection_filter if families else None


def query_user_events(
    user_id: str,
    limit: int = 10,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
    event_type: str = "",
    families: Optional[Tuple[str, ...]] = None,
) -> Dict[str, Any]:
    """Truy vấn hành vi của user bằng Prefix/Time-Range Scan kết hợp Server-side RowFilter."""
    table = get_table(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)
    reversed_uid = reverse_user_id(user_id)
    prefix = f"{reversed_uid}#{user_id}#"

    row_set = RowSet()
    if start_ms is not None or end_ms is not None:
        start_key = f"{prefix}{MAX_INT64 - int(end_ms):019d}" if end_ms is not None else prefix
        end_key = (
            f"{prefix}{MAX_INT64 - int(start_ms) + 1:019d}"
            if start_ms is not None
            else prefix[:-1] + chr(ord(prefix[-1]) + 1)
        )
        row_set.add_row_range_from_keys(start_key.encode("utf-8"), end_key.encode("utf-8"))
        scan_mode = f"Time-Range Scan [{start_key} -> {end_key})"
    else:
        row_set.add_row_range_with_prefix(prefix)
        scan_mode = f"Prefix Scan [{prefix}*]"

    row_filter = _build_server_filter(event_type=event_type, families=families)

    start_ns = time.perf_counter_ns()
    rows = list(table.read_rows(row_set=row_set, limit=limit, filter_=row_filter))
    latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

    filter_parts = []
    if event_type:
        filter_parts.append(f"ConditionalRowFilter(event_type={event_type})")
    if families:
        filter_parts.append(f"FamilyFilter({','.join(families)})")

    return {
        "user_id": user_id,
        "prefix": prefix,
        "scan_mode": scan_mode,
        "filter_applied": " và ".join(filter_parts) if filter_parts else "Không dùng Filter",
        "limit": limit,
        "latency_ms": round(latency_ms, 2),
        "events": [_decode_row(r) for r in rows],
    }


def get_weighted_recommendations(user_id: str, limit: int = 4) -> Dict[str, Any]:
    """Gợi ý sản phẩm, lấy danh sách vừa xem và cá nhân hóa Hero Banner từ 15 sự kiện gần nhất."""
    recent = query_user_events(user_id=user_id, limit=15)
    events = recent["events"]

    category_scores: Dict[str, float] = {}
    recently_viewed_ids: List[str] = []
    latest_product_id = ""

    for idx, event in enumerate(events):
        ev_type = event.get("cf_event", {}).get("event_type", "")
        cf_prod = event.get("cf_product", {})
        weight = EVENT_WEIGHTS.get(ev_type, 0)
        if weight <= 0:
            continue

        category = cf_prod.get("category", "").strip()
        keyword = cf_prod.get("search_keyword", "").strip()
        pid = cf_prod.get("product_id", "").strip()
        if not category and keyword:
            category = infer_category_from_keyword(keyword)

        if pid and pid in PRODUCTS_BY_ID and pid not in recently_viewed_ids:
            recently_viewed_ids.append(pid)

        if not category:
            continue

        recency_factor = max(0.4, 1.0 - idx * 0.05)
        category_scores[category] = round(
            category_scores.get(category, 0.0) + weight * recency_factor, 2
        )
        if pid and not latest_product_id:
            latest_product_id = pid

    if category_scores:
        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        top_category, _ = sorted_cats[0]

        same_cat_other = [
            p for p in SAMPLE_PRODUCTS
            if p["category"] == top_category and p["product_id"] != latest_product_id
        ]
        same_cat_latest = [
            p for p in SAMPLE_PRODUCTS
            if p["category"] == top_category and p["product_id"] == latest_product_id
        ]
        other_cats = sorted(
            [p for p in SAMPLE_PRODUCTS if p["category"] != top_category],
            key=lambda p: category_scores.get(p["category"], 0.0),
            reverse=True,
        )
        recommendations = (same_cat_other + same_cat_latest + other_cats)[:limit]
        score_summary = ", ".join(f"{cat}: {sc}đ" for cat, sc in sorted_cats[:3])
        reason = f"Chấm điểm trọng số {len(events)} hành vi gần nhất ({score_summary})"
    else:
        top_category = "Nổi bật"
        recommendations = SAMPLE_PRODUCTS[:limit]
        reason = "Chưa có lịch sử tương tác, hiển thị các sản phẩm nổi bật"

    recently_viewed = [PRODUCTS_BY_ID[pid] for pid in recently_viewed_ids[:4]]
    dynamic_banner = CATEGORY_BANNERS.get(top_category, CATEGORY_BANNERS["Nổi bật"])

    return {
        "user_id": user_id,
        "target_category": top_category,
        "category_scores": category_scores,
        "dynamic_banner": dynamic_banner,
        "recently_viewed": recently_viewed,
        "analyzed_events_count": len(events),
        "reason": reason,
        "query_latency_ms": recent["latency_ms"],
        "recommendations": recommendations,
    }


def get_overview_analytics(sample_limit: int = 400) -> Dict[str, Any]:
    """Tổng hợp phễu hành vi, phân bố thiết bị, khu vực, từ khóa và phân bổ tải trên 4 vùng Tablet."""
    table = get_table(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)
    per_range_limit = max(25, sample_limit // 4)
    tablet_ranges = (
        ("Tablet 1 (Prefix 00-24)", b"00", b"25"),
        ("Tablet 2 (Prefix 25-49)", b"25", b"50"),
        ("Tablet 3 (Prefix 50-74)", b"50", b"75"),
        ("Tablet 4 (Prefix 75-99)", b"75", b"~"),
    )

    rows = []
    tablet_buckets: Counter = Counter()
    start_ns = time.perf_counter_ns()
    for label, start_k, end_k in tablet_ranges:
        rs = RowSet()
        rs.add_row_range_from_keys(start_k, end_k)
        chunk = list(table.read_rows(row_set=rs, limit=per_range_limit))
        # Chỉ tính các khóa 3 thành phần chuẩn Anti-Hotspotting vào phân bổ 4 Tablet
        optimal_chunk = [
            r for r in chunk if len(_decode_bytes(r.row_key).split("#")) == 3
        ]
        tablet_buckets[label] = len(optimal_chunk)
        rows.extend(optimal_chunk)
    latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

    event_counts: Counter = Counter()
    device_counts: Counter = Counter()
    os_counts: Counter = Counter()
    region_counts: Counter = Counter()
    keyword_counts: Counter = Counter()
    category_counts: Counter = Counter()
    unique_users = set()

    for row in rows:
        decoded = _decode_row(row)
        rk = decoded["row_key"]
        parts = rk.split("#")
        if len(parts) == 3:
            unique_users.add(parts[1])

        ev_type = decoded["cf_event"].get("event_type", "")
        if ev_type:
            event_counts[ev_type] += 1

        dev = decoded["cf_device"].get("device_type", "")
        if dev:
            device_counts[dev] += 1

        os_name = decoded["cf_device"].get("os", "")
        if os_name:
            os_counts[os_name] += 1

        region = decoded["cf_device"].get("ip_region", "")
        if region:
            region_counts[region] += 1

        kw = decoded["cf_product"].get("search_keyword", "").strip()
        if kw and ev_type == "search_keyword":
            keyword_counts[kw] += 1

        cat = decoded["cf_product"].get("category", "").strip()
        if cat:
            category_counts[cat] += 1

    views = event_counts.get("view_product", 0)
    carts = event_counts.get("add_to_cart", 0)
    purchases = event_counts.get("purchase_success", 0)

    return {
        "sampled_rows": len(rows),
        "sample_limit": sample_limit,
        "unique_users": len(unique_users),
        "read_latency_ms": round(latency_ms, 2),
        "funnel": {
            "search_keyword": event_counts.get("search_keyword", 0),
            "view_product": views,
            "add_to_cart": carts,
            "purchase_success": purchases,
            "cart_rate_pct": round((carts / views) * 100.0, 1) if views > 0 else 0.0,
            "purchase_rate_pct": round((purchases / views) * 100.0, 1) if views > 0 else 0.0,
        },
        "tablet_distribution": dict(tablet_buckets),
        "devices": dict(device_counts.most_common()),
        "os": dict(os_counts.most_common()),
        "regions": dict(region_counts.most_common()),
        "categories": dict(category_counts.most_common()),
        "top_keywords": [
            {"keyword": kw, "count": cnt} for kw, cnt in keyword_counts.most_common(6)
        ],
    }


def benchmark_scan_comparison(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Đo trực tiếp thời gian Prefix Scan so với Full Table Scan có lọc theo user_id."""
    table = get_table(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)
    reversed_uid = reverse_user_id(user_id)
    prefix = f"{reversed_uid}#{user_id}#"

    row_set = RowSet()
    row_set.add_row_range_with_prefix(prefix)
    t0 = time.perf_counter_ns()
    prefix_rows = list(table.read_rows(row_set=row_set, limit=limit))
    prefix_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    t1 = time.perf_counter_ns()
    all_rows = list(table.read_rows())
    matched_full = [
        r for r in all_rows if _decode_bytes(r.row_key).startswith(prefix)
    ][:limit]
    full_scan_ms = (time.perf_counter_ns() - t1) / 1_000_000.0

    speedup = round(full_scan_ms / prefix_ms, 2) if prefix_ms > 0 else 0.0
    return {
        "user_id": user_id,
        "prefix": prefix,
        "prefix_scan_ms": round(prefix_ms, 2),
        "prefix_rows": len(prefix_rows),
        "full_scan_ms": round(full_scan_ms, 2),
        "total_scanned_rows": len(all_rows),
        "full_matched_rows": len(matched_full),
        "speedup": speedup,
    }


def detect_user_anomaly(
    user_id: str,
    window_seconds: int = 10,
    threshold: int = 8,
) -> Dict[str, Any]:
    """Phát hiện hành vi bất thường hoặc nghi vấn bot/spam bằng Time-Range Scan trong cửa sổ thời gian ngắn."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - window_seconds * 1000
    window_res = query_user_events(
        user_id=user_id,
        limit=30,
        start_ms=start_ms,
        end_ms=now_ms,
        families=("cf_event",),
    )
    events = window_res["events"]
    total_in_window = len(events)
    purchase_in_window = sum(
        1 for ev in events if ev.get("cf_event", {}).get("event_type") == "purchase_success"
    )

    if purchase_in_window >= 3:
        risk_level = "HIGH_RISK"
        label = "Cảnh báo đơn ảo"
        message = (
            f"Phát hiện {purchase_in_window} giao dịch thanh toán liên tiếp trong {window_seconds} giây "
            "(nghi vấn tạo đơn hàng ảo hoặc trục lợi khuyến mãi)."
        )
    elif total_in_window >= threshold:
        risk_level = "HIGH_RISK"
        label = "Nghi vấn Bot/Script"
        message = (
            f"Phát hiện {total_in_window} thao tác trong {window_seconds} giây (vượt ngưỡng {threshold}) "
            "- nghi vấn công cụ tự động gửi yêu cầu dồn dập."
        )
    elif total_in_window >= max(4, threshold - 3):
        risk_level = "WARNING"
        label = "Tần suất cao"
        message = f"Người dùng phát sinh {total_in_window} thao tác trong {window_seconds} giây gần nhất."
    else:
        risk_level = "NORMAL"
        label = "An toàn"
        message = f"Tần suất bình thường ({total_in_window} thao tác trong {window_seconds} giây gần nhất)."

    return {
        "user_id": user_id,
        "risk_level": risk_level,
        "label": label,
        "message": message,
        "events_in_window": total_in_window,
        "purchases_in_window": purchase_in_window,
        "window_seconds": window_seconds,
        "threshold": threshold,
        "latency_ms": window_res["latency_ms"],
    }
