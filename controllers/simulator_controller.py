"""Controller quản lý Live Traffic Simulator chạy nền để minh họa tải thời gian thực."""

import random
import threading
import time
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from models.catalog import SAMPLE_PRODUCTS, VALID_EVENT_TYPES
from models.clickstream_model import log_clickstream_event

simulator_bp = Blueprint("simulator", __name__)

_SIM_REGIONS = ("VN-HCM", "VN-HN", "VN-DN")
_SIM_DEVICES = (("Desktop", "Windows"), ("Desktop", "macOS"), ("Mobile", "Android"), ("Mobile", "iOS"))
_SIM_KEYWORDS = ("MacBook", "iPhone", "Galaxy", "Sony", "Keychron", "Logitech", "Marshall")


class TrafficSimulator:
    """Bộ sinh luồng sự kiện Clickstream chạy nền an toàn luồng."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._rate_per_sec = 5
        self._generated_count = 0
        self._error_count = 0
        self._last_row_key = ""
        self._last_event_type = ""
        self._last_error = ""

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "rate_per_sec": self._rate_per_sec,
                "generated_count": self._generated_count,
                "error_count": self._error_count,
                "last_row_key": self._last_row_key,
                "last_event_type": self._last_event_type,
                "last_error": self._last_error,
            }

    def start(self, rate_per_sec: int = 5) -> Dict[str, Any]:
        with self._lock:
            self._rate_per_sec = min(max(int(rate_per_sec), 1), 25)
            if self._running:
                return self.status()
            self._stop_event.clear()
            self._running = True
            self._last_error = ""
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self._stop_event.set()
            self._running = False
        return self.status()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                rate = self._rate_per_sec
            interval = 1.0 / max(1, rate)
            t0 = time.perf_counter()

            user_id = f"usr_{random.randint(4001, 4050)}"
            product = random.choice(SAMPLE_PRODUCTS)
            event_type = random.choices(
                VALID_EVENT_TYPES, weights=(45, 25, 20, 10), k=1
            )[0]
            device_type, os_name = random.choice(_SIM_DEVICES)
            ip_region = random.choice(_SIM_REGIONS)
            keyword = random.choice(_SIM_KEYWORDS) if event_type == "search_keyword" else ""

            try:
                logged = log_clickstream_event(
                    user_id=user_id,
                    event_type=event_type,
                    session_id=f"sim_{user_id}",
                    page_url=f"/search?q={keyword}" if keyword else f"/products/{product['product_id']}",
                    product_id="" if event_type == "search_keyword" else product["product_id"],
                    product_name="" if event_type == "search_keyword" else product["product_name"],
                    category=product["category"],
                    price=0 if event_type == "search_keyword" else product["price"],
                    search_keyword=keyword,
                    device_type=device_type,
                    os=os_name,
                    ip_region=ip_region,
                )
                with self._lock:
                    self._generated_count += 1
                    self._last_row_key = logged["row_key"]
                    self._last_event_type = event_type
            except Exception as exc:
                with self._lock:
                    self._error_count += 1
                    self._last_error = str(exc)

            elapsed = time.perf_counter() - t0
            sleep_for = max(0.01, interval - elapsed)
            self._stop_event.wait(sleep_for)


simulator = TrafficSimulator()


@simulator_bp.route("/api/simulator/status", methods=["GET"])
def api_simulator_status():
    return jsonify({"status": "ok", "simulator": simulator.status()})


@simulator_bp.route("/api/simulator/start", methods=["POST"])
def api_simulator_start():
    payload = request.get_json(silent=True) or {}
    rate = payload.get("rate_per_sec", 5)
    return jsonify({"status": "ok", "simulator": simulator.start(rate_per_sec=rate)})


@simulator_bp.route("/api/simulator/stop", methods=["POST"])
def api_simulator_stop():
    return jsonify({"status": "ok", "simulator": simulator.stop()})
