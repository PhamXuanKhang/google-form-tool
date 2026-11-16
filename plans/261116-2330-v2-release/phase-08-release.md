# Phase 8 — Release

Nhánh: `release/v2` (fast-forward tới nhánh phase xanh mới nhất).

## Xác định chế độ

Lập bảng 7 nhóm tính năng của contract với trạng thái xong/chưa, kèm bằng chứng acceptance.

- **Đủ**: cả 7 nhóm xong và mọi acceptance đạt → version 2.0.0, PR chuyển sang ready.
- **Một phần**: thiếu bất kỳ nhóm nào → không đặt 2.0.0 (giữ `1.2.0`), PR ở lại draft, phần
  thiếu ghi rõ trong mô tả PR và báo cáo. Không xoá phase chưa xong khỏi plan.

## Bước

1. Rà hồi quy toàn bộ: pytest, ruff, route snapshot. Chạy lại riêng các test acceptance 1–7.
2. Rà chéo:
   - `grep -rn "https\?://" app/templates` chỉ còn link điều hướng ra ngoài.
   - Mọi module `app.*` có trong `google_form_tool.spec` (test của phase 2).
   - Mọi chuỗi UI mới có bản dịch tiếng Việt (không còn `msgstr ""` cho chuỗi mới); `.mo`
     đã build lại.
   - Không còn `console.log` gỡ lỗi, TODO, hay code chết do chính đợt này tạo ra.
   - `gitleaks` và `pip-audit`, `npm audit` như CI (`.github/workflows/ci.yml`), nếu có sẵn
     công cụ cục bộ; nếu không, dựa vào CI trên PR.
3. Review: chạy skill review code trên diff `master...release/v2`, mức đủ sâu cho thay đổi
   high-risk. Sửa phát hiện đã xác minh; phát hiện đòi đảo quyết định của contract thì ghi
   vào báo cáo cho user, không tự đảo.
4. Docs (đọc từng file trước khi sửa, kiểm lại từng khẳng định với code):
   - `docs/product/user-stories.md`: US-009 đến US-015 đã viết ở các phase; kiểm bảng route
     khớp `tests/test_route_snapshot.py`; cập nhật Backlog (thêm dòng "tạo/sửa form qua agent
     — 2.1").
   - `docs/TEST_MATRIX.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md` (smoke MCP),
     `docs/decisions/README.md` (liệt kê 0004, 0005).
   - `README.md`: bảng tính năng, workflow, mục "Dùng với Claude/agent (MCP)", Known Issues
     (Copy Form vẫn best-effort; MCP cần app đang mở; chạy rải chỉ chạy khi app mở).
   - `landing/index.html`: cập nhật danh sách tính năng nếu trang có liệt kê.
   - `.env.example`: biến mới (`RUNS_DIR`).
5. Version (chỉ ở chế độ Đủ): `app/__init__.py:43` `__version__`, `package.json`, dòng version
   cuối README, và mọi chỗ khác (`grep -rn "1\.2\.0"` ngoài `CHANGELOG.md`, lockfile, plans).
6. `CHANGELOG.md`: mục `[2.0.0] - <ngày chạy>` theo format hiện có (tiếng Việt, Added/Changed/
   Fixed/Security/Internal), chỉ liệt kê thứ đã xong; thêm link so sánh ở cuối file. Ở chế độ
   Một phần, ghi dưới `[Unreleased]`.
7. Packaging smoke đầy đủ: `/healthz` 200, một file `static/vendor` trả 200, smoke MCP (script
   của phase 4). Dọn tiến trình và port; revert thay đổi do build sinh ra.
8. Commit: `chore(release): bump version to 2.0.0 and add changelog` (chế độ Đủ) cùng các
   commit docs riêng. Push `release/v2`.
9. PR: cập nhật tiêu đề (`feat: release 2.0`) và mô tả: tóm tắt 7 nhóm, bảng acceptance với
   bằng chứng, số test trước/sau, kết quả smoke, danh sách "user tự kiểm trước khi publish"
   (từ `plan.md`), các điểm chưa kiểm được trong goal run. Chế độ Đủ: `gh pr ready`.
10. Theo dõi CI trên PR (`gh pr checks --watch`); sửa tới khi mọi check bắt buộc xanh. Check
    đỏ vì hạ tầng (không phải code) sau 2 lần chạy lại → ghi vào báo cáo.
11. `--advice`: gọi `kongming` rà toàn bộ diff và bằng chứng; đăng đánh giá cùng bước tiếp
    theo thành một comment trên PR.
12. Cập nhật frontmatter `plan.md` (`status: completed` hoặc `in_progress`) và viết
    `plans/reports/goal-run-261117-done.md`. Commit `docs(plans): ...`, push.

## Không làm

Không merge PR, không tạo tag, không publish GitHub Release, không sửa URL placeholder của
landing.

## Điều kiện dừng

CI đỏ vì code sau 3 vòng sửa; không push được; phát hiện từ review đòi đổi contract.
