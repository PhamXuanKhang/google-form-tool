import { setCurrentFormId } from './main.js';

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

async function extractFromUrl(url) {
    const container = document.getElementById('form-preview-container');
    showSpinner();

    try {
        const extractRes = await fetch('/form_filling/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ form_url: url })
        });
        const extractData = await readJsonResponse(extractRes);

        if (!extractRes.ok || extractData.error) {
            const message = extractData.error || t("failedToExtractFormData", "Failed to extract form data.");
            showPopup(message);
            showPreviewError(container, message);
            return;
        }

        const previewRes = await fetch('/form_filling/preview');
        const data = await readJsonResponse(previewRes);

        if (!previewRes.ok || data.error) {
            const message = data.error || t("failedToLoadFormPreview", "Failed to load form preview.");
            showPopup(message);
            showPreviewError(container, message);
            return;
        }

        container.innerHTML = renderFormPreview(data);
        container.classList.add("preview-loaded");

        window.formQuestionsData = data;
        
        if (data.id) {
            setCurrentFormId(data.id);
        }
    } catch (error) {
        console.error('Error during extraction:', error);
        const message = t("failedToExtractForm", "Failed to extract form. Please check the URL and try again.");
        showPopup(message);
        showPreviewError(container, message);
    } finally {
        hideSpinner();
    }
}


async function readJsonResponse(response) {
    try {
        return await response.json();
    } catch (error) {
        console.error('Failed to parse JSON response:', error);
        return {};
    }
}

function showPreviewError(container, message) {
    container.innerHTML = "";
    const errorMessage = document.createElement("p");
    errorMessage.className = "text-warning";
    errorMessage.textContent = `⚠️ ${message}`;
    container.appendChild(errorMessage);
    container.classList.remove("preview-loaded");
}


function renderFormPreview(form) {
    let html = `
    <div class="card bg-light p-3">
        <div class="d-flex align-items-center mb-2">
            <div class="rounded-circle bg-info d-flex align-items-center justify-content-center me-2" style="width: 32px; height: 32px;">
                <i class="fas fa-file-alt text-dark"></i>
            </div>
            <div>
                <h5 class="text-dark mb-0">${form.title}</h5>
                <small class="text-muted">${form.description}</small>
            </div>
        </div>
        <div>
    `;

    if (form.response_config && form.response_config.pages) {
        form.response_config.pages.forEach((page, pageIndex) => {
            html += `
            <div class="page-block">
                <h6 class="text-primary mb-3 bold">${t("page", "Page")} ${pageIndex + 1}</h6>
            `;

            if (page.questions) {
                page.questions.forEach((q, qIndex) => {
                    html += `
                    <div class="question-block">
                        <div class="question-title">Q${qIndex + 1}: ${q.text}</div>
                        <div class="question-type">${t("type", "Type")}: ${q.type}</div>
                    `;

                    if (
                        q.answer_config &&
                        ["multiple_choice", "dropdown", "checkbox", "linear_scale", "rank"].includes(q.type) &&
                        q.answer_config.options
                    ) {
                        html += `<div class="option-scroll-wrapper"><div class="option-scroll-inner">
                        `;
                        q.answer_config.options.forEach((opt) => {
                            html += `<div class="option-card">${opt.text}</div>`;
                        });
                        html += `</div></div>
                        `;
                    }

                    html += `</div>`; // close question
                });
            } else {
                html += `<p class='text-muted'>${t("noQuestionsOnThisPage", "No questions on this page.")}</p>`;
            }

            html += `</div>`; // close page
        });
    } else {
        html += `<p class='text-muted'>${t("noPageQuestionStructure", "No page/question structure found.")}</p>`;
    }

    html += "</div></div>";
    return html;
}

function showSpinner() {
  document.getElementById("spinner").style.display = "flex";
}
function hideSpinner() {
  document.getElementById("spinner").style.display = "none";
}

function showPopup(message, type = "info") {
    const toastMessage = document.getElementById("toast-message");
    if (toastMessage) {
        toastMessage.textContent = message;
        const toastElement = document.getElementById("statusToast") || document.getElementById("warningToast");
        if (toastElement) {
            toastElement.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-info', 'text-bg-warning');
            switch (type) {
                case "success":
                    toastElement.classList.add('text-bg-success');
                    break;
                case "error":
                    toastElement.classList.add('text-bg-danger');
                    break;
                case "warning":
                    toastElement.classList.add('text-bg-warning');
                    break;
                default:
                    toastElement.classList.add('text-bg-info');
            }
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
        }
    } else {
        alert(message);
    }
}

window.showPopup = showPopup;

export { extractFromUrl, showSpinner, hideSpinner, showPopup };
