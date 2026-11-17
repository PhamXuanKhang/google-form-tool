/**
 * Template menu of the Configure Answers step: save the current answer
 * settings as a named template, export or import a template file, and apply a
 * saved template. Applying always shows a preview first. Template and form
 * text is written with textContent only.
 */

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

const byId = (id) => document.getElementById(id);
let pendingImport = null;  // body for the apply call after the preview

async function readJson(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) throw new Error(data.error || t("templateFailed", "Template action failed."));
    return data;
}

/** Templates are built from the saved form, so save the cards first. */
async function saveCurrentEdits() {
    if (!window.currentFormId) {
        window.showPopup?.(t("pleaseExtractFormFirst", "Please extract a form first."), "warning");
        return false;
    }
    return (await window.saveManualConfiguration?.()) !== false;
}

async function saveTemplate() {
    if (!(await saveCurrentEdits())) return;
    const name = window.prompt(t("templateNamePrompt", "Template name:"));
    if (!name || !name.trim()) return;
    try {
        await readJson(await fetch("/templates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ form_id: window.currentFormId, name: name.trim() }),
        }));
        window.showPopup?.(t("templateSaved", "Template saved."), "success");
        loadSavedTemplates();
    } catch (error) {
        window.showPopup?.(error.message, "error");
    }
}

async function exportTemplate() {
    if (!(await saveCurrentEdits())) return;
    const link = document.createElement("a");
    link.href = `/forms/${encodeURIComponent(window.currentFormId)}/config/export`;
    link.download = "";
    link.click();
}

function listSection(title, items, describe) {
    const section = document.createElement("div");
    section.className = "mb-3";
    const heading = document.createElement("h6");
    heading.className = "fw-semibold";
    heading.textContent = `${title} (${items.length})`;
    section.appendChild(heading);
    if (items.length) {
        const list = document.createElement("ul");
        list.className = "small mb-0";
        items.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = describe(item);
            list.appendChild(li);
        });
        section.appendChild(list);
    }
    return section;
}

function showPreview(preview, applyBody) {
    pendingImport = applyBody;
    byId("template-preview-summary").textContent = preview.same_structure
        ? t("templateSameStructure", "The template was made from a form with the same structure.")
        : t("templateDifferentStructure", "The template comes from a form with a different structure. Only matching questions will change.");
    const reasons = {
        not_found: t("templateReasonNotFound", "no matching question"),
        options_differ: t("templateReasonOptions", "options differ"),
    };
    byId("template-preview-lists").replaceChildren(
        listSection(t("templateMatched", "Will be updated"), preview.matched, (item) => item.text),
        listSection(t("templateUnmatched", "Not applied"), preview.unmatched,
            (item) => `${item.text} — ${reasons[item.reason] || item.reason}`),
        listSection(t("templateMissing", "Not in the template (unchanged)"), preview.missing, (item) => item.text),
    );
    byId("template-apply").disabled = !preview.matched.length;
    bootstrap.Modal.getOrCreateInstance(byId("template-preview-modal")).show();
}

async function previewImport(body, isFile) {
    if (!(await saveCurrentEdits())) return;
    const url = `/forms/${encodeURIComponent(window.currentFormId)}/config/import`;
    try {
        const response = isFile
            ? await fetch(url, { method: "POST", body })
            : await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await readJson(response);
        showPreview(data.preview, isFile ? { file: body.get("file") } : body);
    } catch (error) {
        window.showPopup?.(error.message, "error");
    }
}

async function applyPending() {
    if (!pendingImport) return;
    const url = `/forms/${encodeURIComponent(window.currentFormId)}/config/import`;
    try {
        let response;
        if (pendingImport.file) {
            const form = new FormData();
            form.append("file", pendingImport.file);
            form.append("apply", "true");
            response = await fetch(url, { method: "POST", body: form });
        } else {
            response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...pendingImport, apply: true }),
            });
        }
        await readJson(response);
        const formResponse = await readJson(await fetch(`/forms/${encodeURIComponent(window.currentFormId)}`));
        window.renderQuestionsStep2?.(window.formQuestionsData);
        window.applyConfigToCards?.(formResponse.form);
        bootstrap.Modal.getOrCreateInstance(byId("template-preview-modal")).hide();
        window.showPopup?.(t("templateApplied", "Template applied."), "success");
    } catch (error) {
        window.showPopup?.(error.message, "error");
    } finally {
        pendingImport = null;
    }
}

async function loadSavedTemplates() {
    const menu = byId("template-menu-list");
    if (!menu) return;
    menu.querySelectorAll(".saved-template").forEach((item) => item.remove());
    try {
        const data = await readJson(await fetch("/templates"));
        byId("template-saved-placeholder").classList.toggle("d-none", data.templates.length > 0);
        data.templates.forEach((template) => {
            const li = document.createElement("li");
            li.className = "saved-template";
            const button = document.createElement("button");
            button.type = "button";
            button.className = "dropdown-item";
            button.textContent = template.name;
            button.addEventListener("click", () => previewImport({ template_id: template.template_id }, false));
            li.appendChild(button);
            menu.appendChild(li);
        });
    } catch (error) {
        console.debug("Could not load templates:", error);
    }
}

byId("template-save")?.addEventListener("click", saveTemplate);
byId("template-export")?.addEventListener("click", exportTemplate);
byId("template-import")?.addEventListener("click", () => byId("template-file").click());
byId("template-file")?.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    previewImport(body, true);
});
byId("template-apply")?.addEventListener("click", applyPending);
byId("template-menu")?.addEventListener("show.bs.dropdown", loadSavedTemplates);
