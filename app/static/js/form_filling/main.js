/**
 * @fileoverview Main JavaScript module for form filling automation interface.
 * 
 * This module coordinates between form extraction, configuration, and submission
 * processes. It manages the overall user interface state and handles the workflow
 * from form URL input to automated submission.
 * 
 * Key Features:
 * - Form URL validation and extraction
 * - Answer method selection (manual/file upload)
 * - Form submission coordination
 * - Real-time monitoring with charts
 * - Settings management
 * 
 * Dependencies:
 * - form_extract.js: Form data extraction functionality
 * - submission.js: Form submission automation
 * - Chart.js: For monitoring visualizations
 * - Bootstrap: For UI components
 * 
 * @author Google Form Automation Tool
 * @version 1.0.0
 */

import { extractFromUrl } from './form_extract.js';
import { startSubmission, stopSubmission } from './submission.js';
import { validatePrefillCompatibility } from './prefill_validator.js';

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

/**
 * Global application state variables.
 * These variables maintain the current state of the form filling interface.
 */

/** @type {string} Current answer input method ('manual' or 'fileUpload') */
window.answerMethod = "manual";

/** @type {boolean} Whether a data file has been successfully uploaded */
window.fileUploaded = false;

/** @type {string|null} The ID of the currently loaded form */
window.currentFormId = null;

/** @type {Array|null} Loaded responses from file upload */
window.loadedResponses = null;

// Function to collect form settings from the UI
function getFormSettings() {
    const formCountInput = document.getElementById("settings-form-count");
    const concurrentThreadsInput = document.getElementById("settings-concurrent-threads");
    const minDelayInput = document.getElementById("settings-min-delay");
    const maxDelayInput = document.getElementById("settings-max-delay");

    let formCount = parseInt(formCountInput?.value || 10, 10);

    // If file uploaded, use the number of loaded responses
    if (window.fileUploaded && window.loadedResponses) {
        formCount = window.loadedResponses.length;
    }

    // Get form URL from session (was entered in step 1)
    const formUrl = document.getElementById('form-url-input').value;

    // Create settings object. submission_mode is sent explicitly even though
    // the backend defaults to prefill_link, so the request shape is unambiguous
    // and a future debug selector cannot accidentally drop the field.
    const settings = {
        form_url: formUrl,
        form_id: window.currentFormId,
        num_submissions: formCount,
        concurrent_threads: parseInt(concurrentThreadsInput?.value || 2, 10),
        min_delay: parseFloat(minDelayInput?.value || 1),
        max_delay: parseFloat(maxDelayInput?.value || 5),
        submission_mode: window.submissionMode || "prefill_link",
    };

    // Include loaded responses if file was uploaded
    if (window.fileUploaded && window.loadedResponses) {
        settings.responses_list = window.loadedResponses;
        settings.use_file_data = true;
    }

    return settings;
}

window.getFormSettings = getFormSettings;
window.validatePrefillCompatibility = validatePrefillCompatibility;

// Function to start form submission
window.startFormSubmission = async function() {
    try {
        const settings = getFormSettings();
        const manualEdits = window.collectManualEdits?.();
        const check = validatePrefillCompatibility(
            window.formQuestionsData,
            settings,
            { manualEdits, t }
        );
        if (check && check.blocking) {
            window.showPopup?.(check.message, "warning");
            return;
        }
        if (check && Array.isArray(check.warnings) && check.warnings.length > 0) {
            window.showPopup?.(check.warnings.join(" "), "warning");
        }
        await startSubmission(settings);
    } catch (error) {
        console.error("Start submission failed:", error);
        window.showPopup?.(
            t("startSubmissionFailed", "Failed to start submission. Check the popup and browser console."),
            "error"
        );
    }
}

// Function to stop form submission
window.stopFormSubmission = async function() {
    await stopSubmission();
}

function toggleAnswerMethod() {
    const manualRadio = document.getElementById("manual");
    const fileUploadRadio = document.getElementById("fileUpload");
    const fileUploadSection = document.getElementById("file-upload-section");
    const questionsContainer = document.getElementById("step-2-questions");

    // Determine selected method (AI is no longer a separate top-level tab —
    // it lives inline inside each text question card now).
    if (manualRadio?.checked) {
        window.answerMethod = "manual";
    } else if (fileUploadRadio?.checked) {
        window.answerMethod = "fileUpload";
    }

    fileUploadSection?.classList.add("d-none");

    if (window.answerMethod === "manual") {
        questionsContainer?.classList.remove("d-none");
        if (window.formQuestionsData) {
            window.renderQuestionsStep2?.(window.formQuestionsData);
        }
    } else if (window.answerMethod === "fileUpload") {
        fileUploadSection?.classList.remove("d-none");
        questionsContainer?.classList.add("d-none");
        window.fileUploaded = false;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const formUrl = params.get('form_url');
    if (formUrl) {
        document.getElementById('form-url-input').value = formUrl;
        extractFromUrl(formUrl);
    }
    toggleAnswerMethod();

    // Initialize charts for submission monitoring
    initializeCharts();
});

/**
 * Resolve a Gemini API key for inline AI generation.
 *
 * Returns localStorage value when present; otherwise prompts the user via a
 * native popup. Newly entered keys are validated through /validate_api_key
 * and persisted to localStorage on success. Returns null when the user
 * cancels or validation fails so callers can short-circuit.
 */
window.getOrAskGeminiKey = async function () {
    const stored = localStorage.getItem('gemini_api_key');
    if (stored && stored.trim()) return stored.trim();

    const entered = window.prompt(t("aiKeyPrompt", "Enter your Google Gemini API key (get one at https://aistudio.google.com/apikey):"));
    if (!entered || !entered.trim()) {
        window.showPopup?.(t("aiKeyRequired", "An API key is required to use AI Generate."), 'warning');
        return null;
    }
    const key = entered.trim();
    try {
        const res = await fetch('/validate_api_key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key })
        });
        const result = await res.json().catch(() => ({}));
        if (res.ok && result.valid) {
            localStorage.setItem('gemini_api_key', key);
            window.showPopup?.(t("aiKeySaved", "API key saved."), 'success');
            return key;
        }
        const code = result.code || "";
        let message = result.error || t("invalidApiKey", "API key validation failed.");
        if (code === "ai_dependency_missing") {
            message = t("aiDependencyMissing", "AI dependency is not installed. Run pip install -r requirements.txt.");
        } else if (code === "model_unavailable") {
            message = t("aiModelUnavailable", "Selected Gemini model is unavailable. Check GEMINI_MODEL or API access.");
        }
        window.showPopup?.(message, 'error');
    } catch (e) {
        window.showPopup?.(`${t("invalidApiKey", "Invalid API key")}: ${e.message}`, 'error');
    }
    return null;
};

document.getElementById('extract-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const formUrlInput = document.getElementById('form-url-input');
    extractFromUrl(formUrlInput.value);
});

document.getElementById('file-upload-form')?.addEventListener('submit', async function (event) {
    event.preventDefault();

    if (!window.currentFormId) {
        window.showPopup(t("pleaseExtractBeforeUpload", "Please extract a form first before uploading data."));
        return;
    }

    const fileInput = document.getElementById('answer-file-input');
    if (!fileInput.files.length) {
        window.showPopup(t("pleaseSelectFile", "Please select a file to upload."));
        return;
    }

    const formData = new FormData();
    formData.append('form_id', window.currentFormId);
    formData.append('answer_file', fileInput.files[0]);

    try {
        const response = await fetch('/load_data', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            window.fileUploaded = true;
            window.loadedResponses = result.responses;

            // Show success message with row count
            const questionsContainer = document.getElementById("step-2-questions");
            questionsContainer.classList.remove("d-none");
            questionsContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>${t("fileLoadedSuccessfully", "File loaded successfully!")}</strong><br>
                    ${result.rows_loaded} ${t("responseSetsReady", "response sets ready for submission.")}
                </div>
                <div class="card p-3">
                    <h6>${t("previewFirstRows", "Preview (first 3 rows):")}</h6>
                    <pre style="max-height: 200px; overflow: auto; font-size: 12px;">${JSON.stringify(result.responses.slice(0, 3), null, 2)}</pre>
                </div>
            `;

            window.showPopup(result.message, 'success');
        } else {
            window.showPopup(result.error || t("failedToLoadFile", "Failed to load file"), 'error');
        }
    } catch (error) {
        console.error('File upload error:', error);
        window.showPopup(`${t("errorUploadingFile", "Error uploading file:")} ${error.message}`, 'error');
    }
});

// Initialize charts for monitoring
function initializeCharts() {
    // Create submission status chart
    const submissionCtx = document.getElementById('submission-chart')?.getContext('2d');
    if (submissionCtx) {
        window.submissionChart = new Chart(submissionCtx, {
            type: 'doughnut',
            data: {
                labels: [t("success", "Success"), t("failed", "Failed"), t("pending", "Pending")],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#28a745', '#dc3545', '#6c757d']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Create resource usage chart
    const resourceCtx = document.getElementById('resource-chart')?.getContext('2d');
    if (resourceCtx) {
        window.resourceChart = new Chart(resourceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage',
                    data: [],
                    borderColor: '#007bff',
                    tension: 0.1
                }, {
                    label: 'Memory Usage',
                    data: [],
                    borderColor: '#20c997',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        min: 0,
                        max: 100
                    }
                }
            }
        });
    }
}


// When extract is successful, store the form ID for later use
export function setCurrentFormId(id) {
    window.currentFormId = id;
}

// Make toggleAnswerMethod globally available
window.toggleAnswerMethod = toggleAnswerMethod;
