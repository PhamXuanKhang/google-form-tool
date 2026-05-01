<div align="center">

<img src="app/static/images/banner.png" alt="Google Form Automation Tool Banner" width="100%">

<h1>Google Form Automation Tool</h1>

<p><strong>Tự động hoá submit Google Form hàng loạt — không cần API, không cần code.</strong></p>

[![Release](https://img.shields.io/github/v/release/PhamXuanKhang/google-form-tool?include_prereleases&style=for-the-badge&color=blue&label=Download)](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)
[![Platform](https://img.shields.io/badge/Windows-10%2F11%2064--bit-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Beta-orange?style=for-the-badge)](https://github.com/PhamXuanKhang/google-form-tool/issues)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

</div>

---

## ⚡ Tải về & Chạy ngay (Windows)

> Không cần cài Python. Không cần config. Double-click là chạy.

**1.** [**⬇ Tải GoogleFormTool-v1.0.0-beta.1-windows.zip**](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)

**2.** Giải nén vào thư mục bất kỳ

**3.** Cài **[Google Chrome](https://www.google.com/chrome/)** nếu chưa có *(bắt buộc)*

**4.** Double-click **`GoogleFormTool.exe`**
   → Trình duyệt tự động mở tại `http://127.0.0.1:5000`

> 💡 **Lần đầu chạy:** App tự tải ChromeDriver phù hợp với Chrome của bạn (~30–60 giây, cần internet). Các lần sau không cần tải lại.

> ⚠️ Antivirus có thể cảnh báo file exe — đây là **false positive** thông thường với PyInstaller. Bỏ qua an toàn.

---

## ✨ Tính năng

| | Tính năng | Mô tả |
|---|-----------|-------|
| 🔍 | **Auto Extract** | Tự động đọc cấu trúc câu hỏi từ bất kỳ Google Form nào |
| 🎯 | **12 Question Types** | Text, Multiple Choice, Checkbox, Scale, Grid, Date, Time... |
| ⚙️ | **Custom Probabilities** | Tuỳ chỉnh xác suất chọn từng đáp án |
| 🚀 | **Bulk Submit** | Multithreading — submit hàng trăm lần với delay ngẫu nhiên |
| 📊 | **Live Monitoring** | CPU, network, thread metrics real-time |
| 🤖 | **AI Responses** | Tích hợp Gemini AI để tạo câu trả lời tự nhiên |
| 🌐 | **i18n** | Giao diện Tiếng Anh / Tiếng Việt |
| 📋 | **History** | Lưu lịch sử submission, export CSV |

---

## 🗺️ Workflow

```
① Paste URL          ② Configure          ③ Settings          ④ Monitor
   Google Form URL  →  Set probabilities  →  Threads & delay  →  Live progress
   → Auto extract      per answer option     Min/max delay        Success/fail
```

---

## 🐛 Known Issues (Beta)

- File upload answer method đang thử nghiệm, có thể không ổn định
- Một số loại câu hỏi đặc biệt (file upload, rating) không hỗ trợ prefill mode
- Docker path chưa được kiểm tra đầy đủ trên tất cả cấu hình

---

## 🛠️ Dành cho Developer (Chạy từ Source)

<details>
<summary>Click để mở hướng dẫn</summary>

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) *(khuyến nghị)* hoặc pip
- Google Chrome

### Setup

```bash
git clone https://github.com/PhamXuanKhang/google-form-tool.git
cd google-form-tool

# Cài dependencies (uv)
uv sync

# Hoặc pip
pip install -r requirements.txt

# Chạy
python wsgi.py
```

Mở `http://localhost:5000`

### Chrome paths (tuỳ chọn)

Để dùng Chrome hoặc ChromeDriver cụ thể, copy `.env.example` thành `.env` và cấu hình:

```env
CHROME_BINARY_PATH=C:\Path\To\chrome.exe
CHROME_DRIVER_PATH=C:\Path\To\chromedriver.exe
```

Nếu để trống, app sẽ tự phát hiện Chrome hệ thống và tự tải ChromeDriver.

### Build exe

```bat
build_exe.bat
```

Output: `dist\GoogleFormTool\GoogleFormTool.exe` (~114 MB uncompressed, ~51 MB zipped)

### Chạy tests

```bash
pytest tests/ -v
```

### Docker (nâng cao)

```bash
docker compose up --build
```

</details>

---

## 📬 Feedback & Liên hệ

Đây là bản **Beta** — mong nhận phản hồi và báo lỗi từ bạn!

<div align="center">

[![Report Bug](https://img.shields.io/badge/🐛_Report_Bug-GitHub_Issues-red?style=for-the-badge)](https://github.com/PhamXuanKhang/google-form-tool/issues/new)
[![Email](https://img.shields.io/badge/📧_Email-phamxuankhang2004@gmail.com-EA4335?style=for-the-badge)](mailto:phamxuankhang2004@gmail.com)
[![LinkedIn](https://img.shields.io/badge/💼_LinkedIn-KhangPham-0A66C2?style=for-the-badge)](https://www.linkedin.com/in/xuan-khang-pham-715208279/)
[![GitHub](https://img.shields.io/badge/⭐_GitHub-PhamXuanKhang-181717?style=for-the-badge)](https://github.com/PhamXuanKhang)

</div>

---

<div align="center">
  <sub>Made with ❤️ by <a href="https://github.com/PhamXuanKhang">KhangPham</a> · v1.0.0-beta.1</sub>
</div>
