/**
 * Open pop up to show form information
 * TODO: Fix the field to suitable for db
 * @param {string} formId
 */
function openFormModal(formId) {
    const forms = window.recentForms || [];
    const selected = forms.find(f => f.id == formId);
    if (selected) {
        window.selected_form = selected;

        // Load data into modal
        document.getElementById('formModalLabel').textContent = selected.title || '';
        document.querySelector('#formModal .modal-body').innerHTML = `
            <p>${selected.description || ''}</p>
            <p>
                <a href="${selected.url || ''}" target="_blank" class="text-decoration-none text-primary" style="cursor: pointer;">
                    <i class="fas fa-link me-1"></i>${selected.url || ''}
                </a>
            </p>
            <p><i class="fas fa-paper-plane"></i> ${selected.submissions || ''} submissions</p>
            <p><i class="fas fa-clock"></i> Last used: ${selected.timestamp || ''}</p>
        `;
        document.querySelector('#formModal .modal-footer a').href = `/fill_form?form_url=${encodeURIComponent(selected.url)}`;

        const modal = new bootstrap.Modal(document.getElementById('formModal'));
        modal.show();
    }
}
