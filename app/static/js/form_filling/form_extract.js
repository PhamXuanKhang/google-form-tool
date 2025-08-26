async function extractFromUrl(url) {
    const container = document.getElementById('form-preview-container');
    showSpinner();

    try {
        await fetch('/form_filling/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ form_url: url })
        });

        const previewRes = await fetch('/form_filling/preview');
        const data = await previewRes.json();

        if (data.error) {
            showPopup(data.error);
            container.classList.remove("preview-loaded");
        } else {
            container.innerHTML = renderFormPreview(data);
            container.classList.add("preview-loaded");

            window.formQuestionsData = data;
        }
    } catch (error) {
        showPopup("❌ Failed to extract form. Please check the URL and try again.");
        container.classList.remove("preview-loaded");
    } finally {
        hideSpinner();
    }

    const previewRes = await fetch('/form_filling/preview');
    const data = await previewRes.json();

    if (data.error) {
        container.innerHTML = `<p class="text-warning">⚠️ ${data.error}</p>`;
        return;
    }


    container.innerHTML = renderFormPreview(data);
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
                <h6 class="text-primary mb-3 bold">Page ${pageIndex + 1}</h6>
            `;

            if (page.questions) {
                page.questions.forEach((q, qIndex) => {
                    html += `
                    <div class="question-block">
                        <div class="question-title">Q${qIndex + 1}: ${q.text}</div>
                        <div class="question-type">Type: ${q.type}</div>
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
                html += "<p class='text-muted'>No questions on this page.</p>";
            }

            html += `</div>`; // close page
        });
    } else {
        html += "<p class='text-muted'>No page/question structure found.</p>";
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