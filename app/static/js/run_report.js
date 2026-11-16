/**
 * Run report page: outcome metrics, actual versus target per question,
 * failure reasons, paged responses, and retry of failed responses.
 * Every value that comes from a form or a run is written with textContent.
 */
(function () {
    const root = document.getElementById('run-report');
    if (!root) return;
    const runId = root.dataset.runId;
    const i18n = window.i18n || {};
    const PAGE_SIZE = 25;
    let rowsOffset = 0;
    let rowsTotal = 0;
    let questionTitles = {};

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function statusLabel(status) {
        return (i18n.statuses && i18n.statuses[status]) || status || '';
    }

    function statusPill(status) {
        const pill = el('span', `status-pill status-${status}`, statusLabel(status));
        return pill;
    }

    function formatDuration(seconds) {
        if (seconds === null || seconds === undefined) return '–';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return h ? `${h}h ${m}m` : m ? `${m}m ${s}s` : `${s}s`;
    }

    function formatTime(value) {
        if (!value) return '';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }

    function answerText(value) {
        return Array.isArray(value) ? value.join(', ') : String(value);
    }

    async function getJson(url, options) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.error) {
            throw new Error(data.error || i18n.couldNotLoadRun || 'Could not load this run.');
        }
        return data;
    }

    function showError(message) {
        document.getElementById('report-loading').classList.add('d-none');
        const box = document.getElementById('report-error');
        box.querySelector('span').textContent = message;
        box.classList.remove('d-none');
    }

    function renderHeader(data) {
        const run = data.run;
        if (data.form_title) {
            document.getElementById('report-title').textContent = data.form_title;
        }
        const status = document.getElementById('report-status');
        status.replaceWith(statusPill(run.status));
        const parts = [
            formatTime(run.created_at),
            (i18n.modes && i18n.modes[run.mode]) || run.mode,
            `${i18n.seed || 'Seed'} ${run.seed}`,
        ];
        if (run.retry_of) parts.push(i18n.retryOf || 'Retry of an earlier run');
        if (run.schedule) {
            parts.push(`${i18n.scheduledOver || 'Spread over'} ${Math.round(run.schedule.window_seconds / 60)} ${i18n.minutes || 'minutes'}`);
        }
        document.getElementById('report-meta').textContent = ' · ' + parts.join(' · ');
        const resume = document.getElementById('resume-run');
        resume.classList.toggle('d-none', !(run.schedule && ['paused', 'interrupted'].includes(run.status)));
    }

    function renderMetrics(summary) {
        document.getElementById('m-total').textContent = summary.total;
        document.getElementById('m-success').textContent = summary.success;
        document.getElementById('m-failed').textContent = summary.failed;
        document.getElementById('m-unknown').textContent = summary.unknown;
        document.getElementById('m-rate').textContent = `${summary.success_rate}%`;
        document.getElementById('m-duration').textContent = formatDuration(summary.duration_seconds);
        const canRetry = summary.failed > 0 || summary.unknown > 0;
        document.getElementById('retry-card').classList.toggle('d-none', !canRetry);
    }

    function renderQuestions(summary) {
        const container = document.getElementById('question-charts');
        container.replaceChildren();
        questionTitles = {};
        summary.questions.forEach((question) => { questionTitles[question.question_id] = question.text; });

        const choice = summary.questions.filter((question) => question.kind === 'choice');
        if (!choice.length) {
            container.appendChild(el('p', 'text-muted', i18n.noChoiceQuestions || 'No choice questions to compare.'));
        }
        choice.forEach((question) => {
            const card = el('div', 'card chart-card');
            const body = el('div', 'card-body');
            body.appendChild(el('h3', 'chart-title', question.text));
            if (question.blank) {
                body.appendChild(el('p', 'small text-muted mb-2', `${i18n.blank || 'Blank'}: ${question.blank_rate}%`));
            }
            const holder = el('div', 'chart-holder');
            const canvas = document.createElement('canvas');
            holder.appendChild(canvas);
            body.appendChild(holder);
            card.appendChild(body);
            container.appendChild(card);
            window.GFCharts.targetVsActual(canvas, question.options, {
                target: i18n.target || 'Target', actual: i18n.actual || 'Actual',
            });
        });

        summary.questions.filter((question) => question.kind === 'text').forEach((question) => {
            const card = el('div', 'card chart-card');
            const body = el('div', 'card-body');
            body.appendChild(el('h3', 'chart-title', question.text));
            body.appendChild(el('p', 'small text-muted mb-2', `${question.distinct} ${i18n.distinctValues || 'distinct values'}`));
            const list = el('ul', 'sample-list');
            question.samples.forEach((sample) => list.appendChild(el('li', null, sample)));
            body.appendChild(list);
            card.appendChild(body);
            container.appendChild(card);
        });
    }

    function renderFailures(summary) {
        const card = document.getElementById('failure-card');
        const list = document.getElementById('failure-list');
        list.replaceChildren();
        card.classList.toggle('d-none', !summary.failure_reasons.length);
        summary.failure_reasons.forEach((reason) => {
            const item = el('li', 'd-flex justify-content-between py-1 border-bottom');
            item.appendChild(el('code', null, reason.reason));
            item.appendChild(el('span', 'fw-semibold', reason.count));
            list.appendChild(item);
        });
    }

    async function loadRows() {
        const status = document.getElementById('rows-filter').value;
        const params = new URLSearchParams({ offset: rowsOffset, limit: PAGE_SIZE });
        if (status) params.set('status', status);
        const body = document.getElementById('rows-body');
        try {
            const data = await getJson(`/runs/${encodeURIComponent(runId)}/rows?${params}`);
            rowsTotal = data.total;
            body.replaceChildren();
            if (!data.rows.length) {
                const tr = el('tr');
                const td = el('td', 'text-muted text-center py-4', i18n.noRows || 'No responses match this filter.');
                td.colSpan = 4;
                tr.appendChild(td);
                body.appendChild(tr);
            }
            data.rows.forEach((row) => {
                const tr = el('tr');
                tr.appendChild(el('td', 'text-muted', row.index + 1));
                const statusCell = el('td');
                statusCell.appendChild(statusPill(row.status));
                if (row.error) statusCell.appendChild(el('div', 'small text-muted', row.error));
                tr.appendChild(statusCell);
                tr.appendChild(el('td', 'small text-nowrap', formatTime(row.finished_at)));
                const answers = el('td', 'answers-cell');
                Object.entries(row.answers || {}).forEach(([key, value]) => {
                    const line = el('div', 'answer-line');
                    line.appendChild(el('span', 'answer-key', questionTitles[key] || key));
                    line.appendChild(el('span', null, answerText(value)));
                    answers.appendChild(line);
                });
                tr.appendChild(answers);
                body.appendChild(tr);
            });
            const from = data.rows.length ? rowsOffset + 1 : 0;
            const to = rowsOffset + data.rows.length;
            document.getElementById('rows-range').textContent = (i18n.rowsRange || '{from}–{to} of {total}')
                .replace('{from}', from).replace('{to}', to).replace('{total}', rowsTotal);
            document.getElementById('rows-prev').disabled = rowsOffset === 0;
            document.getElementById('rows-next').disabled = to >= rowsTotal;
        } catch (error) {
            window.showToast(error.message, 'error');
        }
    }

    async function retry() {
        const button = document.getElementById('retry-button');
        button.disabled = true;
        try {
            const data = await getJson(`/runs/${encodeURIComponent(runId)}/retry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ include_unknown: document.getElementById('retry-include-unknown').checked }),
            });
            window.showToast(i18n.retryStarted || 'Started a new run for the failed responses.', 'success');
            window.location.href = `/runs/${encodeURIComponent(data.run_id)}/view`;
        } catch (error) {
            window.showToast(error.message || i18n.retryFailed || 'Could not start the retry.', 'error');
            button.disabled = false;
        }
    }

    async function load() {
        try {
            const data = await getJson(`/runs/${encodeURIComponent(runId)}`);
            renderHeader(data);
            renderMetrics(data.summary);
            renderQuestions(data.summary);
            renderFailures(data.summary);
            document.getElementById('report-loading').classList.add('d-none');
            document.getElementById('report-body').classList.remove('d-none');
            await loadRows();
        } catch (error) {
            showError(error.message);
        }
    }

    document.getElementById('rows-filter').addEventListener('change', () => { rowsOffset = 0; loadRows(); });
    document.getElementById('rows-prev').addEventListener('click', () => { rowsOffset = Math.max(0, rowsOffset - PAGE_SIZE); loadRows(); });
    document.getElementById('rows-next').addEventListener('click', () => { rowsOffset += PAGE_SIZE; loadRows(); });
    document.getElementById('retry-button').addEventListener('click', retry);
    const resumeButton = document.getElementById('resume-run');
    resumeButton.addEventListener('click', async () => {
        resumeButton.disabled = true;
        try {
            await getJson(`/runs/${encodeURIComponent(runId)}/resume`, { method: 'POST' });
            window.showToast(i18n.resumed || 'Resumed.', 'success');
            load();
        } catch (error) {
            window.showToast(error.message, 'error');
        } finally {
            resumeButton.disabled = false;
        }
    });
    load();
})();
