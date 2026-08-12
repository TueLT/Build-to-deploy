# Orbit — AI Personal Assistant UI

Giao diện MVP cho trợ lý cá nhân AI tích hợp trong nền tảng chat. Dự án chỉ bao gồm frontend và sử dụng dữ liệu mẫu, không có backend, API hoặc chức năng xác thực thật.

## Công nghệ sử dụng

- React 18
- Vite
- React Router
- Bootstrap 5 và Bootstrap Icons
- React Hook Form
- FullCalendar
- Framer Motion

## Yêu cầu môi trường

Trước khi bắt đầu, máy cần có:

- [Git](https://git-scm.com/downloads)
- [Node.js](https://nodejs.org/) phiên bản 18 trở lên
- npm (được cài kèm Node.js)

## Hai frontend độc lập

Frontend hiện được tách thành hai ứng dụng riêng, cùng gọi backend ở cổng `8000`:

| Ứng dụng | Thư mục | Cổng | Phạm vi |
| --- | --- | --- | --- |
| User | `Frontend/user` | `5173` | Chat, tasks, calendar, reminders, memory và profile |
| Admin | `Frontend/admin` | `5174` | Đăng nhập admin và quản trị users, conversations, user data |

Mở hai terminal từ đúng thư mục frontend:

```powershell
cd Frontend\user
npm.cmd install
npm.cmd run dev
```

```powershell
cd Frontend\admin
npm.cmd install
npm.cmd run dev
```

Sau đó mở `http://localhost:5173` cho User hoặc `http://localhost:5174` cho Admin. Admin không chứa route hay layout của User; tài khoản thường cũng không thể đăng nhập vào Admin.

Kiểm tra bằng Terminal, PowerShell hoặc Command Prompt:

```bash
git --version
node --version
npm --version
```

## Tải và chạy dự án từ Git

### 1. Clone repository

Thay `<repository-url>` bằng đường dẫn Git của dự án:

```bash
git clone <repository-url>
```

Ví dụ:

```bash
git clone https://github.com/your-account/orbit-ai-assistant.git
```

### 2. Di chuyển vào thư mục dự án

```bash
cd orbit-ai-assistant
```

Nếu repository dùng tên thư mục khác, hãy thay `orbit-ai-assistant` bằng tên thư mục vừa clone.

### 3. Cài đặt và chạy frontend

Không chạy `npm` ở thư mục `Frontend` nữa. Hãy chạy từng app trong thư mục riêng:

```powershell
# User app — http://localhost:5173
cd Frontend\user
npm.cmd install
npm.cmd run dev
```

```powershell
# Admin app — http://localhost:5174
cd Frontend\admin
npm.cmd install
npm.cmd run dev
```

User và Admin là hai app độc lập. Admin có màn hình login và bootstrap admin riêng; không nhúng các trang User.

## Các trang User có sẵn

| Trang | Đường dẫn |
| --- | --- |
| Đăng nhập | `/login` |
| Đăng ký | `/register` |
| Trợ lý AI cá nhân | `/assistant` |
| Chat | `/chat` |
| Công việc | `/tasks` |
| Lịch | `/calendar` |
| Nhắc nhở | `/reminders` |
| Bộ nhớ AI | `/memory` |
| Hồ sơ và cài đặt | `/profile` |

Đường dẫn `/` sẽ tự chuyển đến trang `/assistant`.

## Các trang Admin có sẵn

Đặt `ADMIN_BOOTSTRAP_KEY` trong backend `.env`, mở `http://localhost:5174/register` để tạo admin đầu tiên,
sau đó đăng nhập tại `http://localhost:5174/login`. Đăng ký User không tự cấp quyền admin.

| Trang | Đường dẫn |
| --- | --- |
| Đăng nhập Admin | `/login` |
| Tạo admin đầu tiên | `/register` |
| Dashboard | `/` |
| Users | `/users` |
| Conversations | `/conversations` |
| User data | `/user-data` |

## Build phiên bản production

Tạo bản build User hoặc Admin từ thư mục tương ứng:

```powershell
cd Frontend\user
npm.cmd run build

cd ..\admin
npm.cmd run build
```

Kết quả sẽ nằm trong thư mục `dist/`.

Chạy thử bản production cho app cần kiểm tra:

```powershell
# User
cd Frontend\user
npm.cmd run preview

# Admin — chạy ở terminal khác
cd Frontend\admin
npm.cmd run preview
```

Vite sẽ hiển thị địa chỉ preview trong Terminal.

## Xử lý lỗi thường gặp

### PowerShell báo `npm.ps1 cannot be loaded`

Nếu Windows chặn script PowerShell, dùng file thực thi `npm.cmd`:

```powershell
npm.cmd install
npm.cmd run dev
```

Hoặc mở Command Prompt thay vì PowerShell rồi chạy lại các lệnh `npm` thông thường.

### Cổng 5173 hoặc 5174 đang được sử dụng

Đóng process đang chiếm cổng hoặc chạy app bằng cổng khác:

```powershell
# Ví dụ chạy User ở cổng 5183
cd Frontend\user
npm.cmd run dev -- --port 5183
```

### Giao diện hoặc dependency hoạt động không đúng sau khi cập nhật code

Xóa thư mục `node_modules` và file `package-lock.json`, sau đó cài lại:

PowerShell:

```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm.cmd install
```

macOS/Linux:

```bash
rm -rf node_modules package-lock.json
npm install
```

## Cấu trúc chính

```text
src/
├── components/    # Component dùng lại cho layout và từng tính năng
├── data/          # Dữ liệu mẫu
├── pages/         # Các trang của ứng dụng
├── router/        # Cấu hình React Router
├── main.jsx       # Điểm khởi tạo ứng dụng
└── styles.css     # Design system và responsive styles
```

## Lưu ý

- Dự án hiện chỉ là giao diện frontend.
- Dữ liệu chat, công việc, lịch và nhắc nhở đều là dữ liệu mẫu.
- Các nút thao tác không kết nối backend hoặc API thật.
- Login và Register chỉ minh họa giao diện và validation phía client.
