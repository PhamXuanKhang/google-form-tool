/**
 * Open pop up to show form information
 * 
 * @param {string} formId
 */
function openFormModal(formId) {
    const forms = window.recentForms || [];
    const selected = forms.find(f => f.id == formId);
    const i18n = window.i18n || {};
    if (selected) {
        window.selected_form = selected;

        document.getElementById('formModalLabel').textContent = selected.title || '';
        document.querySelector('#formModal .modal-body').innerHTML = `
            <p>${escapeHtml(selected.description || '')}</p>
            <p>
                <a href="${escapeHtml(selected.url || '')}" target="_blank" class="text-decoration-none text-primary" style="cursor: pointer;">
                    <i class="fas fa-link me-1"></i>${escapeHtml(selected.url || '')}
                </a>
            </p>
            <p><i class="fas fa-paper-plane"></i> ${selected.total_fill || 0} ${escapeHtml(i18n.submissions || 'submissions')}</p>
            <p><i class="fas fa-clock"></i> ${escapeHtml(i18n.lastUsed || 'Last used')}: ${escapeHtml(selected.last_used || i18n.never || 'Never')}</p>
            <hr>
            <h6 class="fw-bold">${escapeHtml(i18n.submissionHistory || 'Submission History')}</h6>
            <div id="submissionHistoryContainer" class="text-muted">${escapeHtml(i18n.loadingSubmissionHistory || 'Loading submission history...')}</div>
        `;

        const deleteBtn = document.getElementById('deleteFormBtn');
        deleteBtn.href = '#';
        deleteBtn.onclick = () => deleteSelectedForm(selected.url);
        document.getElementById('fillFormBtn').href = `/form_filling?form_url=${encodeURIComponent(selected.url)}`;

        const exportBtn = document.getElementById('exportHistoryBtn');
        exportBtn.href = `/export_history/${selected.id}`;
        exportBtn.setAttribute('download', `${selected.title || 'form'}_history.csv`);

        const modal = new bootstrap.Modal(document.getElementById('formModal'));
        modal.show();
        loadSubmissionHistory(selected.id);
    }
}

async function deleteSelectedForm(formUrl) {
    try {
        const response = await fetch('/forms/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ form_url: formUrl }),
        });
        const data = await readJsonResponse(response);

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Could not delete form.');
        }

        window.location.reload();
    } catch (error) {
        alert(error.message);
    }
}

async function loadSubmissionHistory(formId) {
    const container = document.getElementById('submissionHistoryContainer');
    if (!container) return;

    try {
        const response = await fetch(`/submission_history/${encodeURIComponent(formId)}`);
        const data = await readJsonResponse(response);

        if (!response.ok || data.error) {
            throw new Error(data.error || window.i18n?.couldNotLoadSubmissionHistory || "Could not load submission history.");
        }

        container.innerHTML = renderSubmissionHistory(data.submissions || []);
    } catch (error) {
        container.innerHTML = `<p class="text-danger mb-0">${escapeHtml(error.message)}</p>`;
    }
}

async function readJsonResponse(response) {
    try {
        return await response.json();
    } catch (error) {
        console.error('Failed to parse history response:', error);
        return {};
    }
}

function renderSubmissionHistory(submissions) {
    if (!submissions.length) {
        return `<p class="text-muted mb-0">${escapeHtml(window.i18n?.noSubmissionHistoryYet || 'No submission history yet.')}</p>`;
    }

    const rows = submissions.map((submission) => {
        const successRate = Number.isFinite(Number(submission.success_rate))
            ? `${Number(submission.success_rate).toFixed(1)}%`
            : "";

        return `
            <tr>
                <td><code>${escapeHtml(submission.submission_id || '')}</code></td>
                <td>${escapeHtml(String(submission.num_submission ?? ''))}</td>
                <td>${escapeHtml(String(submission.concurrent_thread ?? ''))}</td>
                <td>${escapeHtml(String(submission.time_used ?? ''))}s</td>
                <td>${successRate}</td>
                <td>${escapeHtml(submission.network_status || '')}</td>
            </tr>
        `;
    }).join('');

    return `
        <div class="table-responsive">
            <table class="table table-sm align-middle mb-0">
                <thead>
                    <tr>
                        <th>${escapeHtml(window.i18n?.submissionId || 'Submission ID')}</th>
                        <th>${escapeHtml(window.i18n?.submissions || 'Submissions')}</th>
                        <th>${escapeHtml(window.i18n?.threads || 'Threads')}</th>
                        <th>${escapeHtml(window.i18n?.timeUsed || 'Time used')}</th>
                        <th>${escapeHtml(window.i18n?.successRate || 'Success rate')}</th>
                        <th>${escapeHtml(window.i18n?.networkStatus || 'Network/status')}</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[char]));
}
