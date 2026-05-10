let sourceFormId = null;
let copyPlan = null;

const sourceUrlInput = document.getElementById("source-form-url");
const extractSourceBtn = document.getElementById("extract-source-btn");
const previewPlanBtn = document.getElementById("preview-plan-btn");
const applyCopyBtn = document.getElementById("apply-copy-btn");
const targetEditUrlInput = document.getElementById("target-edit-url");
const ownershipConfirmation = document.getElementById("ownership-confirmation");
const sourceSummary = document.getElementById("source-summary");
const planSummary = document.getElementById("plan-summary");
const capabilityMatrix = document.getElementById("capability-matrix");
const warningsList = document.getElementById("warnings-list");
const copyReport = document.getElementById("copy-report");

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function setMessage(element, message, type = "info") {
    element.innerHTML = `<div class="alert alert-${escapeHtml(type)} mb-0">${escapeHtml(message)}</div>`;
}

function updateApplyState() {
    applyCopyBtn.disabled = !sourceFormId || !copyPlan || !targetEditUrlInput.value.trim() || !ownershipConfirmation.checked;
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }
    return data;
}

function renderCapabilityMatrix(matrix) {
    const supported = escapeHtml((matrix.supported || []).join(", "));
    const partial = escapeHtml((matrix.partial || []).join(", "));
    const unsupported = escapeHtml((matrix.unsupported || []).join(", "));
    capabilityMatrix.innerHTML = `
        <div class="row g-3">
            <div class="col-md-4"><div class="border rounded p-3 h-100"><strong>Supported</strong><p class="mb-0 small">${supported}</p></div></div>
            <div class="col-md-4"><div class="border rounded p-3 h-100"><strong>Partial</strong><p class="mb-0 small">${partial}</p></div></div>
            <div class="col-md-4"><div class="border rounded p-3 h-100"><strong>Unsupported</strong><p class="mb-0 small">${unsupported}</p></div></div>
        </div>`;
}

function renderWarnings(warnings) {
    if (!warnings.length) {
        warningsList.innerHTML = `<div class="alert alert-success">No copy warnings for the current source form.</div>`;
        return;
    }
    warningsList.innerHTML = `<div class="alert alert-warning"><strong>Best-effort warnings</strong><ul class="mb-0">${warnings.map((warning) => `<li>${escapeHtml(warning.message)}</li>`).join("")}</ul></div>`;
}

extractSourceBtn.addEventListener("click", async () => {
    try {
        setMessage(sourceSummary, "Extracting source form...", "info");
        const data = await postJson("/form_copy/extract_source", { form_url: sourceUrlInput.value.trim() });
        sourceFormId = data.form.id;
        copyPlan = null;
        previewPlanBtn.disabled = false;
        setMessage(sourceSummary, `Source loaded: ${data.form.title}`, "success");
        planSummary.innerHTML = "";
        capabilityMatrix.innerHTML = "";
        warningsList.innerHTML = "";
        updateApplyState();
    } catch (error) {
        sourceFormId = null;
        previewPlanBtn.disabled = true;
        setMessage(sourceSummary, error.message, "danger");
        updateApplyState();
    }
});

previewPlanBtn.addEventListener("click", async () => {
    try {
        setMessage(planSummary, "Building copy plan...", "info");
        const data = await postJson("/form_copy/preview_plan", { form_id: sourceFormId });
        copyPlan = data.plan;
        renderCapabilityMatrix(copyPlan.capability_matrix);
        renderWarnings(copyPlan.warnings || []);
        setMessage(planSummary, `${copyPlan.operations.length} copy operations planned. Review warnings before applying.`, "success");
        updateApplyState();
    } catch (error) {
        copyPlan = null;
        setMessage(planSummary, error.message, "danger");
        updateApplyState();
    }
});

applyCopyBtn.addEventListener("click", async () => {
    try {
        setMessage(copyReport, "Applying copy plan to target form...", "info");
        const data = await postJson("/form_copy/apply_to_target", {
            form_id: sourceFormId,
            target_url: targetEditUrlInput.value.trim(),
            ownership_confirmed: ownershipConfirmation.checked,
        });
        const result = data.result;
        const warnings = result.warnings || [];
        copyReport.innerHTML = `<div class="alert alert-${result.status === "success" ? "success" : "warning"}">
            <strong>Status:</strong> ${escapeHtml(result.status)}<br>
            <strong>Operations:</strong> ${escapeHtml(result.operations_succeeded)}/${escapeHtml(result.operations_total)} succeeded.
            ${warnings.length ? `<ul class="mb-0 mt-2">${warnings.map((warning) => `<li>${escapeHtml(warning.message)}</li>`).join("")}</ul>` : ""}
        </div>`;
    } catch (error) {
        setMessage(copyReport, error.message, "danger");
    }
});

targetEditUrlInput.addEventListener("input", updateApplyState);
ownershipConfirmation.addEventListener("change", updateApplyState);