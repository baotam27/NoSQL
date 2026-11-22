# Hướng dẫn Tải, Cài đặt và Chạy lần đầu từ đầu (Windows)

Tài liệu này hướng dẫn từng bước từ con số 0 cho máy tính Windows chưa từng cài đặt môi trường, giúp bạn tải mã nguồn, thiết lập Python, Google Cloud Bigtable Emulator và chạy kiểm thử thành công toàn bộ ứng dụng web MVC **TechZone E-Commerce và Bigtable Clickstream**.

## Bước 1: Tải và cài đặt phần mềm bắt buộc

### 1.1. Cài đặt Python 3.10 trở lên
1. Tải bộ cài Python cho Windows tại `https://www.python.org/downloads/`.
2. Chạy tệp cài đặt và **bắt buộc đánh dấu vào ô `Add python.exe to PATH`** ở màn hình đầu tiên, sau đó chọn **Install Now**.
3. Mở PowerShell mới và kiểm tra:

```powershell
python --version
pip --version
```

Xác nhận thành công khi màn hình in ra phiên bản (ví dụ `Python 3.10.11` hoặc `Python 3.11+`).

### 1.2. Cài đặt Google Cloud CLI (`gcloud`), `cbt` và Bigtable Emulator
1. Tải bộ cài Google Cloud CLI cho Windows (`GoogleCloudSDKInstaller.exe`) tại `https://cloud.google.com/sdk/docs/install#windows`.
2. Cài đặt theo các bước mặc định. Ở màn hình cuối cùng, có thể bỏ chọn khởi chạy `gcloud init` nếu bạn chỉ chạy thử trên Emulator cục bộ trước.
3. **Đóng hoàn toàn PowerShell/VS Code cũ và mở lại cửa sổ mới** để Windows nạp biến môi trường `PATH`, sau đó kiểm tra:

```powershell
gcloud --version
```

4. Cài đặt đủ 3 thành phần `beta`, `cbt` và `bigtable` (bắt buộc để chạy Bigtable Emulator và công cụ dòng lệnh `cbt`):

```powershell
gcloud components install beta cbt bigtable
```

*(Khi hệ thống hỏi `Do you want to continue (Y/n)?`, gõ `Y` rồi nhấn Enter).*

5. Kiểm tra thành phần vừa cài:

```powershell
cbt -version
gcloud beta emulators bigtable --help
```

## Bước 2: Tải mã nguồn dự án về máy

Chọn một trong hai cách sau:

- **Cách 1 (Từ tệp nén ZIP)**: Giải nén mã nguồn vào thư mục có đường dẫn ngắn, **không chứa dấu tiếng Việt và không chứa khoảng trắng** (ví dụ `D:\baitap\NoSQL\NoSQL` hoặc `C:\Projects\bigtable-clickstream`).
- **Cách 2 (Từ Git)**:

```powershell
git clone <DUONG_DAN_REPO>
cd <TEN_THU_MUC_DU_AN>
```

Mở thư mục dự án trong VS Code (hoặc Antigravity) và kiểm tra thấy đầy đủ các tệp chính: `app.py`, `config.py`, `load_test.py`, `requirements.txt`, `models/`, `controllers/`, `templates/`, `static/`.

## Bước 3: Tạo môi trường ảo Python và cài thư viện

Mở Terminal PowerShell bên trong thư mục dự án (`Ctrl + ~` trên VS Code) và chạy lần lượt các lệnh sau:

### 3.1. Cấp quyền chạy script PowerShell (chỉ cần làm 1 lần trên Windows)
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
*(Nếu được hỏi xác nhận, gõ `Y` và nhấn Enter).*

### 3.2. Tạo và kích hoạt môi trường ảo (`venv`)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Xác nhận thành công khi đầu dòng lệnh xuất hiện tiền tố `(venv)`.

### 3.3. Cài đặt các thư viện cần thiết từ `requirements.txt`
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Kiểm tra nhanh thư viện đã cài đúng:

```powershell
python -c "import flask; from google.cloud import bigtable; print('Moi truong Python da san sang')"
```

## Bước 4: Khởi chạy ứng dụng lần đầu với Bigtable Emulator

### 4.1. Khởi động Bigtable Emulator (Terminal 1)
Tại tab PowerShell thứ nhất, chạy lệnh:

```powershell
gcloud beta emulators bigtable start --host-port=127.0.0.1:8086
```

Khi thấy dòng `[bigtable] Cloud Bigtable emulator running on 127.0.0.1:8086`, **giữ nguyên tab Terminal 1 chạy ngầm và không đóng**.

### 4.2. Khởi tạo 2 bảng dữ liệu Bigtable (Terminal 2)
Bấm dấu `+` để mở tab PowerShell thứ hai tại thư mục dự án, kích hoạt `venv` và trỏ kết nối về Emulator:

```powershell
.\venv\Scripts\Activate.ps1
$env:BIGTABLE_EMULATOR_HOST="127.0.0.1:8086"
```

Chạy cụm lệnh `cbt` để tạo bảng chính `ecommerce_clickstream` (3 Họ cột) và bảng thống kê `product_metrics` (1 Họ cột) kèm chính sách dọn rác 90 ngày:

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

Xác nhận 2 bảng đã được tạo:

```powershell
cbt -project demo-project -instance clickstream-instance ls
```

### 4.3. Chạy máy chủ Web Flask (`app.py`)
Tại Terminal 2, chạy:

```powershell
python app.py
```

Mở trình duyệt và kiểm tra 2 màn hình chính:
1. **`http://127.0.0.1:5000/` (Cửa hàng Cá nhân hóa)**:
   - Bấm thử các nút **Kịch bản 1 chạm** (`Săn Laptop Pro`, `Đổi sang Âm thanh`, `Mua nhanh iPhone 16`) để xem thanh Pipeline sáng đèn, Hero Banner tự đổi chủ đề và hộp Giải phẫu Row Key 3 màu.
   - Bấm nút **Mô phỏng Bot/Gian lận** để kiểm tra khối **Phát hiện gian lận và bất thường (Fraud Detection)** bật cảnh báo đỏ trong cửa sổ 10 giây.
   - Thử bộ lọc **Time-Range Scan** (`5 phút gần nhất`) kết hợp **ConditionalRowFilter** (`Chỉ view_product`) và **FamilyNameRegexFilter** (`Chỉ cf_event và cf_product`).
2. **`http://127.0.0.1:5000/analytics` (Quản trị và Bigtable Console)**:
   - Bấm **Bắt đầu giả lập** (Live Traffic Simulator) vài giây rồi bấm **Dừng giả lập** để quan sát Phễu chuyển đổi, Phân bổ 4 vùng Tablet và bảng `product_metrics`.
   - Bấm **Chạy so sánh Scan** để đo trực tiếp độ trễ Prefix Scan so với Full Table Scan.

## Bước 5: Chạy kiểm thử chịu tải lần đầu (`load_test.py`)

Nhấn `Ctrl + C` ở Terminal 2 để tạm dừng web (hoặc mở Terminal 3 nhớ chạy lại `.\venv\Scripts\Activate.ps1` và `$env:BIGTABLE_EMULATOR_HOST="127.0.0.1:8086"`), sau đó chạy lần lượt 4 kịch bản đo hiệu năng:

```powershell
python load_test.py --mode hotspot --count 2000
python load_test.py --mode optimal --count 2000
python load_test.py --mode batch --count 2000 --batch-size 250
python load_test.py --mode read-compare --user-id usr_2049
```

## Bước 6: Triển khai lên Google Cloud thật (Chụp ảnh báo cáo)

Khi ứng dụng đã chạy mượt ở chế độ cục bộ và bạn muốn đưa lên Google Cloud Skills Boost để chụp ảnh **Bigtable Studio**, **Monitoring** và **Key Visualizer**, thực hiện theo **Phần B** trong tệp `README.md`.

## Bước 7: Xử lý lỗi hay gặp khi cài đặt lần đầu

- **`'python' is not recognized`**: Khi cài Python chưa đánh dấu `Add python.exe to PATH`. Hãy chạy lại bộ cài Python, chọn **Modify** và bật tùy chọn thêm vào `PATH`, sau đó mở lại PowerShell.
- **`'gcloud' is not recognized` hoặc lỗi thiếu `beta`/`cbt`**: Đóng và mở lại cửa sổ PowerShell sau khi cài Google Cloud CLI, sau đó chạy lại `gcloud components install beta cbt bigtable`.
- **Lỗi `ModuleNotFoundError: No module named 'flask'`**: Chưa kích hoạt môi trường ảo `(venv)`. Chạy `.\venv\Scripts\Activate.ps1` trước khi chạy `python app.py`.
- **Lỗi `bind: Only one usage of each socket address` ở cổng `8086`**: Bigtable Emulator đã được bật sẵn ở một cửa sổ khác; có thể dùng luôn tiến trình đó mà không cần mở thêm.
- **Lỗi kết nối timeout khi chạy `python app.py`**: Quên đặt `$env:BIGTABLE_EMULATOR_HOST="127.0.0.1:8086"` trong tab Terminal hiện tại hoặc Terminal 1 chạy Emulator đã bị tắt.
