# Hệ thống quản lý dữ liệu Clickstream và hành vi người dùng trên Google Cloud Bigtable

Ứng dụng minh họa sàn thương mại điện tử **TechZone** xây dựng theo kiến trúc **MVC (Flask Blueprints + Bigtable Repositories)**, kết hợp ghi nhận, lọc dữ liệu phía server (`Time-Range Scan`, `RowFilter`), thống kê bộ đếm nguyên tử (`ReadModifyWrite`) và gợi ý sản phẩm có trọng số theo thời gian thực trên **Google Cloud Bigtable**.

## Cấu trúc dự án MVC

- `config.py`: Khai báo `PROJECT_ID`, `INSTANCE_ID`, `TABLE_ID` (`ecommerce_clickstream`), `METRICS_TABLE_ID` (`product_metrics`) và tự động chuyển đổi giữa Bigtable Emulator (`BIGTABLE_EMULATOR_HOST`) với Google Cloud thật (ADC).
- `requirements.txt`: Danh sách thư viện Python cần thiết (`Flask`, `google-cloud-bigtable`).
- `models/`: Tầng Model và truy xuất dữ liệu Bigtable:
  - `catalog.py`: Danh mục 8 sản phẩm mẫu, 3 hồ sơ người dùng, banner cá nhân hóa và trọng số hành vi (`purchase_success: 5`, `add_to_cart: 3`, `view_product: 2`, `search_keyword: 1`).
  - `bigtable_client.py`: Quản lý kết nối đa luồng và kiểm tra/khởi tạo 2 bảng.
  - `clickstream_model.py`: Row Key `[reversed_user_id]#[user_id]#[reverse_timestamp]`, ghi đơn và ghi lô (`mutate_rows`), Time-Range Scan, Server-side `ConditionalRowFilter` và `FamilyNameRegexFilter`, gợi ý có trọng số, phân bổ 4 vùng Tablet và so sánh Prefix Scan với Full Table Scan.
  - `metrics_model.py`: Bảng `product_metrics` với Row Key `[product_id]#[YYYYMMDD]` và họ cột `cf_stats` dùng `AppendRow.increment_cell_value` (`ReadModifyWrite`).
- `controllers/`: Tầng Controller (Flask Blueprints) gồm `shop_controller.py`, `analytics_controller.py` và `simulator_controller.py`.
- `templates/` và `static/`: Tầng View (`base.html`, `shop.html`, `analytics.html`) cùng CSS/JS tách riêng.
- `app.py`: Điểm khởi chạy Flask Application Factory.
- `bigtable_service.py`: Lớp facade giữ tương thích các hàm cũ và ủy quyền về `models/`.
- `load_test.py`: Kiểm thử tải đa luồng hỗ trợ `--mode hotspot`, `--mode optimal`, `--mode batch` và `--mode read-compare`.

## Yêu cầu môi trường và Cài đặt lần đầu (Prerequisites)

Nếu chạy trên máy mới chưa cài môi trường, thực hiện một lần duy nhất các bước sau:

1. Cài đặt **Python 3.10+** và **Google Cloud SDK (`gcloud`)**.
2. Cài thêm thành phần `cbt` và `bigtable` emulator cho Google Cloud SDK:

```powershell
gcloud components install cbt bigtable
```

3. Tạo môi trường ảo Python và cài thư viện từ `requirements.txt`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

*(Nếu PowerShell báo lỗi chặn chạy script `Activate.ps1`, chạy lệnh `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` rồi kích hoạt lại).*

## Phần A: Quy trình vận hành mỗi lần mở máy (Chế độ Cục bộ với Emulator)

Vì Bigtable Emulator lưu dữ liệu tạm thời trên RAM, dữ liệu sẽ được làm mới sau mỗi lần tắt máy hoặc đóng Terminal chạy Emulator. Mỗi lần mở thư mục dự án (`d:\baitap\NoSQL\NoSQL`) trên VS Code hoặc Antigravity, thực hiện lần lượt 6 bước sau:

### Bước 1: Khởi động máy chủ Bigtable Emulator (Terminal 1)

Mở Terminal bằng tổ hợp phím `Ctrl + ~` và chạy:

```powershell
gcloud beta emulators bigtable start --host-port=127.0.0.1:8086
```

Khi thấy dòng `[bigtable] Cloud Bigtable emulator running on 127.0.0.1:8086`, giữ nguyên tab Terminal này chạy ngầm và không tắt.

### Bước 2: Mở Terminal 2 và trỏ kết nối về Emulator

Bấm biểu tượng dấu `+` ở góc phải khung Terminal để mở tab PowerShell mới, kích hoạt môi trường ảo và đặt biến môi trường:

```powershell
.\venv\Scripts\Activate.ps1
$env:BIGTABLE_EMULATOR_HOST="127.0.0.1:8086"
```

### Bước 3: Khởi tạo 2 bảng (`ecommerce_clickstream` và `product_metrics`)

Chạy cụm lệnh `cbt` dưới đây tại Terminal 2 để tạo đủ cấu trúc bảng cùng chính sách dọn rác 90 ngày:

```powershell
cbt -project demo-project -instance clickstream-instance createtable ecommerce_clickstream
cbt -project demo-project -instance clickstream-instance createfamily ecommerce_clickstream cf_event
cbt -project demo-project -instance clickstream-instance createfamily ecommerce_clickstream cf_product
cbt -project demo-project -instance clickstream-instance createfamily ecommerce_clickstream cf_device
cbt -project demo-project -instance clickstream-instance setgcpolicy ecommerce_clickstream cf_event maxage=90d
cbt -project demo-project -instance clickstream-instance setgcpolicy ecommerce_clickstream cf_product maxage=90d
cbt -project demo-project -instance clickstream-instance setgcpolicy ecommerce_clickstream cf_device maxage=90d

cbt -project demo-project -instance clickstream-instance createtable product_metrics
cbt -project demo-project -instance clickstream-instance createfamily product_metrics cf_stats
cbt -project demo-project -instance clickstream-instance setgcpolicy product_metrics cf_stats maxage=90d
```

Xác nhận danh sách bảng:

```powershell
cbt -project demo-project -instance clickstream-instance ls
```

### Bước 4: Khởi chạy ứng dụng Web MVC (`app.py`)

```powershell
python app.py
```

Truy cập hai màn hình chính trên trình duyệt:
- `http://127.0.0.1:5000/`: Sàn thương mại điện tử TechZone cá nhân hóa theo thời gian thực.
- `http://127.0.0.1:5000/analytics`: Dashboard phân tích phễu chuyển đổi, `product_metrics`, Live Traffic Simulator và đối chiếu Bigtable Studio SQL.

### Bước 5: Checklist kiểm thử nhanh ứng dụng Web MVC

1. **Trên trang `/` (Cửa hàng Cá nhân hóa)**:
   - Bấm các nút **Kịch bản 1 chạm** (`Săn Laptop Pro`, `Đổi sang Âm thanh`, `Mua nhanh iPhone 16`): kiểm tra thanh **Live Telemetry Pipeline** sáng đèn tuần tự, **Hero Banner** tự đổi màu chủ đề, hộp **Giải phẫu Row Key** hiển thị 3 phần màu và dòng mới trượt vào bảng Clickstream.
   - Bấm nút **Mô phỏng Bot/Gian lận**: kiểm tra hộp **Phát hiện gian lận và bất thường (Fraud Detection • Time-Range 10s)** chuyển sang cảnh báo đỏ `Nghi vấn Bot/Script` khi vượt ngưỡng 8 thao tác trong 10 giây.
   - Chuyển đổi giữa 3 tài khoản (`Minh Anh - usr_1001`, `Hoàng Nam - usr_2049`, `Thanh Trúc - usr_3088`): kiểm tra Prefix Scan và hồ sơ điểm trọng số cập nhật theo từng user.
   - Thử bộ lọc **5 phút gần nhất (Time-Range Scan)** kết hợp **Chỉ `view_product`** (`ConditionalRowFilter`) và **Chỉ `cf_event` và `cf_product`** (`FamilyNameRegexFilter`): kiểm tra cột `cf_device` được ẩn ngay phía server.
   - Bấm **Mua ngay** hoặc **Thanh toán đơn hàng**: kiểm tra Modal Biên nhận hiển thị chính xác Row Key `purchase_success` vừa lưu.
2. **Trên trang `/analytics` (Quản trị và Bigtable Console)**:
   - Bấm **Bắt đầu giả lập** (Live Traffic Simulator) trong vài giây rồi bấm **Dừng giả lập**: quan sát số sự kiện, Phễu chuyển đổi, Phân bổ 4 vùng Tablet và bảng `product_metrics` tự động cập nhật.
   - Bấm **Chạy so sánh Scan**: kiểm tra tỷ lệ tăng tốc giữa Prefix Scan và Full Table Scan.
   - Bấm **Sao chép SQL** ở mục đối chiếu Bigtable Studio để dán trực tiếp lên Google Cloud Console.

### Bước 6: Chạy các kịch bản kiểm thử chịu tải (`load_test.py`)

```powershell
python load_test.py --mode hotspot --count 2000
python load_test.py --mode optimal --count 2000
python load_test.py --mode batch --count 2000 --batch-size 250
python load_test.py --mode read-compare --user-id usr_2049
```

### Bước 7: Dừng hệ thống khi nghỉ

Nhấn `Ctrl + C` ở cả Terminal chạy `app.py` và Terminal chạy Bigtable Emulator.

## Phần B: Triển khai trên Google Cloud Skills Boost để thu thập số liệu và ảnh báo cáo

### 5.1. Khởi tạo phòng Lab miễn phí

1. Truy cập `https://www.cloudskillsboost.google/` và đăng nhập bằng tài khoản Gmail.
2. Tìm kiếm từ khóa `Cloud Bigtable` và chọn một bài lab thực hành cơ bản (ví dụ: *Cloud Bigtable: Qwik Start*).
3. Bấm **Start Lab** và lưu lại 3 thông số ở khung bên trái: `Username`, `Password` và `GCP Project ID`.

### 5.2. Tạo Instance và 2 Bảng trên Bigtable Console thật (Chụp Hình 2.1 và Hình 2.2)

1. Mở Google Cloud Console bằng đúng tài khoản học viên của bài lab và kích hoạt Bigtable API nếu được yêu cầu.
2. Tạo cụm máy chủ (**Hình 2.1**):
   - Instance ID: `clickstream-instance`, Storage type: `SSD`, Cluster ID: `clickstream-cluster`, Region: `us-central1` (hoặc Region mặc định bài lab cho phép).
   - Node scaling mode: **Autoscaling** (`Min nodes = 1`, `Max nodes = 2`, `CPU utilization target = 70%`).
   - Chụp ảnh cấu hình này làm **Hình 2.1**, sau đó bấm **Create**.
3. Tạo bảng chính `ecommerce_clickstream` (**Hình 2.2**):
   - Vào **Tables** -> **Create Table** -> nhập Table ID `ecommerce_clickstream`.
   - Tạo 3 họ cột `cf_event`, `cf_product`, `cf_device` kèm GC Policy **Maximum age: 90 days**.
   - Chụp ảnh danh sách 3 họ cột kèm GC Policy làm **Hình 2.2**, sau đó bấm **Create**.
4. Tạo bảng thống kê thứ 2 `product_metrics`:
   - Bấm **Create Table** -> nhập Table ID `product_metrics` -> thêm 1 họ cột `cf_stats` (Maximum age: `90 days`) -> bấm **Create**.

### 5.3. Chuyển kết nối từ máy cá nhân lên Google Cloud thật

```powershell
Remove-Item Env:BIGTABLE_EMULATOR_HOST -ErrorAction SilentlyContinue
gcloud auth login
gcloud auth application-default login
gcloud config set project <LAB_PROJECT_ID>
```

Mở tệp `config.py`, đổi biến `PROJECT_ID` thành `<LAB_PROJECT_ID>` và lưu lại. Kiểm tra kết nối:

```powershell
cbt -project <LAB_PROJECT_ID> -instance clickstream-instance ls
```

### 5.4. Đẩy dữ liệu tải lớn lên Cloud và chụp bộ ảnh thực nghiệm (Hình 2.3, Hình 2.4 và Chương 4)

1. Bắn tải để ghi nhận thông số Chương 4 và tạo dữ liệu cho Key Visualizer:

```powershell
python load_test.py --mode hotspot --count 25000
python load_test.py --mode optimal --count 25000
python load_test.py --mode batch --count 25000 --batch-size 500
python load_test.py --mode read-compare --user-id usr_2049
```

2. Chạy `python app.py`, mở `http://127.0.0.1:5000` và `http://127.0.0.1:5000/analytics`, bật **Live Traffic Simulator** trong lúc mở tab **Monitoring** trên Bigtable Console để quan sát biểu đồ Throughput và CPU tăng theo thời gian thực.
3. Trên Bigtable Console, chụp đủ các ảnh:
   - **Hình 2.3 (Bigtable Studio)**: Dùng các câu truy vấn GoogleSQL có sẵn ngay trên trang `/analytics` để hiển thị dữ liệu đã giải mã UTF-8.
   - **Monitoring**: Chụp biểu đồ Throughput, CPU utilization và Latency của `clickstream-instance`.
   - **Hình 2.4 và Chương 4 (Key Visualizer)**: Đợi 10 đến 15 phút sau khi bắn tải để xem bản đồ nhiệt phân bố tải theo dải Row Key.
4. Bấm **End Lab** trên Google Cloud Skills Boost sau khi lưu đủ ảnh.

## Xử lý sự cố thường gặp (Troubleshooting)

- **Lỗi `bind: Only one usage of each socket address` khi chạy Emulator**: Cổng `127.0.0.1:8086` đang có một tiến trình `cbtemulator.exe` chạy sẵn từ trước. Có thể dùng trực tiếp tiến trình đang chạy hoặc tắt cửa sổ Terminal cũ rồi khởi động lại.
- **Ứng dụng vẫn kết nối Emulator dù đã đăng nhập Google Cloud**: Kiểm tra bằng `echo $env:BIGTABLE_EMULATOR_HOST`. Nếu vẫn còn giá trị, chạy `Remove-Item Env:BIGTABLE_EMULATOR_HOST` rồi chạy lại `python app.py`.
- **Trang `/analytics` báo bảng `product_metrics` chưa tồn tại trên Cloud**: Tạo thêm bảng `product_metrics` với họ cột `cf_stats` theo Bước 5.2 (ứng dụng trang Shop `/` vẫn hoạt động bình thường trong lúc chờ tạo bảng thứ 2).
- **PowerShell báo lỗi không cho chạy `.\venv\Scripts\Activate.ps1`**: Chạy một lần lệnh `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` trong PowerShell rồi kích hoạt lại môi trường ảo.
