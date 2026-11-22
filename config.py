"""Cấu hình kết nối Google Cloud Bigtable và danh sách bảng của hệ thống."""

import os
from typing import Dict, Optional

from google.cloud import bigtable

PROJECT_ID = "demo-project"
INSTANCE_ID = "clickstream-instance"
TABLE_ID = "ecommerce_clickstream"
METRICS_TABLE_ID = "product_metrics"

COLUMN_FAMILIES = ("cf_event", "cf_product", "cf_device")
METRICS_COLUMN_FAMILIES = ("cf_stats",)

# Tự động đọc biến môi trường BIGTABLE_EMULATOR_HOST; nếu không có sẽ dùng ADC tới Google Cloud thật
BIGTABLE_EMULATOR_HOST: Optional[str] = os.environ.get("BIGTABLE_EMULATOR_HOST") or None


def is_emulator_mode() -> bool:
    """Kiểm tra hệ thống đang chạy với Bigtable Emulator hay Google Cloud thật."""
    return bool(os.environ.get("BIGTABLE_EMULATOR_HOST"))


def get_connection_info() -> Dict[str, str]:
    """Trả về thông tin kết nối hiện tại để hiển thị trên giao diện và CLI."""
    emulator_host = os.environ.get("BIGTABLE_EMULATOR_HOST") or ""
    if emulator_host:
        mode = "Bigtable Emulator"
        endpoint = emulator_host
    else:
        mode = "Google Cloud Bigtable (ADC)"
        endpoint = "bigtable.googleapis.com"

    return {
        "mode": mode,
        "endpoint": endpoint,
        "project_id": PROJECT_ID,
        "instance_id": INSTANCE_ID,
        "table_id": TABLE_ID,
        "metrics_table_id": METRICS_TABLE_ID,
    }


def get_bigtable_client(admin: bool = True) -> bigtable.Client:
    """Khởi tạo Bigtable Client qua Emulator hoặc Application Default Credentials."""
    return bigtable.Client(project=PROJECT_ID, admin=admin)
