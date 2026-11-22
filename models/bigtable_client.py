"""Quản lý kết nối Bigtable Client và khởi tạo bảng an toàn đa luồng."""

import threading
from typing import Dict, Tuple

from google.cloud.bigtable.column_family import MaxVersionsGCRule

from config import (
    COLUMN_FAMILIES,
    INSTANCE_ID,
    METRICS_COLUMN_FAMILIES,
    METRICS_TABLE_ID,
    TABLE_ID,
    get_bigtable_client,
    is_emulator_mode,
)

_client_lock = threading.Lock()
_cached_client = None
_cached_instance = None
_cached_tables: Dict[str, object] = {}
_verified_tables: Dict[str, bool] = {}


def _get_instance():
    global _cached_client, _cached_instance
    if _cached_client is None:
        _cached_client = get_bigtable_client(admin=True)
        _cached_instance = _cached_client.instance(INSTANCE_ID)
    return _cached_instance


def ensure_table_exists(
    table_id: str = TABLE_ID,
    column_families: Tuple[str, ...] = COLUMN_FAMILIES,
    auto_create_emulator: bool = True,
) -> bool:
    """Đảm bảo bảng tồn tại trên Emulator hoặc kiểm tra trạng thái trên Google Cloud thật."""
    with _client_lock:
        if _verified_tables.get(table_id):
            return True

        instance = _get_instance()
        table = instance.table(table_id)
        if not table.exists():
            if is_emulator_mode() and auto_create_emulator:
                cf_rules = {cf: MaxVersionsGCRule(5) for cf in column_families}
                table.create(column_families=cf_rules)
            else:
                if table_id == TABLE_ID:
                    raise RuntimeError(
                        f"Bảng '{table_id}' chưa tồn tại trong instance '{INSTANCE_ID}'. "
                        "Hãy tạo bảng cùng 3 Column Families (cf_event, cf_product, cf_device) trước khi chạy trên Cloud."
                    )
                return False

        _cached_tables[table_id] = table
        _verified_tables[table_id] = True
        return True


def get_table(
    table_id: str = TABLE_ID,
    column_families: Tuple[str, ...] = COLUMN_FAMILIES,
    auto_create_emulator: bool = True,
):
    """Lấy đối tượng Table dùng chung an toàn đa luồng."""
    if not ensure_table_exists(
        table_id=table_id,
        column_families=column_families,
        auto_create_emulator=auto_create_emulator,
    ):
        return None
    return _cached_tables[table_id]


def ensure_all_tables() -> Dict[str, bool]:
    """Khởi tạo hoặc kiểm tra cả hai bảng ecommerce_clickstream và product_metrics."""
    return {
        TABLE_ID: ensure_table_exists(TABLE_ID, COLUMN_FAMILIES),
        METRICS_TABLE_ID: ensure_table_exists(METRICS_TABLE_ID, METRICS_COLUMN_FAMILIES),
    }
