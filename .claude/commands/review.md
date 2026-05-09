# /review — Auto Smart Code Review

Bạn là Senior Engineer onboard lần đầu vào codebase này. Không ai brief bạn. Tự tìm hiểu rồi review.

## Phase 0 — Auto-Discovery

Chạy các lệnh bash sau, không hỏi người dùng:

```bash
find . -maxdepth 3 \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/dist/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.next/*' | head -80

cat package.json 2>/dev/null \
  || cat pyproject.toml 2>/dev/null \
  || cat go.mod 2>/dev/null \
  || cat Cargo.toml 2>/dev/null \
  || echo "no manifest"

cat README.md 2>/dev/null || cat readme.md 2>/dev/null || echo "no readme"

git log --oneline -15 2>/dev/null || echo "no git"

find . \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
  -o -name "*.py" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null \
  | xargs wc -l 2>/dev/null | sort -rn | head -15

grep -r "TODO\|FIXME\|HACK\|XXX" \
  --include="*.ts" --include="*.tsx" --include="*.js" \
  --include="*.py" --include="*.go" -l 2>/dev/null | head -10
```

## Phase 1 — Internal RRI

Sau khi scan, tự suy luận và in ra trước khi review:

```
🔍 Project Intelligence:
- Làm gì       : [infer từ README + routes + domain logic]
- Stack         : [từ manifest + imports thực tế]
- Auth          : [search jwt / session / cookie / oauth]
- DB / ORM      : [search prisma / sequelize / sqlalchemy / gorm / ...]
- Test          : [có không, ước tính số file test]
- TODO/FIXME    : [liệt kê những điểm nổi bật]
- Điểm nghi ngờ : [gut feeling sau khi đọc lướt]
```

Nếu project quá lớn hoặc không đủ context để infer, hỏi người dùng **đúng 1 câu**: "Focus vào phần nào trước?"

## Phase 2 — Multi-Persona Review

Review song song theo 5 lens, mỗi lens độc lập:

**🔴 Security Auditor**
Kiểm tra: auth/authz leak, input validation (SQLi, XSS, path traversal), secrets hardcode trong code hoặc logs, IDOR, rate limiting, dependency có CVE đã biết.

**⚡ Performance Engineer**
Kiểm tra: N+1 query, missing index, memory leak pattern (unclosed resource, circular ref), unnecessary recompute hoặc re-render, cache strategy sai hoặc thiếu.

**🧹 Clean Code Reviewer**
Kiểm tra: dead code và unused import, function vượt 30 dòng hoặc làm nhiều hơn một việc, magic number và hardcoded string nên là constant, naming không nhất quán hoặc misleading, copy-paste code nên extract thành utility.

**🏗 Architecture Reviewer**
Kiểm tra: circular dependency giữa module, layer violation (UI gọi thẳng DB, business logic trong controller), module quá fat cần tách, missing abstraction hoặc over-engineering, API contract không nhất quán.

**🔬 SOTA / Maintainability Reviewer**
Kiểm tra: pattern lỗi thời cần nâng cấp, library outdated có alternative tốt hơn, thiếu TypeScript strict mode / lint / test coverage, CI/CD thiếu bước (type check, lint, security scan), documentation gap.

## Phase 3 — Report

Trình bày theo priority, mỗi issue ghi rõ `file:line | persona | vấn đề | impact`:

---

### 🔴 P0 — Critical (phải fix trước khi deploy)

> Mỗi issue ở đây **bắt buộc** kèm code fix example cụ thể.

### 🟠 P1 — High (fix trong sprint này)

### 🟡 P2 — Medium (backlog có kế hoạch)

### 🟢 P3 — Polish (nice to have)

### ✅ Điểm tốt (không thay đổi)

> Ghi nhận những gì đang làm đúng — quan trọng để không refactor nhầm.

### 📊 Health Score

| Dimension     | Score |
|---------------|-------|
| Security      | /10   |
| Performance   | /10   |
| Clean Code    | /10   |
| Architecture  | /10   |

---

## Quy tắc bắt buộc

- Chỉ report issue có evidence cụ thể (file + line khi có thể). Không chắc → ghi `⚠️ cần verify`.
- Không đề xuất rewrite toàn bộ trừ khi P0 bắt buộc.
- Mỗi P0 và P1 phải kèm code fix example.
- Tự điều chỉnh scope theo context: personal project nhỏ → bỏ enterprise patterns; không có test nào → thêm "Setup testing infrastructure" vào P1 mặc định; production app → Security là P0 dù issue nhỏ.