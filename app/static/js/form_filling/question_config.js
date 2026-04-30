function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Make sure renderQuestionsStep2 is available globally
function renderQuestionsStep2(formData) {
    const container = document.getElementById("step-2-questions");
    container.innerHTML = `
        <div class="mb-4">
            <label class="form-label fw-bold">Number of Forms to Submit:</label>
            <input type="number" id="form-count" class="form-control w-25" min="1" value="10">
        </div>
    `;

    const pages = formData.response_config.pages || [];
    pages.forEach((page, pageIndex) => {
        const pageDiv = document.createElement('div');
        pageDiv.classList.add("mb-4");
        pageDiv.innerHTML = `<h5 class="text-primary mb-3">Page ${pageIndex + 1}</h5>`;

        (page.questions || []).forEach((question) => {
            const qEl = document.createElement('div');
            qEl.classList.add("card", "p-3", "mb-3");

            const type = question.type;
            qEl.dataset.questionId = question.question_id || "";
            qEl.dataset.questionType = type || "";

            const qTitle = `<h6 class="fw-bold">${escapeHtml(question.text)}</h6>
                            <div class="text-muted mb-2"><small>Type: <code>${escapeHtml(type)}</code></small></div>`;

            const isDefaultEmail = question.question_id === "q_email" && !question.entry_id;
            const hasConfiguredEmail = Array.isArray(question.answer_config?.answers) && question.answer_config.answers.length > 0;
            const hasFillPercent = Number.isFinite(question.answer_config?.fill_percentage) && question.answer_config.fill_percentage > 0;

            if (isDefaultEmail && !hasConfiguredEmail && !hasFillPercent) {
                return;
            }

            if (type === "input_email") {
                qEl.innerHTML = `
                    ${qTitle}
                    <div class="d-flex align-items-center mb-2">
                        <label class="me-2">Distribution %:</label>
                        <input type="number" class="form-control w-25 fill-percent" value="100" min="0" max="100">
                        <span class="ms-1">%</span>
                    </div>
                    <div class="d-flex align-items-center mb-2 email-generator">
                        <label class="me-2">Email domain:</label>
                        <select class="form-select w-auto me-2 email-domain">
                            <option>@gmail.com</option>
                            <option>@yahoo.com</option>
                            <option>@company.com</option>
                        </select>
                        <button class="btn btn-sm btn-outline-primary generate-email-btn"><i class="fas fa-magic me-1"></i> Generate</button>
                    </div>
                    <textarea class="form-control mb-1 email-textarea answer-textarea" rows="4" placeholder="Each line = 1 email"></textarea>

                    <div class="text-end text-muted small">Each line is a candidate email; submissions pick randomly.</div>
                `;

            } else if (["input_text", "textarea", "date", "time"].includes(type)) {
                const generatorOptions = (() => {
                    if (type === "input_text") return ["Name", "Phone", "Generic Text", "AI Generate"];
                    if (type === "textarea") return ["Generic Text", "AI Generate"];
                    if (type === "date") return ["Date"];
                    if (type === "time") return ["Time"];
                    return ["Generic Text"];
                })();
                const optionsHtml = generatorOptions
                    .map(option => `<option>${option}</option>`)
                    .join("");
                const placeholder = type === "date"
                    ? "Each line = YYYY-MM-DD"
                    : type === "time"
                        ? "Each line = HH:MM"
                        : "Each line is a candidate answer";
                qEl.innerHTML = `
                    ${qTitle}
                    <div class="d-flex align-items-center mb-2">
                        <label class="me-2">Answer Type:</label>
                        <select class="form-select w-auto me-2 answer-generator-type">
                            ${optionsHtml}
                        </select>
                        <button class="btn btn-sm btn-outline-primary generate-answer-btn"><i class="fas fa-magic me-1"></i> Generate</button>
                    </div>
                    <div class="d-flex align-items-center mb-2">
                        <label class="me-2">Distribution %:</label>
                        <input type="number" class="form-control w-25 fill-percent" value="100" min="0" max="100">
                        <span class="ms-1">%</span>
                    </div>
                    <textarea class="form-control answer-textarea" rows="4" placeholder="${placeholder}"></textarea>
                    <div class="text-end text-muted small">Selections are randomized per submission.</div>
                `;
            }

            else if (["multiple_choice", "dropdown", "linear_scale", "rank"].includes(type)) {
                const opts = (question.answer_config?.options || []);
                const supportsBranchSubmit = ["multiple_choice", "dropdown"].includes(type);
                let optionsHTML = opts.map((opt, i) => {
                    const branchSubmitControl = supportsBranchSubmit ? `
                        <div class="form-check ms-2 mb-0 flex-shrink-0">
                            <input class="form-check-input option-submit-branch" type="checkbox" ${opt.next_page_id === "__submit__" ? "checked" : ""}>
                            <label class="form-check-label small">Submit after this option</label>
                        </div>
                    ` : "";

                    return `
                        <div class="d-flex align-items-center mb-2 option-row" data-option-text="${escapeHtml(opt.text)}">
                            <input class="form-control me-2 option-text" value="${escapeHtml(opt.text)}" disabled>
                            <input type="number" class="form-control w-25 option-percent" value="${i === opts.length - 1 ? 100 : 0}" min="0" max="100" 
                                oninput="adjustPercentDistribution(this)">
                            <span class="ms-1">%</span>
                            ${branchSubmitControl}
                        </div>
                    `;
                }).join("");

                qEl.innerHTML = `
                    ${qTitle}
                    <div class="d-flex justify-content-between">
                        <div class="text-muted small mb-2">Adjust % per option, total = 100%</div>
                        <button class="btn btn-sm btn-outline-secondary" onclick="randomizeDistribution(this)">🎲 Randomize</button>
                    </div>
                    ${optionsHTML}
                    <div class="text-end text-muted small mt-1">Total: <span class="percent-total">100%</span></div>
                    <!-- Optional: pie chart -->
                    <div class="chart-container mt-3">
                        <canvas class="form-chart" height="120"></canvas>
                    </div>
                `;
                const chartCanvas = qEl.querySelector("canvas.form-chart");
                const labels = opts.map(opt => opt.text);
                const values = opts.map((_, i) => i === opts.length - 1 ? 100 : 0);

            }

            else if (type === "checkbox") {
                const opts = (question.answer_config?.options || []);
                let optionsHTML = opts.map((opt) => `
                    <div class="d-flex align-items-center mb-2 option-row" data-option-text="${escapeHtml(opt.text)}">
                        <input class="form-control me-2 option-text" value="${escapeHtml(opt.text)}" disabled>
                        <input type="number" class="form-control w-25 option-percent" value="0" min="0" max="100">
                        <span class="ms-1">%</span>
                    </div>
                `).join("");

                qEl.innerHTML = `
                    ${qTitle}
                    <div class="text-muted small mb-2">Set max % per option (independent, no total check)</div>
                    ${optionsHTML}
                `;
            }

            pageDiv.appendChild(qEl);
        });

        container.appendChild(pageDiv);
    });

    document.querySelectorAll(".email-generator").forEach(container => {
        const domainSelect = container.querySelector(".email-domain");
        const generateBtn = container.querySelector(".generate-email-btn");
        const textarea = container.closest(".card").querySelector(".email-textarea");

        generateBtn.addEventListener("click", () => {
            const domain = domainSelect.value;
            const count = getTargetCount();
            textarea.value = generateEmails(domain, count);
        });
    });

    document.querySelectorAll(".generate-answer-btn").forEach(button => {
        button.addEventListener("click", async () => {
            const card = button.closest(".card");
            const generatorType = card.querySelector(".answer-generator-type")?.value || "Text";
            const textarea = card.querySelector(".answer-textarea");
            if (!textarea) return;

            if (String(generatorType).toLowerCase() === "ai generate") {
                await runInlineAIGenerate(card, button, textarea);
                return;
            }

            textarea.value = generateValues(generatorType, getTargetCount()).join("\n");
        });
    });
}

async function runInlineAIGenerate(card, button, textarea) {
    const t = (key, fallback) => window.i18n?.[key] || fallback;
    const questionType = card.dataset.questionType;
    const questionId = card.dataset.questionId;
    const targetCount = getTargetCount();

    if (!["input_text", "textarea"].includes(questionType)) {
        window.showPopup?.(t("aiOnlyForText", "AI Generate only supports text-like questions in this beta."), 'warning');
        return;
    }
    if (!window.currentFormId) {
        window.showPopup?.(t("pleaseExtractFormFirst", "Please extract a form first."), 'warning');
        return;
    }

    const apiKey = await (window.getOrAskGeminiKey?.() || Promise.resolve(null));
    if (!apiKey) return;  // user cancelled or key invalid; popup already shown

    const originalLabel = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i> ${t("generating", "Generating...")}`;

    try {
        const res = await fetch('/generate_ai_text_answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                form_id: window.currentFormId,
                question_id: questionId,
                api_key: apiKey,
                count: targetCount,
            }),
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok || !result.success) {
            window.showPopup?.(result.error || t("aiGenerateFailed", "Failed to generate AI answers"), 'error');
            return;
        }
        const answers = Array.isArray(result.answers) ? result.answers.slice(0, targetCount) : [];
        while (answers.length < targetCount) {
            answers.push("");
        }
        textarea.value = answers.join("\n");
        window.showPopup?.(t("aiGenerateSuccess", "AI answers generated."), 'success');
    } catch (e) {
        window.showPopup?.(`${t("aiGenerateFailed", "Failed to generate AI answers")}: ${e.message}`, 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = originalLabel;
    }
}


function adjustPercentDistribution(changedInput) {
    const container = changedInput.closest('.card');
    const percentInputs = container.querySelectorAll('.option-percent');
    const totalDisplay = container.querySelector('.percent-total');

    let total = 0;
    percentInputs.forEach(input => total += parseFloat(input.value || 0));

    if (total > 100) {
        // Nếu tổng vượt 100, tự động giảm các ô khác (trừ ô vừa chỉnh)
        let excess = total - 100;
        percentInputs.forEach(input => {
            if (input !== changedInput && excess > 0) {
                let val = parseFloat(input.value);
                let reduce = Math.min(val, excess);
                input.value = val - reduce;
                excess -= reduce;
            }
        });
    }

    // Cập nhật lại tổng
    total = 0;
    percentInputs.forEach(input => total += parseFloat(input.value || 0));
    if (totalDisplay) totalDisplay.textContent = total.toFixed(0) + "%";
}


function randomizeDistribution(button) {
    const container = button.closest('.card');
    const inputs = container.querySelectorAll('.option-percent');

    const n = inputs.length;
    let values = Array.from({ length: n }, () => Math.random());
    const sum = values.reduce((a, b) => a + b, 0);
    values = values.map(v => Math.round((v / sum) * 100));

    // Điều chỉnh lại để tổng chính xác 100%
    let diff = 100 - values.reduce((a, b) => a + b, 0);
    values[values.length - 1] += diff;

    inputs.forEach((input, i) => input.value = values[i]);
    const totalDisplay = container.querySelector('.percent-total');
    if (totalDisplay) totalDisplay.textContent = "100%";
}


function adjustTextAreaRows(percentInput) {
    const container = percentInput.closest('.card');
    const textarea = container.querySelector('textarea');
    const formCountInput = document.getElementById('form-count');
    const formCount = parseInt(formCountInput.value || 10);
    const percent = parseFloat(percentInput.value || 100);
    const lines = Math.round((percent / 100) * formCount);

    const existingLines = textarea.value.trim().split("\n");
    if (existingLines.length > lines) {
        textarea.value = existingLines.slice(0, lines).join("\n");
    } else {
        while (textarea.value.trim().split("\n").length < lines) {
            textarea.value += "\n";
        }
    }

    textarea.rows = Math.max(lines, 3);
}


function generateEmails(domain, count) {
    const result = [];
    const names = ["user", "demo", "test", "form", "data", "entry"];
    for (let i = 0; i < count; i++) {
        const name = names[Math.floor(Math.random() * names.length)];
        const id = Math.floor(1000 + Math.random() * 9000);
        result.push(`${name}${id}${domain}`);
    }
    return result.join("\n");
}

function getTargetCount() {
    const formCount = document.getElementById("form-count")?.value;
    const settingsCount = document.getElementById("settings-form-count")?.value;
    const count = parseInt(formCount || settingsCount || "10", 10);
    return Number.isInteger(count) && count > 0 ? count : 10;
}

function generateValues(type, count) {
    const normalizedType = String(type || "").toLowerCase();
    if (normalizedType === "name") return generateNames(count);
    if (normalizedType === "phone") return generatePhones(count);
    if (normalizedType === "date") return generateDates(count);
    if (normalizedType === "time") return generateTimes(count);
    if (normalizedType === "generic text") return generateGenericText(count);
    return generateGenericText(count);
}

function generateNames(count) {
    const firstNames = ["An", "Binh", "Chi", "Dung", "Ha", "Khanh", "Linh", "Minh", "Nam", "Trang"];
    const lastNames = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui", "Do"];
    return Array.from({ length: count }, (_, i) => {
        const first = firstNames[i % firstNames.length];
        const last = lastNames[(i + Math.floor(i / firstNames.length)) % lastNames.length];
        return `${last} ${first}`;
    });
}

function generatePhones(count) {
    const prefixes = ["090", "091", "093", "096", "097", "098", "032", "033", "034", "035"];
    return Array.from({ length: count }, (_, i) => {
        const suffix = String(1000000 + ((i * 7919) % 9000000)).padStart(7, "0");
        return `${prefixes[i % prefixes.length]}${suffix}`;
    });
}

function generateDates(count) {
    const today = new Date();
    return Array.from({ length: count }, (_, i) => {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        return [
            date.getFullYear(),
            String(date.getMonth() + 1).padStart(2, "0"),
            String(date.getDate()).padStart(2, "0")
        ].join("-");
    });
}

function generateTimes(count) {
    return Array.from({ length: count }, (_, i) => {
        const hour = String(i % 24).padStart(2, "0");
        const minute = String((i * 7) % 60).padStart(2, "0");
        return `${hour}:${minute}`;
    });
}

function generateGenericText(count) {
    return Array.from({ length: count }, (_, i) => `Sample answer ${i + 1}`);
}

function collectManualEdits() {
    const edits = {};
    const questionCards = document.querySelectorAll("#step-2-questions .card[data-question-id]");

    questionCards.forEach(card => {
        const questionId = card.dataset.questionId;
        if (!questionId) return;

        const edit = {};
        const fillPercentInput = card.querySelector(".fill-percent");
        const textarea = card.querySelector(".answer-textarea");
        const optionRows = card.querySelectorAll(".option-row");

        if (fillPercentInput) {
            edit.fill_percentage = parsePercent(fillPercentInput.value, 100);
        }

        if (textarea) {
            const answers = textarea.value
                .split("\n")
                .map(line => line.trim())
                .filter(Boolean);
            if (answers.length > 0) {
                edit.answers = answers;
            }
        }

        if (optionRows.length > 0) {
            edit.options = Array.from(optionRows).map(row => ({
                text: row.dataset.optionText || row.querySelector(".option-text")?.value || "",
                percentage: parsePercent(row.querySelector(".option-percent")?.value, 0),
                next_page_id: row.querySelector(".option-submit-branch")?.checked ? "__submit__" : null
            })).filter(option => option.text);
        }

        if (Object.keys(edit).length > 0) {
            edits[questionId] = edit;
        }
    });

    return edits;
}

function parsePercent(value, fallback) {
    const percent = parseFloat(value);
    return Number.isFinite(percent) ? percent : fallback;
}

function validateManualConfiguration() {
    const issues = [];
    const questionCards = document.querySelectorAll("#step-2-questions .card[data-question-id]");

    questionCards.forEach(card => {
        const type = card.dataset.questionType || "";
        const title = card.querySelector("h6")?.textContent?.trim() || "Question";
        const fillInput = card.querySelector(".fill-percent");
        const fillValue = fillInput ? parseFloat(fillInput.value) : null;

        if (fillInput && (!Number.isFinite(fillValue) || fillValue < 0 || fillValue > 100)) {
            issues.push(`${title}: distribution % must be between 0 and 100.`);
        }

        if (["multiple_choice", "dropdown", "linear_scale"].includes(type)) {
            const percentInputs = card.querySelectorAll(".option-percent");
            let total = 0;
            let hasInvalid = false;
            percentInputs.forEach(input => {
                const val = parseFloat(input.value);
                if (!Number.isFinite(val) || val < 0 || val > 100) {
                    hasInvalid = true;
                }
                total += Number.isFinite(val) ? val : 0;
            });
            if (hasInvalid) {
                issues.push(`${title}: option % must be between 0 and 100.`);
            }
            if (percentInputs.length > 0 && Math.round(total) !== 100) {
                issues.push(`${title}: option % total must equal 100 (current ${total.toFixed(0)}).`);
            }
        }

        if (["input_text", "textarea", "input_email", "date", "time"].includes(type)) {
            const textarea = card.querySelector("textarea");
            const answers = (textarea?.value || "")
                .split("\n")
                .map(line => line.trim())
                .filter(Boolean);
            const effectiveFill = Number.isFinite(fillValue) ? fillValue : 100;
            if (effectiveFill > 0 && answers.length === 0) {
                issues.push(`${title}: add at least one answer or set % to 0.`);
            }
        }
    });

    return issues;
}

// Export functions to global scope
window.renderQuestionsStep2 = renderQuestionsStep2;
window.adjustPercentDistribution = adjustPercentDistribution;
window.randomizeDistribution = randomizeDistribution;
window.adjustTextAreaRows = adjustTextAreaRows;
window.generateEmails = generateEmails;
window.generateValues = generateValues;
window.collectManualEdits = collectManualEdits;
window.validateManualConfiguration = validateManualConfiguration;
