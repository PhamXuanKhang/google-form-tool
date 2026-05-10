<div align="center">

<img src="app/static/images/banner.png" alt="Google Form Automation Tool Banner" width="100%">

<h1>Google Form Automation Tool</h1>

<p><strong>Tự động hoá submit Google Form hàng loạt bằng desktop app chạy local.</strong></p>

[![Landing](https://img.shields.io/badge/Landing-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://<your-vercel-app>.vercel.app)
[![Release](https://img.shields.io/github/v/release/PhamXuanKhang/google-form-tool?include_prereleases&style=for-the-badge&color=blue&label=Download)](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)
[![Platform](https://img.shields.io/badge/Windows-10%2F11%2064--bit-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Beta-orange?style=for-the-badge)](https://github.com/PhamXuanKhang/google-form-tool/issues)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

</div>

---

## Tải về & chạy ngay trên Windows

> Landing page sẽ được deploy tại `https://<your-vercel-app>.vercel.app`. Trong lúc chờ URL thật, tải bản mới nhất tại GitHub Releases.

**1.** Mở [GitHub Releases latest](https://github.com/PhamXuanKhang/google-form-tool/releases/latest)

**2.** Tải Windows installer `.exe` mới nhất. File `.msi` là tuỳ chọn nếu release có kèm.

**3.** Cài app và mở từ Start Menu hoặc Desktop shortcut.

**4.** Cài Google Chrome/Chromium nếu máy chưa có; app có thể tự resolve ChromeDriver khi khả dụng.

> App chạy trong Electron desktop window và tự start backend local; không cần cài Python global.

> Windows SmartScreen hoặc antivirus có thể cảnh báo cho tới khi app được code-sign hoặc có đủ reputation.

---

## Tính năng

| | Tính năng | Mô tả |
|---|-----------|-------|
| Auto Extract | **Đọc cấu trúc form** | Tự động đọc title, description, page và câu hỏi từ Google Form respondent URL |
| Question Types | **12 loại câu hỏi** | Text, Multiple Choice, Checkbox, Scale, Grid, Date, Time... |
| Custom Probabilities | **Tuỳ chỉnh xác suất** | Cấu hình xác suất chọn từng đáp án và câu trả lời tuỳ biến |
| Bulk Submit | **Submit hàng loạt** | Multithreading với delay ngẫu nhiên, success/fail realtime |
| Live Monitoring | **Giám sát realtime** | CPU, network và thread metrics trong quá trình submit |
| Copy Form MVP | **Copy best-effort** | Preview/copy form sang target editable link, kèm warnings cho unsupported features |
| i18n | **Tiếng Anh / Tiếng Việt** | Chuyển ngôn ngữ trong UI |
| History | **Lịch sử submission** | Lưu lịch sử submission và export CSV |

---

## Workflow

```text
① Paste URL          ② Configure          ③ Submit settings          ④ Monitor
   Google Form URL  →  Set probabilities  →  Threads & delay        →  Live progress
   → Auto extract      per answer option     Min/max delay             Success/fail
```

---

## Known Issues (Beta)

- Copy Form là best-effort, không claim exact clone Google Form.
- Một số tính năng Google Forms như grid native, file upload, quiz/theme/branching có thể unsupported hoặc partial.
- Windows SmartScreen có thể cảnh báo khi app chưa code-sign.
- Docker path chưa được kiểm tra đầy đủ trên tất cả cấu hình.

---

## Dành cho Developer (chạy từ source)

<details>
<summary>Click để mở hướng dẫn</summary>

### Prerequisites
- Python 3.11+
- Node.js 20+ nếu chạy Electron/package installer
- [uv](https://docs.astral.sh/uv/) *(khuyến nghị)* hoặc pip
- Google Chrome/Chromium

### Setup Flask backend

```bash
git clone https://github.com/PhamXuanKhang/google-form-tool.git
cd google-form-tool

uv sync
# hoặc
pip install -r requirements.txt

python wsgi.py
```

Mở `http://localhost:5000` khi chạy backend trực tiếp.

### Electron dev

```bash
npm install
npm run electron:dev
```

### Landing page dev

```bash
cd landing
npm run dev
```

### Chrome paths tuỳ chọn

Copy `.env.example` thành `.env` và cấu hình nếu muốn dùng Chrome/ChromeDriver cụ thể:

```env
CHROME_BINARY_PATH=C:\Path\To\chrome.exe
CHROME_DRIVER_PATH=C:\Path\To\chromedriver.exe
```

### Build Windows installers

```powershell
.\scripts\package-windows.ps1
```

Output nằm trong `release/`, gồm installer artifacts và `SHA256SUMS.txt`.

### Chạy tests

```bash
pytest tests/ -v
```

### Docker nâng cao

```bash
docker compose up --build
```

</details>

---

## Release flow

- Build installer bằng `scripts/package-windows.ps1`.
- Upload `.exe`, optional `.msi`, và `SHA256SUMS.txt` lên [GitHub Releases](https://github.com/PhamXuanKhang/google-form-tool/releases/latest).
- Landing page không lưu binary trong repo; CTA luôn trỏ tới GitHub Releases latest.
- Khi deploy Vercel xong, thay `https://<your-vercel-app>.vercel.app` bằng URL thật.

---

## Feedback & liên hệ

Đây là bản **Beta** — mong nhận phản hồi và báo lỗi từ bạn.

<div align="center">

[![Report Bug](https://img.shields.io/badge/Report_Bug-GitHub_Issues-red?style=for-the-badge)](https://github.com/PhamXuanKhang/google-form-tool/issues/new)
[![Email](https://img.shields.io/badge/Email-phamxuankhang2004@gmail.com-EA4335?style=for-the-badge)](mailto:phamxuankhang2004@gmail.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-KhangPham-0A66C2?style=for-the-badge)](https://www.linkedin.com/in/xuan-khang-pham-715208279/)
[![GitHub](https://img.shields.io/badge/GitHub-PhamXuanKhang-181717?style=for-the-badge)](https://github.com/PhamXuanKhang)

</div>

---

<div align="center">
  <sub>Made by <a href="https://github.com/PhamXuanKhang">KhangPham</a> · v1.1.0</sub>
</div>
