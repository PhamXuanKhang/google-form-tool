/**
 * Batch preview: plans the batch on the server (POST /simulate) and shows
 * target versus simulated spread per choice question plus sample rows.
 * Nothing is sent to Google. Text from the form is set with textContent.
 */

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

let lastSeed = null;
let charts = [];

function byId(id) {
    return document.getElementById(id);
}

function showState(state) {
    byId('simulation-empty').classList.toggle('d-none', state !== 'empty');
    byId('simulation-loading').classList.toggle('d-none', state !== 'loading');
    byId('simulation-error').classList.toggle('d-none', state !== 'error');
    byId('simulation-result').classList.toggle('d-none', state !== 'result');
    const hasResult = state === 'result';
    byId('simulate-again-button').classList.toggle('d-none', !hasResult);
    byId('run-simulated-button').classList.toggle('d-none', !hasResult);
}

function cell(tag, text, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text === undefined || text === null ? '' : String(text);
    return node;
}

function answerText(value) {
    if (value === undefined || value === null) return '';
    return Array.isArray(value) ? value.join(', ') : String(value);
}

function renderCharts(questions) {
    charts.forEach((chart) => chart.destroy());
    charts = [];
    const container = byId('simulation-charts');
    container.replaceChildren();
    questions.filter((question) => question.kind === 'choice').forEach((question) => {
        const card = document.createElement('div');
        card.className = 'card chart-card';
        const body = document.createElement('div');
        body.className = 'card-body';
        body.appendChild(cell('h5', question.text, 'chart-title'));
        const holder = document.createElement('div');
        holder.className = 'chart-holder';
        const canvas = document.createElement('canvas');
        holder.appendChild(canvas);
        body.appendChild(holder);
        card.appendChild(body);
        container.appendChild(card);
        charts.push(window.GFCharts.targetVsActual(canvas, question.options, {
            target: t('target', 'Target'),
            actual: t('simulated', 'Simulated'),
        }));
    });
    if (!charts.length) {
        container.appendChild(cell('p', t('noChoiceQuestions', 'No choice questions to compare.'), 'text-muted small'));
    }
}

function renderSamples(questions, rows) {
    const head = byId('simulation-sample-head');
    const body = byId('simulation-sample-body');
    const headRow = document.createElement('tr');
    headRow.appendChild(cell('th', '#'));
    questions.forEach((question) => headRow.appendChild(cell('th', question.text)));
    head.replaceChildren(headRow);
    body.replaceChildren(...rows.map((row) => {
        const tr = document.createElement('tr');
        tr.appendChild(cell('td', row.index + 1, 'text-muted'));
        questions.forEach((question) => tr.appendChild(cell('td', answerText(row.answers[question.question_id]))));
        return tr;
    }));
}

async function simulate(seed) {
    const settings = window.getFormSettings?.();
    if (!settings?.form_id) {
        window.showPopup?.(t('pleaseExtractFormFirst', 'Please extract a form first.'), 'warning');
        return;
    }
    const body = {
        form_id: settings.form_id,
        num_submissions: settings.num_submissions,
        submission_mode: settings.submission_mode,
    };
    if (settings.upload_id) body.upload_id = settings.upload_id;
    if (Number.isInteger(seed)) body.seed = seed;

    showState('loading');
    try {
        const response = await fetch('/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.error) {
            throw new Error(data.error || t('simulationFailed', 'Could not simulate this batch.'));
        }
        lastSeed = data.seed;
        byId('simulation-meta').textContent = t('simulationMeta', '{total} responses · seed {seed}')
            .replace('{total}', data.total).replace('{seed}', data.seed);
        byId('simulation-warnings').textContent = (data.warnings || []).join(' ');
        renderCharts(data.questions);
        renderSamples(data.questions, data.sample_rows || []);
        showState('result');
    } catch (error) {
        byId('simulation-error').querySelector('span').textContent = error.message;
        showState('error');
    }
}

byId('simulate-button')?.addEventListener('click', () => simulate(lastSeed));
byId('simulate-again-button')?.addEventListener('click', () => simulate(null));
byId('run-simulated-button')?.addEventListener('click', () => {
    if (Number.isInteger(lastSeed)) window.startFormSubmission(lastSeed);
});
