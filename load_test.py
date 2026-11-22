"""Công cụ kiểm thử chịu tải đa luồng so sánh Hotspot, Anti-Hotspotting, Batch Write và Prefix Scan trên Bigtable."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import random
import statistics
import time
from typing import Any, Dict, List

from config import COLUMN_FAMILIES, TABLE_ID, get_connection_info
from models.bigtable_client import ensure_table_exists
from models.catalog import SAMPLE_PRODUCTS, VALID_EVENT_TYPES
from models.clickstream_model import (
    benchmark_scan_comparison,
    build_hotspot_row_key,
    build_row_key,
    log_clickstream_batch,
    log_clickstream_event,
)

REGIONS = ("VN-HCM", "VN-HN", "VN-DN")
DEVICES = (("Desktop", "Windows"), ("Desktop", "macOS"), ("Mobile", "Android"), ("Mobile", "iOS"))
SEARCH_KEYWORDS = ("MacBook", "iPhone", "Galaxy", "Sony", "Keychron", "Logitech", "Marshall")


def compute_percentile(sorted_values: List[float], percentile: float) -> float:
    """Tính phân vị theo nội suy tuyến tính trên danh sách đã sắp xếp."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower_idx = math.floor(rank)
    upper_idx = math.ceil(rank)
    if lower_idx == upper_idx:
        return sorted_values[int(rank)]
    weight = rank - lower_idx
    return sorted_values[lower_idx] * (1.0 - weight) + sorted_values[upper_idx] * weight


def build_simulated_event(index: int, base_ts_ms: int, mode: str, num_users: int) -> Dict[str, Any]:
    """Tạo dữ liệu sự kiện mô phỏng với Row Key theo kịch bản kiểm thử."""
    user_id = f"usr_{1000 + (index % num_users)}"
    ts_ms = base_ts_ms + index
    product = random.choice(SAMPLE_PRODUCTS)
    event_type = random.choice(VALID_EVENT_TYPES)
    device_type, os_name = random.choice(DEVICES)
    ip_region = random.choice(REGIONS)

    if mode == "hotspot":
        row_key = build_hotspot_row_key(user_id=user_id, timestamp_ms=ts_ms)
    else:
        row_key, _ = build_row_key(user_id=user_id, timestamp_ms=ts_ms)

    search_keyword = random.choice(SEARCH_KEYWORDS) if event_type == "search_keyword" else ""
    page_url = (
        f"/search?q={search_keyword}"
        if event_type == "search_keyword"
        else f"/products/{product['product_id']}"
    )

    return {
        "user_id": user_id,
        "event_type": event_type,
        "session_id": f"load_sess_{index % num_users}",
        "page_url": page_url,
        "product_id": "" if event_type == "search_keyword" else product["product_id"],
        "product_name": "" if event_type == "search_keyword" else product["product_name"],
        "category": product["category"],
        "price": 0 if event_type == "search_keyword" else product["price"],
        "search_keyword": search_keyword,
        "device_type": device_type,
        "os": os_name,
        "ip_region": ip_region,
        "timestamp_ms": ts_ms,
        "row_key_override": row_key,
    }


def _print_table(title: str, rows: List[tuple]) -> None:
    col1_w = max(len(r[0]) for r in rows) + 2
    col2_w = max(len(r[1]) for r in rows) + 2
    border = f"+{'-' * col1_w}+{'-' * col2_w}+"

    print()
    print(title)
    print(border)
    print(f"| {'Chỉ số':<{col1_w - 2}} | {'Giá trị đo được':<{col2_w - 2}} |")
    print(border)
    for label, value in rows:
        print(f"| {label:<{col1_w - 2}} | {value:<{col2_w - 2}} |")
    print(border)
    print()


def print_write_report(
    mode: str,
    count: int,
    workers: int,
    succeeded: int,
    failed: int,
    total_time_sec: float,
    latencies_ms: List[float],
    sample_row_key: str,
    latency_unit_label: str = "Độ trễ mỗi request",
) -> None:
    """In bảng tổng hợp kết quả kiểm thử ghi để đưa vào báo cáo."""
    sorted_lat = sorted(latencies_ms)
    throughput = succeeded / total_time_sec if total_time_sec > 0 else 0.0
    avg_ms = statistics.mean(sorted_lat) if sorted_lat else 0.0
    p50_ms = compute_percentile(sorted_lat, 50)
    p95_ms = compute_percentile(sorted_lat, 95)
    p99_ms = compute_percentile(sorted_lat, 99)
    min_ms = sorted_lat[0] if sorted_lat else 0.0
    max_ms = sorted_lat[-1] if sorted_lat else 0.0

    scenario_map = {
        "hotspot": "Kịch bản 1 - Lỗi Hotspotting ({timestamp}#{user_id})",
        "optimal": "Kịch bản 2 - Tối ưu Anti-Hotspotting ({reversed_user_id}#{user_id}#{reverse_timestamp})",
        "batch": "Kịch bản 3 - Ghi lô tối ưu (mutate_rows + Anti-Hotspotting)",
    }
    conn = get_connection_info()

    rows = [
        ("Kịch bản kiểm thử", scenario_map.get(mode, mode)),
        ("Môi trường kết nối", f"{conn['mode']} ({conn['endpoint']})"),
        ("Bảng Bigtable", f"{conn['instance_id']}/{conn['table_id']}"),
        ("Số luồng (workers)", str(workers)),
        ("Row Key mẫu", sample_row_key),
        ("Tổng số sự kiện yêu cầu", str(count)),
        ("Số sự kiện ghi thành công", str(succeeded)),
        ("Số sự kiện thất bại", str(failed)),
        ("Tổng thời gian chạy (giây)", f"{total_time_sec:.3f} s"),
        ("Thông lượng ghi (events/sec)", f"{throughput:.2f} events/sec"),
        (f"{latency_unit_label} trung bình (Avg)", f"{avg_ms:.2f} ms"),
        (f"{latency_unit_label} P50 (Median)", f"{p50_ms:.2f} ms"),
        (f"{latency_unit_label} P95", f"{p95_ms:.2f} ms"),
        (f"{latency_unit_label} P99", f"{p99_ms:.2f} ms"),
        (f"{latency_unit_label} Min / Max", f"{min_ms:.2f} ms / {max_ms:.2f} ms"),
    ]
    _print_table("BẢNG THỐNG KÊ KIỂM THỬ CHỊU TẢI BIGTABLE CLICKSTREAM", rows)


def run_single_write(event_payload: Dict[str, Any]) -> float:
    """Thực thi ghi đơn lẻ một sự kiện vào ecommerce_clickstream."""
    result = log_clickstream_event(update_metrics=False, **event_payload)
    return float(result["write_latency_ms"])


def run_read_compare(user_id: str, iterations: int = 5) -> None:
    """So sánh độ trễ trung bình giữa Prefix Scan và Full Table Scan."""
    prefix_latencies: List[float] = []
    full_latencies: List[float] = []
    last_result: Dict[str, Any] = {}

    for _ in range(iterations):
        last_result = benchmark_scan_comparison(user_id=user_id, limit=10)
        prefix_latencies.append(last_result["prefix_scan_ms"])
        full_latencies.append(last_result["full_scan_ms"])

    avg_prefix = statistics.mean(prefix_latencies)
    avg_full = statistics.mean(full_latencies)
    speedup = avg_full / avg_prefix if avg_prefix > 0 else 0.0
    conn = get_connection_info()

    rows = [
        ("Kịch bản kiểm thử", "Kịch bản 4 - So sánh Đọc (Prefix Scan so với Full Table Scan)"),
        ("Môi trường kết nối", f"{conn['mode']} ({conn['endpoint']})"),
        ("User ID truy vấn", f"{user_id} (Prefix: {last_result.get('prefix', '')})"),
        ("Số lần lặp đo (iterations)", str(iterations)),
        ("Tổng số dòng đang có trong bảng", str(last_result.get("total_scanned_rows", 0))),
        ("Độ trễ trung bình Prefix Scan", f"{avg_prefix:.2f} ms"),
        ("Độ trễ trung bình Full Table Scan", f"{avg_full:.2f} ms"),
        ("Tỷ lệ tăng tốc (Speedup)", f"{speedup:.2f}x nhanh hơn"),
    ]
    _print_table("BẢNG SO SÁNH HIỆU NĂNG TRUY VẤN ĐỌC BIGTABLE", rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kiểm thử chịu tải ghi và so sánh tốc độ đọc trên Google Cloud Bigtable."
    )
    parser.add_argument(
        "--mode",
        choices=("hotspot", "optimal", "batch", "read-compare"),
        default="optimal",
        help="Chọn kịch bản: 'hotspot', 'optimal', 'batch', hoặc 'read-compare'.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=2000,
        help="Tổng số sự kiện clickstream cần mô phỏng (mặc định: 2000).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=32,
        help="Số luồng song song trong ThreadPoolExecutor (mặc định: 32).",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=200,
        help="Số lượng User ID giả lập (mặc định: 200).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=250,
        help="Số sự kiện mỗi lô khi chạy --mode batch (mặc định: 250).",
    )
    parser.add_argument(
        "--user-id",
        default="usr_2049",
        help="User ID dùng trong chế độ --mode read-compare (mặc định: usr_2049).",
    )
    args = parser.parse_args()

    ensure_table_exists(table_id=TABLE_ID, column_families=COLUMN_FAMILIES)

    if args.mode == "read-compare":
        print(f"Đang chạy so sánh Prefix Scan và Full Table Scan cho {args.user_id}...")
        run_read_compare(user_id=args.user_id, iterations=5)
        return

    base_ts_ms = int(time.time() * 1000)
    events = [
        build_simulated_event(i, base_ts_ms, args.mode, max(1, args.users))
        for i in range(args.count)
    ]
    sample_row_key = events[0]["row_key_override"] if events else ""

    if args.mode == "batch":
        print(f"Đang chạy ghi lô (--mode batch) {args.count} sự kiện, kích thước lô {args.batch_size}...")
        batch_result = log_clickstream_batch(events, chunk_size=max(1, args.batch_size))
        print_write_report(
            mode="batch",
            count=args.count,
            workers=1,
            succeeded=batch_result["succeeded"],
            failed=batch_result["failed"],
            total_time_sec=batch_result["total_time_sec"],
            latencies_ms=batch_result["batch_latencies_ms"],
            sample_row_key=sample_row_key,
            latency_unit_label="Độ trễ mỗi lô",
        )
        return

    latencies_ms: List[float] = []
    failed = 0
    first_error = ""

    print(
        f"Đang chạy kiểm thử chế độ '{args.mode}' với {args.count} sự kiện "
        f"trên {args.workers} luồng..."
    )

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_single_write, ev) for ev in events]
        for future in as_completed(futures):
            try:
                latencies_ms.append(future.result())
            except Exception as exc:
                failed += 1
                if not first_error:
                    first_error = str(exc)

    total_time_sec = time.perf_counter() - start_time
    if first_error:
        print(f"Cảnh báo lỗi trong quá trình ghi: {first_error}")

    print_write_report(
        mode=args.mode,
        count=args.count,
        workers=args.workers,
        succeeded=len(latencies_ms),
        failed=failed,
        total_time_sec=total_time_sec,
        latencies_ms=latencies_ms,
        sample_row_key=sample_row_key,
    )


if __name__ == "__main__":
    main()
