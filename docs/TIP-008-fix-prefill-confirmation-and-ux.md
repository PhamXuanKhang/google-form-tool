# TIP-008: Fix Prefill Submission Confirmation + Step 3 Form Count UX

## Background

After DBG-007 manual testing, user reported two issues:
1. All prefill submissions fail — user sees `<redacted>` in server logs and checkbox/multiple-choice questions have no answers in the prefill URL.
2. Step 3 shows a redundant, editable form count that conflicts with Step 2.

---

## Root Cause Analysis

### Issue A — Submission 100% failure

**The `<redacted>` is log format, not a real value.** `_redact_prefill_url()` is called only inside logging statements. The actual URL sent to Chrome has real values (lorem ipsum text, option names, etc.). The user is reading the server log and misidentifying `Prefill submit confirmation failed for https://...?entry.111=<redacted>` as Chrome showing `<redacted>` in form fields.

**Real root cause: confirmation wait fails for Vietnamese forms.**

After clicking Submit, `_submit_prefilled_url` waits with:

```python
WebDriverWait(driver, 10).until(
    lambda d: (
        d.current_url != start_url
        or d.find_elements(
            By.XPATH,
            "//*[contains(text(), 'response') or "
            "contains(text(), 'submitted') or "
            "contains(text(), 'gửi') or "
            "contains(text(), 'recorded')]"
        )
    )
)
```

This fails because:
- Google Forms confirmation page may load at the **same URL** (URL doesn't change), so `d.current_url != start_url` is `False`.
- Vietnamese confirmation text is **"Câu trả lời của bạn đã được ghi lại"** — it contains none of the four keywords. "ghi lại" ≠ "gửi" (send), and the English words "response/submitted/recorded" don't appear.

Result: all 10 submissions timeout after 10 seconds each → 100% fail rate.

**Fix:** Replace URL/keyword detection with `EC.staleness_of(submit_button)`. When Google Forms navigates to the confirmation page (any language), the Submit button element is removed from the DOM. Selenium's staleness check is language-neutral.

---

### Issue B — Checkbox answers missing from prefill URL

`_select_multiple_options` in `form_processor.py` can return `[]`:

```python
if any(weight > 0 for weight in weights):
    return [
        option.text
        for option, weight in zip(configured_options, weights)
        if random.random() * 100 < weight  # Can be empty if all randoms miss
    ]
```

If every option has low weight (e.g., 10%), there is a `(0.9)^n` chance all randoms miss → empty list. In `PrefillLinkGenerator._build_params`, an empty list is skipped (`if value == []: continue`) → no `entry.*` param for that question → checkbox appears blank.

---

### Issue C — Step 3 form count conflicts with Step 2

`question_config.js` renders `#form-count` in Step 2 (inside `renderQuestionsStep2()`). The HTML template has a separate `#settings-form-count` input in Step 3. The sync in `navigation.js` runs **only once** (guarded by `dataset.syncedFromStep2`), so if the user:

1. Opens Step 2 — `#form-count` shows 10
2. Navigates to Step 3 — syncs once, `#settings-form-count` = 10 ✓
3. Goes back to Step 2, changes `#form-count` to 50
4. Returns to Step 3 — `#settings-form-count` still shows 10 ✗ (sync guard blocks re-sync)

User expectation: Step 2 is where they set the count; Step 3 should just confirm it.

---

## Changes Required

### Fix 1 — `app/core/form_submitter.py` — Replace confirmation check

In `_submit_prefilled_url`, replace the post-Submit `WebDriverWait` lambda with `EC.staleness_of`.

**Current code (lines ~542–558):**
```python
driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
driver.execute_script("arguments[0].click();", submit_button)

WebDriverWait(driver, 10).until(
    lambda d: (
        d.current_url != start_url
        or d.find_elements(
            By.XPATH,
            "//*[contains(text(), 'response') or "
            "contains(text(), 'submitted') or "
            "contains(text(), 'gửi') or "
            "contains(text(), 'recorded')]"
        )
    )
)
logger.info("Prefill URL submitted successfully")
return True
```

**Replace with:**
```python
driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
driver.execute_script("arguments[0].click();", submit_button)

WebDriverWait(driver, 10).until(
    EC.staleness_of(submit_button)
)
logger.info("Prefill URL submitted successfully")
return True
```

No other changes to `_submit_prefilled_url`.

---

### Fix 2 — `app/core/form_processor.py` — Prevent empty checkbox selection

In `_select_multiple_options`, guarantee at least one option is returned when weights are configured.

**Current code:**
```python
if any(weight > 0 for weight in weights):
    return [
        option.text
        for option, weight in zip(configured_options, weights)
        if random.random() * 100 < weight
    ]
```

**Replace with:**
```python
if any(weight > 0 for weight in weights):
    selected = [
        option.text
        for option, weight in zip(configured_options, weights)
        if random.random() * 100 < weight
    ]
    return selected if selected else [random.choice([opt.text for opt in configured_options])]
```

---

### Fix 3a — `app/templates/form_filling.html` — Make Step 3 count read-only

**Current (lines ~144–146):**
```html
<label for="settings-form-count" class="form-label">{{ _('Number of submissions') }}</label>
<input type="number" class="form-control" id="settings-form-count" min="1" max="500" value="10" step="1">
<div class="form-text">{{ _('Maximum 500 submissions per batch.') }}</div>
```

**Replace with:**
```html
<label for="settings-form-count" class="form-label">{{ _('Number of submissions') }}</label>
<input type="number" class="form-control bg-light" id="settings-form-count" min="1" max="500" value="10" step="1" readonly>
<div class="form-text">{{ _('Set in Step 2. Go back to change.') }}</div>
```

---

### Fix 3b — `app/static/js/form_filling/navigation.js` — Re-sync every time

In `syncSettingsFromExistingFormCount`, remove the one-time guard so it syncs every time Step 3 is shown.

**Current:**
```javascript
function syncSettingsFromExistingFormCount() {
    const settingsFormCount = document.getElementById("settings-form-count");
    const existingFormCount = document.getElementById("form-count");

    if (settingsFormCount && existingFormCount && !settingsFormCount.dataset.syncedFromStep2) {
        settingsFormCount.value = existingFormCount.value || settingsFormCount.value;
        settingsFormCount.dataset.syncedFromStep2 = "true";
    }
}
```

**Replace with:**
```javascript
function syncSettingsFromExistingFormCount() {
    const settingsFormCount = document.getElementById("settings-form-count");
    const existingFormCount = document.getElementById("form-count");

    if (settingsFormCount && existingFormCount) {
        settingsFormCount.value = existingFormCount.value || settingsFormCount.value;
    }
}
```

No changes needed to `main.js` — `getFormSettings()` already reads `#settings-form-count`, which will now always reflect the Step 2 value.

---

### Fix 4 — `tests/test_prefill_submission.py` — Update FakeWebDriverWait for staleness_of

`EC.staleness_of(element)` calls `element.is_enabled()` and returns `True` when it raises `StaleElementReferenceException`. `FakeElement.is_enabled()` never raises, so the condition never passes in tests → infinite loop.

Update `FakeWebDriverWait.until` to handle `staleness_of` by type-checking:

**Current:**
```python
class FakeWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver

    def until(self, condition):
        from selenium.common.exceptions import TimeoutException
        try:
            result = condition(self.driver)
            if not result:
                raise TimeoutException("Condition returned falsy")
            return result
        except TimeoutException:
            raise
        except Exception:
            raise TimeoutException("Condition threw exception")
```

**Replace with:**
```python
class FakeWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver

    def until(self, condition):
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support import expected_conditions as EC

        # staleness_of is always True in tests (page navigates after Submit click).
        if isinstance(condition, EC.staleness_of):
            return True

        try:
            result = condition(self.driver)
            if not result:
                raise TimeoutException("Condition returned falsy")
            return result
        except TimeoutException:
            raise
        except Exception:
            raise TimeoutException("Condition threw exception")
```

Also update `test_submit_prefilled_url_clicks_through_and_returns_true` assertion — script count stays at 4 (scrollIntoView + click for Next, scrollIntoView + click for Submit), no change needed there.

---

## Verification

After applying all changes:

```bash
pytest tests/ -v
```

All 127+ tests must pass.

Then manual test:
1. Extract a Vietnamese Google Form that has text, multiple-choice, and checkbox questions.
2. Submit with prefill_link mode, 1 submission, no delay.
3. Confirm at least 1 success (0% failure rate is the goal).
4. Navigate Step 2 → change Number of Forms → navigate to Step 3 → confirm Step 3 shows updated value and is read-only.

---

## Out of scope

- Improving data generators with Vietnamese name/phone data (reference: `D:\02_projects\tools\google-form-tool\manage_data.py`) — noted for a future TIP.
- Button XPATH improvements — current XPATH (`//div[@role='button']//span[contains(text(), 'Submit') or contains(text(), 'Gửi')]`) is acceptable; `EC.staleness_of` removes the need for a fragile post-submit text check.
