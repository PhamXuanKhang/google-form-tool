/**
 * Personas panel and AI Autopilot panel of the Configure Answers step.
 *
 * Personas: edit names and weights, then "Edit answers" shows the question
 * cards with that persona's settings. Cards that differ from the shared
 * settings are marked and can be reset. While editing a persona the wizard
 * cannot move on, so persona answers never overwrite the shared ones.
 *
 * Autopilot: asks the backend for a proposal (nothing is saved) and applies
 * only what the user selects, through /save_edit and the personas route.
 * Text from the form or the model is set with textContent only.
 */

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

const byId = (id) => document.getElementById(id);
const MAX_PERSONAS = 8;
let personas = [];
let baseForm = null;
let editing = null;  // persona being edited

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
}

async function readJson(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) throw new Error(data.error || t("requestFailed", "Request failed."));
    return data;
}

function questions(form) {
    return (form?.response_config?.pages || []).flatMap((page) => page.questions || []);
}

async function loadForm() {
    const data = await readJson(await fetch(`/forms/${encodeURIComponent(window.currentFormId)}`));
    baseForm = data.form;
    return baseForm;
}

function togglePanel(id, button) {
    const panel = byId(id);
    const open = panel.classList.toggle("d-none") === false;
    button.setAttribute("aria-expanded", String(open));
    return open;
}

// ------------------------------------------------------------- personas

function renderPersonas() {
    const list = byId("persona-list");
    list.replaceChildren(...personas.map((persona, index) => {
        const row = el("div", "persona-row");
        const name = el("input", "form-control form-control-sm");
        name.value = persona.name;
        name.maxLength = 80;
        name.setAttribute("aria-label", t("personaName", "Persona name"));
        name.addEventListener("input", () => { persona.name = name.value; });
        const weight = el("input", "form-control form-control-sm persona-weight");
        weight.type = "number";
        weight.min = "0";
        weight.max = "100";
        weight.step = "1";
        weight.value = persona.weight;
        weight.setAttribute("aria-label", t("personaWeight", "Share of responses (%)"));
        weight.addEventListener("input", () => { persona.weight = Number(weight.value) || 0; updateTotal(); });
        const overrides = Object.keys(persona.overrides || {}).length;
        const info = el("span", "small text-muted", `${overrides} ${t("overriddenQuestions", "questions differ")}`);
        const edit = el("button", "btn btn-outline-primary btn-sm", t("editAnswers", "Edit answers"));
        edit.type = "button";
        edit.addEventListener("click", () => startEditing(persona));
        const remove = el("button", "btn btn-outline-secondary btn-sm", t("remove", "Remove"));
        remove.type = "button";
        remove.addEventListener("click", () => { personas.splice(index, 1); renderPersonas(); });
        const percent = el("span", "small", "%");
        row.append(name, weight, percent, info, edit, remove);
        return row;
    }));
    if (!personas.length) list.appendChild(el("p", "small text-muted mb-0", t("noPersonas", "No personas: every response uses the shared settings.")));
    byId("persona-add").disabled = personas.length >= MAX_PERSONAS;
    updateTotal();
}

function updateTotal() {
    const total = personas.reduce((sum, persona) => sum + (Number(persona.weight) || 0), 0);
    const label = byId("persona-total");
    label.textContent = personas.length ? `${t("total", "Total")}: ${Math.round(total * 100) / 100}%` : "";
    label.classList.toggle("text-danger", personas.length > 0 && Math.abs(total - 100) > 0.01);
}

async function openPersonas() {
    if (!window.currentFormId) return;
    try {
        const data = await readJson(await fetch(`/forms/${encodeURIComponent(window.currentFormId)}/personas`));
        personas = data.personas;
        renderPersonas();
    } catch (error) {
        window.showPopup?.(error.message, "error");
    }
}

async function savePersonas() {
    try {
        const data = await readJson(await fetch(`/forms/${encodeURIComponent(window.currentFormId)}/personas`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ personas }),
        }));
        personas = data.personas;
        renderPersonas();
        window.showPopup?.(t("personasSaved", "Personas saved."), "success");
        return true;
    } catch (error) {
        window.showPopup?.(error.message, "error");
        return false;
    }
}

function settingsOf(config) {
    const options = (config?.options || []).map((option) => ({ text: option.text, percentage: Number(option.percentage) || 0 }));
    return {
        fill_percentage: config?.fill_percentage ?? null,
        answers: config?.answers?.length ? config.answers : null,
        options: options.length ? options : null,
    };
}

function sameSettings(a, b) {
    return JSON.stringify(settingsOf(a)) === JSON.stringify(settingsOf(b));
}

function markOverrides() {
    document.querySelectorAll("#step-2-questions .card[data-question-id]").forEach((card) => {
        card.querySelector(".override-tools")?.remove();
        const questionId = card.dataset.questionId;
        if (!editing || !editing.overrides?.[questionId]) return;
        const tools = el("div", "override-tools");
        tools.appendChild(el("span", "status-pill status-in_flight", t("overridden", "Differs for this persona")));
        const reset = el("button", "btn btn-link btn-sm p-0", t("resetToShared", "Use shared settings"));
        reset.type = "button";
        reset.addEventListener("click", () => {
            delete editing.overrides[questionId];
            const question = questions(baseForm).find((q) => q.question_id === questionId);
            window.applyConfigToCards?.({ response_config: { pages: [{ questions: [question] }] } });
            markOverrides();
        });
        tools.appendChild(reset);
        card.prepend(tools);
    });
}

async function startEditing(persona) {
    if (editing) return;
    if (!(await window.saveManualConfiguration?.())) return;
    try {
        await loadForm();
    } catch (error) {
        window.showPopup?.(error.message, "error");
        return;
    }
    editing = persona;
    editing.overrides = editing.overrides || {};
    const merged = JSON.parse(JSON.stringify(baseForm));
    questions(merged).forEach((question) => {
        const override = editing.overrides[question.question_id];
        if (override) question.answer_config = { ...question.answer_config, ...override };
    });
    window.renderQuestionsStep2?.(window.formQuestionsData);
    window.applyConfigToCards?.(merged);
    markOverrides();
    byId("persona-editing-name").textContent = `${t("editingPersona", "Editing answers for")} ${persona.name}`;
    byId("persona-editing-banner").classList.remove("d-none");
    byId("persona-editing-banner").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function stopEditing(save) {
    if (!editing) return;
    if (save) {
        const edits = window.collectManualEdits?.() || {};
        questions(baseForm).forEach((question) => {
            const edit = edits[question.question_id];
            if (!edit) return;
            const override = {
                fill_percentage: edit.fill_percentage,
                answers: edit.answers?.length ? edit.answers : null,
                options: (edit.options || []).length
                    ? edit.options.map((option) => ({ text: option.text, percentage: option.percentage }))
                    : null,
            };
            if (sameSettings(override, question.answer_config)) {
                delete editing.overrides[question.question_id];
            } else {
                editing.overrides[question.question_id] = override;
            }
        });
    }
    const persona = editing;
    editing = null;
    byId("persona-editing-banner").classList.add("d-none");
    window.renderQuestionsStep2?.(window.formQuestionsData);
    window.applyConfigToCards?.(baseForm);
    if (save) {
        if (!(await savePersonas())) {
            editing = persona;  // keep the edits on screen to fix and retry
            byId("persona-editing-banner").classList.remove("d-none");
        }
    } else {
        await openPersonas();
    }
}

window.isEditingPersona = () => editing !== null;

// ------------------------------------------------------------ autopilot

let proposal = null;

function describe(settings) {
    if (!settings) return "";
    if (settings.options) return settings.options.map((option) => `${option.text} ${option.percentage}%`).join(", ");
    if (settings.answers) return settings.answers.slice(0, 5).join(" · ");
    if (settings.fill_percentage !== undefined && settings.fill_percentage !== null) return `${settings.fill_percentage}%`;
    return "";
}

async function generateProposal() {
    const audience = byId("autopilot-audience").value.trim();
    const error = byId("autopilot-error");
    error.classList.add("d-none");
    if (!audience) {
        window.showPopup?.(t("describeAudience", "Describe who answers the form first."), "warning");
        return;
    }
    if (!(await window.saveManualConfiguration?.())) return;
    const apiKey = await window.getOrAskGeminiKey?.();
    if (!apiKey) return;
    const button = byId("autopilot-generate");
    button.disabled = true;
    try {
        proposal = await readJson(await fetch("/ai/propose_config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                form_id: window.currentFormId,
                api_key: apiKey,
                audience,
                want_personas: byId("autopilot-personas").checked,
            }),
        }));
        renderProposal();
    } catch (err) {
        error.querySelector("span").textContent = err.message;
        error.classList.remove("d-none");
        byId("autopilot-result").classList.add("d-none");
    } finally {
        button.disabled = false;
    }
}

function renderProposal() {
    byId("autopilot-warnings").replaceChildren(...proposal.warnings.map((warning) => el("li", null, warning)));
    byId("autopilot-rows").replaceChildren(...proposal.questions.map((item) => {
        const row = el("tr");
        const pick = el("td");
        const box = el("input", "form-check-input autopilot-pick");
        box.type = "checkbox";
        box.checked = true;
        box.dataset.questionId = item.question_id;
        box.setAttribute("aria-label", item.text);
        pick.appendChild(box);
        row.append(pick, el("td", "small", item.text), el("td", "small text-muted", describe(item.before)),
            el("td", "small", describe(item.after)));
        return row;
    }));
    const box = byId("autopilot-personas-box");
    box.classList.toggle("d-none", !proposal.personas);
    byId("autopilot-persona-list").replaceChildren(...(proposal.personas || []).map((persona) =>
        el("li", null, `${persona.name} — ${persona.weight}%${persona.description ? `: ${persona.description}` : ""}`)));
    byId("autopilot-result").classList.remove("d-none");
}

async function applyProposal() {
    const selected = Array.from(document.querySelectorAll(".autopilot-pick:checked")).map((box) => box.dataset.questionId);
    const edits = Object.fromEntries(selected.map((id) => [id, proposal.edits[id]]));
    const applyPersonas = proposal.personas && byId("autopilot-apply-personas").checked;
    try {
        if (selected.length) {
            await readJson(await fetch("/save_edit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ form_id: window.currentFormId, edits }),
            }));
        }
        if (applyPersonas) {
            await readJson(await fetch(`/forms/${encodeURIComponent(window.currentFormId)}/personas`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ personas: proposal.personas }),
            }));
        }
        const form = await loadForm();
        window.renderQuestionsStep2?.(window.formQuestionsData);
        window.applyConfigToCards?.(form);
        if (!byId("personas-panel").classList.contains("d-none")) await openPersonas();
        window.showPopup?.(t("proposalApplied", "Proposal applied. Simulate the batch to check it."), "success");
    } catch (error) {
        window.showPopup?.(error.message, "error");
    }
}

// --------------------------------------------------------------- wiring

byId("personas-toggle")?.addEventListener("click", (event) => {
    if (togglePanel("personas-panel", event.currentTarget)) openPersonas();
});
byId("autopilot-toggle")?.addEventListener("click", (event) => togglePanel("autopilot-panel", event.currentTarget));
byId("persona-add")?.addEventListener("click", () => {
    if (personas.length >= MAX_PERSONAS) return;
    personas.push({ name: `${t("persona", "Persona")} ${personas.length + 1}`, weight: 0, overrides: {} });
    renderPersonas();
});
byId("persona-save")?.addEventListener("click", savePersonas);
byId("persona-edit-done")?.addEventListener("click", () => stopEditing(true));
byId("persona-edit-cancel")?.addEventListener("click", () => stopEditing(false));
byId("autopilot-generate")?.addEventListener("click", generateProposal);
byId("autopilot-apply")?.addEventListener("click", applyProposal);
byId("autopilot-all")?.addEventListener("change", (event) => {
    document.querySelectorAll(".autopilot-pick").forEach((box) => { box.checked = event.target.checked; });
});
