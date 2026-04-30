/**
 * This module handles form submission automation.
 * It implements the Start, Stop, and Monitor functionality
 * for automatic form submissions.
 */

// Track submission state
let submissionActive = false;
let submissionInterval;
let currentSubmissionFormId = null;
let lastWarningMessage = null;
const DEFAULT_REFRESH_INTERVAL = 2000; // 2 seconds

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

/**
 * Start form submission automation
 * @param {object} settings - Submission settings object
 */
export async function startSubmission(settings) {
    if (submissionActive) {
        return;
    }

    currentSubmissionFormId = settings?.form_id || null;
    lastWarningMessage = null;

    if (!currentSubmissionFormId) {
        showStatusMessage(t("pleaseExtractFormFirst", "Please extract a form first."), 'warning');
        return false;
    }
    
    try {
        const response = await fetch('/start_submission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (data.error) {
            showStatusMessage(data.error, 'error');
            return false;
        }
        
        submissionActive = true;
        updateUIForActiveSubmission();
        
        // Start monitoring
        startStatusMonitoring();
        
        showStatusMessage(data.message || t("submissionStartedSuccessfully", "Submission started successfully"), 'success');
        if (Array.isArray(data.warnings) && data.warnings.length > 0) {
            showStatusMessage(data.warnings.join(" "), 'warning');
        }
        if (data.debug_prefill_sample) {
            console.info("Prefill sample (redacted):", data.debug_prefill_sample);
        }
        return true;
    } catch (error) {
        console.error('Error starting submission:', error);
        showStatusMessage(t("failedToStartSubmission", "Failed to start submission. Check console for details."), 'error');
        return false;
    }
}

/**
 * Stop the current form submission
 */
export async function stopSubmission() {
    if (!submissionActive) {
        return;
    }
    
    try {
        const response = await fetch('/stop_submission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        submissionActive = false;
        clearInterval(submissionInterval);
        
        updateUIForStoppedSubmission();
        
        showStatusMessage(data.message || t("submissionStopped", "Submission stopped"), 'info');
        return true;
    } catch (error) {
        console.error('Error stopping submission:', error);
        showStatusMessage(t("failedToStopSubmission", "Failed to stop submission. Check console for details."), 'error');
        return false;
    }
}

/**
 * Start monitoring the submission status
 */
function startStatusMonitoring() {
    // Clear any existing interval
    if (submissionInterval) {
        clearInterval(submissionInterval);
    }
    
    // Create new interval for status updates
    submissionInterval = setInterval(async () => {
        await updateSubmissionStatus();
    }, DEFAULT_REFRESH_INTERVAL);
    
    // Get initial status immediately
    updateSubmissionStatus();
}

/**
 * Fetch and update the submission status
 */
async function updateSubmissionStatus() {
    if (!currentSubmissionFormId) {
        showStatusMessage(t("pleaseExtractFormFirst", "Please extract a form first."), 'warning');
        return;
    }

    try {
        const response = await fetch(`/submission_status?form_id=${encodeURIComponent(currentSubmissionFormId)}`);
        const statusData = await response.json();

        if (statusData.active_submissions) {
            showStatusMessage(t("noActiveSubmissionForThisForm", "No active submission for this form."), 'info');
            stopStatusMonitoring();
            return;
        }

        if (statusData.message && !statusData.running && !statusData.total) {
            showStatusMessage(statusData.message, 'info');
            stopStatusMonitoring();
            return;
        }
        
        // Update UI with status data
        updateStatusDisplay(statusData);
        await updateSystemResources();
        
        // If submission is no longer running, stop monitoring
        if (!statusData.running) {
            submissionActive = false;
            clearInterval(submissionInterval);
            updateUIForStoppedSubmission();
        }
    } catch (error) {
        console.error('Error updating submission status:', error);
        // Don't stop monitoring on error - it might be temporary
    }
}

/**
 * Update UI elements with submission status data
 * @param {object} statusData - The status data from the server
 */
function updateStatusDisplay(statusData) {
    if (!isSingleStatusShape(statusData)) {
        console.warn('Unexpected submission status shape:', statusData);
        showStatusMessage(t("noActiveSubmissionForThisForm", "No active submission for this form."), 'info');
        stopStatusMonitoring();
        return;
    }

    // Find DOM elements to update
    const progressElement = document.getElementById('submission-progress');
    const successRateElement = document.getElementById('success-rate');
    const completedElement = document.getElementById('completed-count');
    const totalElement = document.getElementById('total-count');
    const timeElement = document.getElementById('elapsed-time');
    
    if (!progressElement || !successRateElement || !completedElement || !totalElement || !timeElement) {
        console.warn('Status display elements not found in DOM');
        return;
    }
    
    // Update elements with data
    if (statusData.total > 0) {
        const progressPercent = Math.round((statusData.completed / statusData.total) * 100);
        progressElement.style.width = `${progressPercent}%`;
        progressElement.setAttribute('aria-valuenow', progressPercent);
        progressElement.textContent = `${progressPercent}%`;
    }
    
    successRateElement.textContent = `${statusData.success_rate?.toFixed(1) || 0}%`;
    completedElement.textContent = statusData.completed || 0;
    totalElement.textContent = statusData.total || 0;
    
    if (statusData.elapsed_time) {
        timeElement.textContent = formatTime(statusData.elapsed_time);
    }

    if (statusData.warning && statusData.warning !== lastWarningMessage) {
        lastWarningMessage = statusData.warning;
        showStatusMessage(statusData.warning, 'warning');
    }
    
    // Update charts if they exist
    updateCharts(statusData);
}

function stopStatusMonitoring() {
    submissionActive = false;
    if (submissionInterval) {
        clearInterval(submissionInterval);
        submissionInterval = null;
    }
    updateUIForStoppedSubmission();
}

function isSingleStatusShape(statusData) {
    return statusData &&
        !statusData.active_submissions &&
        typeof statusData.running === 'boolean' &&
        Number.isFinite(Number(statusData.total)) &&
        Number.isFinite(Number(statusData.completed)) &&
        Number.isFinite(Number(statusData.success_rate));
}

/**
 * Update charts with the latest data
 * @param {object} statusData - The status data from the server
 */
function updateCharts(statusData) {
    // This assumes you have initialized charts elsewhere
    if (window.submissionChart) {
        const pending = Math.max((statusData.total || 0) - (statusData.completed || 0), 0);
        // Update submission progress chart
        window.submissionChart.data.datasets[0].data = [
            statusData.success || 0,
            statusData.failed || 0,
            pending
        ];
        window.submissionChart.update();
    }
    
    // Update other charts as needed
}

async function updateSystemResources() {
    try {
        const response = await fetch('/system_status');
        if (!response.ok) {
            console.warn('System status request failed:', response.status);
            return;
        }

        const resourceData = await response.json();
        updateResourceDisplay(resourceData);
    } catch (error) {
        console.warn('Error updating system resources:', error);
    }
}

function updateResourceDisplay(resourceData) {
    const cpuValue = normalizePercent(
        resourceData?.cpu?.system_cpu ?? resourceData?.cpu?.process_cpu ?? 0
    );
    const ramValue = normalizePercent(resourceData?.memory?.memory_percent ?? 0);

    const cpuElement = document.getElementById('resource-cpu-current');
    const ramElement = document.getElementById('resource-ram-current');
    if (cpuElement) {
        cpuElement.textContent = `CPU: ${cpuValue.toFixed(1)}%`;
    }
    if (ramElement) {
        ramElement.textContent = `RAM: ${ramValue.toFixed(1)}%`;
    }

    if (!window.resourceChart) {
        return;
    }

    const now = new Date();
    const label = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const labels = window.resourceChart.data.labels;
    const cpuData = window.resourceChart.data.datasets[0].data;
    const ramData = window.resourceChart.data.datasets[1].data;

    labels.push(label);
    cpuData.push(cpuValue);
    ramData.push(ramValue);

    while (labels.length > 10) labels.shift();
    while (cpuData.length > 10) cpuData.shift();
    while (ramData.length > 10) ramData.shift();

    window.resourceChart.update();
}

function normalizePercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(100, number));
}

/**
 * Update UI for active submission
 */
function updateUIForActiveSubmission() {
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    
    if (startButton) {
        startButton.classList.add('d-none');
    }
    
    if (stopButton) {
        stopButton.classList.remove('d-none');
    }
    
    // Additional UI updates for active state
    document.querySelectorAll('.submission-controls input, .submission-controls select').forEach(el => {
        el.disabled = true;
    });
}

/**
 * Update UI for stopped submission
 */
function updateUIForStoppedSubmission() {
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    
    if (startButton) {
        startButton.classList.remove('d-none');
    }
    
    if (stopButton) {
        stopButton.classList.add('d-none');
    }
    
    // Additional UI updates for stopped state
    document.querySelectorAll('.submission-controls input, .submission-controls select').forEach(el => {
        el.disabled = false;
    });
}

/**
 * Format seconds into human-readable time
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Display a status message to the user
 * @param {string} message - The message to display
 * @param {string} type - Message type (success, error, info)
 */
function showStatusMessage(message, type = 'info') {
    // This depends on your UI implementation
    const toast = document.getElementById('statusToast');
    const toastBody = document.getElementById('toast-message');
    
    if (!toast || !toastBody) {
        console.warn('Toast notification elements not found');
        console.log(`${type.toUpperCase()}: ${message}`);
        return;
    }
    
    // Update toast content
    toastBody.textContent = message;
    
    // Remove existing classes
    toast.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-info', 'text-bg-warning');
    
    // Add appropriate class based on type
    switch (type) {
        case 'success':
            toast.classList.add('text-bg-success');
            break;
        case 'error':
            toast.classList.add('text-bg-danger');
            break;
        case 'warning':
            toast.classList.add('text-bg-warning');
            break;
        default:
            toast.classList.add('text-bg-info');
    }
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}
