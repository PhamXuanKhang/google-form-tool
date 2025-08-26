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
            const qTitle = `<h6 class="fw-bold">${question.text}</h6>
                            <div class="text-muted mb-2"><small>Type: <code>${type}</code></small></div>`;

            if (type === "input_email") {
                qEl.innerHTML = `
                    ${qTitle}
                    <div class="d-flex align-items-center mb-2 email-generator">
                        <label class="me-2">Email domain:</label>
                        <select class="form-select w-auto me-2 email-domain">
                            <option>@gmail.com</option>
                            <option>@yahoo.com</option>
                            <option>@company.com</option>
                        </select>
                        <button class="btn btn-sm btn-outline-primary generate-email-btn"><i class="fas fa-magic me-1"></i> Generate</button>
                        <textarea class="form-control mb-1 email-textarea" rows="4" placeholder="Each line = 1 email"></textarea>
                    </div>
                    
                    <div class="text-end text-muted small">Should match <b>form count</b></div>
                `;

            } else if (["input_text", "textarea", "date", "time"].includes(type)) {
                qEl.innerHTML = `
                    ${qTitle}
                    <div class="d-flex align-items-center mb-2">
                        <label class="me-2">Answer Type:</label>
                        <select class="form-select w-auto me-2">
                            <option>Name</option>
                            <option>Phone</option>
                            <option>Date</option>
                            <option>Hour</option>
                            <option>Minute</option>
                            <option>AI Generate</option>
                        </select>
                        <button class="btn btn-sm btn-outline-primary"><i class="fas fa-magic me-1"></i> Generate</button>
                    </div>
                    <div class="d-flex align-items-center mb-2">
                        <label class="me-2">Distribution %:</label>
                        <input type="number" class="form-control w-25" value="100" min="0" max="100">
                        <span class="ms-1">%</span>
                    </div>
                    <textarea class="form-control" rows="4" placeholder="Each line = 1 answer"></textarea>
                `;
            }

            else if (["multiple_choice", "dropdown", "linear_scale", "rank"].includes(type)) {
                const opts = (question.answer_config?.options || []);
                let optionsHTML = opts.map((opt, i) => `
                    <div class="d-flex align-items-center mb-2">
                        <input class="form-control me-2" value="${opt.text}" disabled>
                        <input type="number" class="form-control w-25 option-percent" value="${i === opts.length - 1 ? 100 : 0}" min="0" max="100" 
                            oninput="adjustPercentDistribution(this)">
                        <span class="ms-1">%</span>
                    </div>
                `).join("");

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
                    <div class="d-flex align-items-center mb-2">
                        <input class="form-control me-2" value="${opt.text}" disabled>
                        <input type="number" class="form-control w-25" value="0" min="0" max="100">
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
        const textarea = container.querySelector(".email-textarea");

        generateBtn.addEventListener("click", () => {
            const domain = domainSelect.value;
            const count = parseInt(document.getElementById("form-count").value || 10);
            textarea.value = generateEmails(domain, count);
        });
    });
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
