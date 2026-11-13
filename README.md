# 🏫 HCMUNRE Campus Map & Green Space Management System
> **Hệ thống Bản đồ Số WebGIS & Quản lý Hạ tầng - Không gian Xanh Khuôn viên HCMUNRE**

[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![GeoDjango](https://img.shields.io/badge/GeoDjango-GIS-006600?style=for-the-badge&logo=django&logoColor=white)](https://docs.djangoproject.com/en/stable/ref/contrib/gis/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgis.net/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

---

## 📌 Giới thiệu dự án

**CampusMap_Project** là hệ thống WebGIS hiện đại phục vụ việc số hóa, tra cứu thông tin bản đồ và quản lý không gian xanh, hạ tầng kỹ thuật tại Trường Đại học Tài nguyên và Môi trường TP.HCM (HCMUNRE). Dự án kết hợp công nghệ cơ sở dữ liệu không gian địa lý (**PostGIS**) và giao diện bản đồ động tương tác (**Leaflet.js**) giúp sinh viên, cán bộ giảng viên và ban quản lý dễ dàng tra cứu, quản lý và phản hồi.

---

## ✨ Tính năng nổi bật

### 🗺️ 1. Bản đồ số WebGIS Tương tác (Interactive Campus Map)
- **Hiển thị trực quan:** Bản đồ số tích hợp lớp nền bản đồ OpenStreetMap với ranh giới khuôn viên các cơ sở (Campus), các khối tòa nhà (Building), từng tầng (Floor), phòng học / văn phòng / lab / wc (Room).
- **Quản lý mảng xanh (Green Space):** Thống kê và hiển thị diện tích thảm cỏ, vườn hoa cảnh quan (`GreenArea`) và từng vị trí gốc cây xanh (`Tree`) kèm trạng thái sinh trưởng (phát triển tốt / cần chăm sóc).
- **Bộ lọc & Tìm kiếm thông minh:** Tìm kiếm nhanh phòng học, vị trí theo từ khóa; chuyển đổi linh hoạt giữa các cơ sở và bật/tắt các lớp dữ liệu (Layer Toggles).
- **Bản vẽ mặt bằng:** Tích hợp liên kết bản vẽ mặt bằng và hình ảnh chụp thực tế cho từng công trình.

### 🔐 2. Hệ thống Xác thực & Phân quyền (Auth & RBAC)
- **Đăng ký tài khoản kèm mã OTP qua Email:** Tự động gửi OTP qua Gmail SMTP để xác thực kích hoạt tài khoản.
- **Quên / Đặt lại mật khẩu an toàn:** Xác thực qua OTP tạm thời có thời hạn (Hashed OTP).
- **Phân quyền người dùng chi tiết (RBAC):** Bảng vai trò tùy biến phân quyền rành mạch cho từng hành động CRUD trên từng loại tài nguyên (Cơ sở, Tòa nhà, Phòng, Bãi xe, Mảng xanh, Cây xanh, Quản lý tài khoản).

### 🛠️ 3. Cổng Quản trị Nội dung & Hạ tầng (Admin Portal)
- Dashboard theo dõi số lượng và biểu đồ thống kê cơ sở vật chất, tỷ lệ phủ xanh khuôn viên.
- Giao diện thêm, sửa, xóa (CRUD) các thực thể không gian địa lý hỗ trợ tọa độ và hình đa giác (WGS84 / SRID 4326).
- **CMS Trang chủ:** Tùy biến linh hoạt các khối nội dung Banner (Hero), Phần giới thiệu (Intro), Thẻ tiện ích (Feature Groups) và Chân trang (Footer) ngay trên trang quản trị.

### 💬 4. Hộp thư Góp ý & Báo lỗi (Feedback & Interaction)
- Sinh viên và cán bộ có thể gửi phản ánh lỗi cơ sở vật chất, đề xuất cải tiến kèm hình ảnh trực tiếp.
- Trao đổi hai chiều theo luồng (Thread message) giữa người dùng và ban quản lý.
- Hỗ trợ tương tác thả biểu tượng cảm xúc (Emoji reactions: 👍, ❤️, 😂, 😮, 😢, 🙏).

---

## 🏗️ Cấu trúc thư mục dự án

```text
CampusMap_Project/
├── core/                       # Cấu hình chính của Django project
│   ├── settings.py             # Cấu hình PostGIS, Auth, Media, Static, Email SMTP
│   ├── urls.py                 # Định tuyến toàn hệ thống
│   └── wsgi.py / asgi.py
├── map_app/                    # Ứng dụng nghiệp vụ chính
│   ├── models.py               # Mô hình GIS (Campus, Building, Room, GreenArea, Tree,...)
│   ├── views.py                # Public views & WebGIS APIs
│   ├── portal_views.py         # Views quản trị Portal, RBAC & Auth OTP
│   ├── forms.py                # Biểu mẫu nhập liệu & xác thực
│   ├── permissions.py          # Kiểm tra quyền truy cập theo vai trò
│   ├── templates/              # Giao diện HTML (Leaflet map, Admin portal, Auth)
│   └── static/                 # CSS, JS, Icons, Images
├── media/                      # File ảnh người dùng tải lên (campus, building, trees,...)
├── .env.email.example          # File mẫu cấu hình biến môi trường gửi Mail
├── manage.py                   # Lệnh điều khiển Django CLI
└── db.sqlite3                  # Database phụ / dự phòng
```

---

## 🚀 Hướng dẫn cài đặt & Chạy trên máy cá nhân (Local)

### 1. Yêu cầu môi trường
- **Python**: Phiên bản 3.10 - 3.12
- **PostgreSQL**: Phiên bản 14 trở lên kèm extension **PostGIS**
- **GDAL / GEOS / PROJ**: Đã cài đặt thư viện hỗ trợ xử lý GIS (phù hợp với môi trường OS của bạn)

### 2. Sao chép dự án & Tạo môi trường ảo
```bash
# Clone repository
git clone https://github.com/<tai-khoan-cua-ban>/CampusMap_Project.git
cd CampusMap_Project

# Tạo và kích hoạt môi trường ảo (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Cấu hình biến môi trường (`.env`)
Tạo file `.env` tại thư mục gốc của dự án và khai báo các thông số kết nối:

```env
# Django
SECRET_KEY=your-django-secret-key-here
DEBUG=True

# Cấu hình PostgreSQL & PostGIS
DB_NAME=campusmap_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432

# Cấu hình Gmail SMTP (Gửi OTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### 4. Cài đặt thư viện & Khởi tạo Database
```bash
# Cài đặt các gói phụ thuộc
pip install django psycopg2-binary pillow python-dotenv

# Áp dụng migration vào cơ sở dữ liệu PostGIS
python manage.py makemigrations
python manage.py migrate

# Tạo tài khoản quản trị tối cao (Superuser)
python manage.py createsuperuser
```

### 5. Khởi chạy máy chủ phát triển
```bash
python manage.py runserver
```

Truy cập ứng dụng tại trình duyệt:
- 🌐 **Trang chủ / Bản đồ:** `http://127.0.0.1:8000/` hoặc `http://127.0.0.1:8000/map/`
- ⚙️ **Trang Quản trị Portal:** `http://127.0.0.1:8000/quan-tri/`
- 🔑 **Đăng nhập / Đăng ký:** `http://127.0.0.1:8000/login/`

---

## 👨‍💻 Tác giả & Đóng góp
- **Đơn vị phát triển:** Dự án số hóa phục vụ khuôn viên HCMUNRE.
- Mọi ý kiến đóng góp hoặc báo lỗi vui lòng gửi qua mục **Góp ý** trên giao diện ứng dụng hoặc tạo **Issue** trên GitHub.
