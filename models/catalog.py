"""Dữ liệu danh mục sản phẩm mẫu, hồ sơ người dùng, banner cá nhân hóa và trọng số hành vi."""

from typing import Any, Dict, List

MAX_INT64 = 9223372036854775807

VALID_EVENT_TYPES = (
    "view_product",
    "search_keyword",
    "add_to_cart",
    "purchase_success",
)

EVENT_WEIGHTS: Dict[str, int] = {
    "purchase_success": 5,
    "add_to_cart": 3,
    "view_product": 2,
    "search_keyword": 1,
}

SAMPLE_USERS = ("usr_1001", "usr_2049", "usr_3088")

USER_PROFILES: Dict[str, Dict[str, str]] = {
    "usr_1001": {
        "user_id": "usr_1001",
        "name": "Minh Anh",
        "segment": "Tín đồ Flagship Mobile",
        "avatar": "MA",
        "default_region": "VN-HN",
    },
    "usr_2049": {
        "user_id": "usr_2049",
        "name": "Hoàng Nam",
        "segment": "Kỹ sư Phần mềm và Dữ liệu",
        "avatar": "HN",
        "default_region": "VN-HCM",
    },
    "usr_3088": {
        "user_id": "usr_3088",
        "name": "Thanh Trúc",
        "segment": "Người yêu Âm thanh và Gear",
        "avatar": "TT",
        "default_region": "VN-DN",
    },
}

CATEGORIES = ("Tất cả", "Laptop", "Điện thoại", "Phụ kiện", "Âm thanh")

QUICK_KEYWORDS = ("MacBook", "iPhone", "Galaxy", "Sony", "Keychron", "Marshall")

CATEGORY_BANNERS: Dict[str, Dict[str, str]] = {
    "Laptop": {
        "tag": "Cá nhân hóa từ Bigtable Clickstream • Danh mục Laptop",
        "title": "Không gian làm việc hiệu năng cao cho Lập trình và AI",
        "subtitle": "Hệ thống phát hiện bạn đang quan tâm dòng Laptop cao cấp qua chuỗi hành vi thời gian thực. Ưu đãi trả góp 0% và tặng kèm Hub USB-C.",
        "theme": "theme-laptop",
        "cta_category": "Laptop",
    },
    "Điện thoại": {
        "tag": "Cá nhân hóa từ Bigtable Clickstream • Danh mục Điện thoại",
        "title": "Thế hệ Smartphone AI và Camera Pro mới nhất",
        "subtitle": "Gợi ý tức thì dựa trên lượt xem và tìm kiếm Điện thoại gần đây của bạn. Thu cũ đổi mới trợ giá đến 4.000.000 VNĐ.",
        "theme": "theme-phone",
        "cta_category": "Điện thoại",
    },
    "Phụ kiện": {
        "tag": "Cá nhân hóa từ Bigtable Clickstream • Danh mục Phụ kiện",
        "title": "Nâng cấp góc làm việc với Bàn phím cơ và Chuột công thái học",
        "subtitle": "Được đề xuất tự động từ lịch sử tương tác Phụ kiện trên Bigtable. Giảm thêm 15% khi mua kèm Laptop hoặc PC.",
        "theme": "theme-accessory",
        "cta_category": "Phụ kiện",
    },
    "Âm thanh": {
        "tag": "Cá nhân hóa từ Bigtable Clickstream • Danh mục Âm thanh",
        "title": "Trải nghiệm âm thanh Hi-Res và Chống ồn chủ động đỉnh cao",
        "subtitle": "Cá nhân hóa theo thời gian thực từ sở thích Âm thanh của bạn. Tặng gói nghe nhạc Lossless 6 tháng.",
        "theme": "theme-audio",
        "cta_category": "Âm thanh",
    },
    "Nổi bật": {
        "tag": "TechZone Flagship Store • Powered by Google Cloud Bigtable",
        "title": "Sàn thương mại điện tử cá nhân hóa theo thời gian thực",
        "subtitle": "Mọi thao tác tìm kiếm, xem sản phẩm, thêm giỏ hàng và thanh toán đều được ghi vào Bigtable với độ trễ mili-giây để điều chỉnh giao diện ngay lập tức.",
        "theme": "theme-default",
        "cta_category": "Tất cả",
    },
}

SAMPLE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "product_id": "SP001",
        "product_name": "MacBook Pro 14 M3 Pro",
        "category": "Laptop",
        "price": 49990000,
        "old_price": 54990000,
        "discount_pct": 9,
        "rating": 4.9,
        "reviews_count": 142,
        "badge": "Bán chạy",
        "icon_type": "laptop",
        "accent": "#2563eb",
        "specs": "Chip M3 Pro 11-core, RAM 18GB, SSD 512GB, Liquid Retina XDR",
        "description": "Hiệu năng vượt trội cho lập trình, thiết kế đồ họa và xử lý dữ liệu lớn với thời lượng pin lên đến 18 giờ.",
    },
    {
        "product_id": "SP002",
        "product_name": "Dell XPS 13 Plus 9320",
        "category": "Laptop",
        "price": 36490000,
        "old_price": 40990000,
        "discount_pct": 11,
        "rating": 4.8,
        "reviews_count": 89,
        "badge": "Cao cấp",
        "icon_type": "laptop",
        "accent": "#0284c7",
        "specs": "Intel Core i7 Gen 13, RAM 16GB, SSD 1TB, Màn hình OLED 3.5K",
        "description": "Thiết kế siêu mỏng nhẹ nguyên khối, dãy phím cảm ứng lực và bàn di chuột kính liền mạch hiện đại.",
    },
    {
        "product_id": "SP003",
        "product_name": "iPhone 16 Pro Max 256GB",
        "category": "Điện thoại",
        "price": 33990000,
        "old_price": 36990000,
        "discount_pct": 8,
        "rating": 4.9,
        "reviews_count": 318,
        "badge": "Mới nhất",
        "icon_type": "phone",
        "accent": "#7c3aed",
        "specs": "Chip A18 Pro, Titan Sa Mạc, Camera 48MP Fusion, Pin 33 giờ",
        "description": "Flagship màn hình 6.9 inch Super Retina XDR viền siêu mỏng cùng nút Điều khiển Camera chuyên nghiệp.",
    },
    {
        "product_id": "SP004",
        "product_name": "Samsung Galaxy S25 Ultra",
        "category": "Điện thoại",
        "price": 31490000,
        "old_price": 34990000,
        "discount_pct": 10,
        "rating": 4.8,
        "reviews_count": 215,
        "badge": "AI Phone",
        "icon_type": "phone",
        "accent": "#4f46e5",
        "specs": "Snapdragon 8 Elite, RAM 12GB, S Pen tích hợp, Camera 200MP",
        "description": "Trải nghiệm quyền năng Galaxy AI toàn diện cùng khung viền Titan bền bỉ và ống kính zoom quang học sắc nét.",
    },
    {
        "product_id": "SP005",
        "product_name": "Bàn phím cơ Keychron K2 Pro",
        "category": "Phụ kiện",
        "price": 2390000,
        "old_price": 2790000,
        "discount_pct": 14,
        "rating": 4.9,
        "reviews_count": 176,
        "badge": "QMK/VIA",
        "icon_type": "keyboard",
        "accent": "#059669",
        "specs": "Layout 75%, Hot-swap, Kết nối Bluetooth 5.1 và USB-C",
        "description": "Gõ êm ái với lớp đệm tiêu âm silicone, switch Keychron K Pro lắp sẵn và keycap PBT double-shot bền màu.",
    },
    {
        "product_id": "SP006",
        "product_name": "Chuột Logitech MX Master 3S",
        "category": "Phụ kiện",
        "price": 2490000,
        "old_price": 2990000,
        "discount_pct": 17,
        "rating": 4.9,
        "reviews_count": 264,
        "badge": "Công thái học",
        "icon_type": "mouse",
        "accent": "#0d9488",
        "specs": "Cảm biến 8000 DPI trên kính, Cuộn MagSpeed siêu êm, USB-C",
        "description": "Tối ưu cho lập trình viên và nhà thiết kế nhờ nút bấm Quiet Click giảm 90% tiếng ồn và cuộn từ tính.",
    },
    {
        "product_id": "SP007",
        "product_name": "Tai nghe Sony WH-1000XM5",
        "category": "Âm thanh",
        "price": 7490000,
        "old_price": 8490000,
        "discount_pct": 12,
        "rating": 4.9,
        "reviews_count": 198,
        "badge": "Chống ồn ANC",
        "icon_type": "headphone",
        "accent": "#ea580c",
        "specs": "8 micro khử ồn chủ động, Hi-Res Audio LDAC, Pin 30 giờ",
        "description": "Đỉnh cao chống ồn chủ động thế hệ mới với hai bộ xử lý độc lập cùng chất âm chi tiết, giàu nhạc tính.",
    },
    {
        "product_id": "SP008",
        "product_name": "Loa Marshall Acton III",
        "category": "Âm thanh",
        "price": 6890000,
        "old_price": 7990000,
        "discount_pct": 14,
        "rating": 4.8,
        "reviews_count": 134,
        "badge": "Vintage",
        "icon_type": "speaker",
        "accent": "#d97706",
        "specs": "Công suất 60W Class D, Bluetooth 5.2, Âm trường rộng",
        "description": "Thiết kế cổ điển mang tính biểu tượng kết hợp công nghệ Dynamic Loudness giữ trọn âm sắc ở mọi mức âm lượng.",
    },
]

PRODUCTS_BY_ID: Dict[str, Dict[str, Any]] = {
    item["product_id"]: item for item in SAMPLE_PRODUCTS
}


def infer_category_from_keyword(keyword: str) -> str:
    """Suy luận danh mục sản phẩm từ từ khóa tìm kiếm."""
    normalized = (keyword or "").strip().lower()
    if not normalized:
        return ""

    for product in SAMPLE_PRODUCTS:
        if normalized in product["category"].lower():
            return product["category"]
        if normalized in product["product_name"].lower():
            return product["category"]
        if normalized in product["specs"].lower():
            return product["category"]
    return ""
