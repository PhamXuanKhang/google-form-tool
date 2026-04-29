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

    // Create settings object
    const settings = {
        form_url: formUrl,
        form_id: window.currentFormId,
        num_submissions: formCount,
        concurrent_threads: parseInt(concurrentThreadsInput?.value || 2, 10),
        min_delay: parseFloat(minDelayInput?.value || 1),
        max_delay: parseFloat(maxDelayInput?.value || 5),
    };

    // Include loaded responses if file was uploaded
    if (window.fileUploaded && window.loadedResponses) {
        settings.responses_list = window.loadedResponses;
        settings.use_file_data = true;
    }

    // Include AI-generated responses
    if (window.answerMethod === "aiGenerate" && window.aiGeneratedResponses) {
        settings.responses = window.aiGeneratedResponses;
        settings.use_ai_responses = true;
    }

    return settings;
}

window.getFormSettings = getFormSettings;

// Function to start form submission
window.startFormSubmission = async function() {
    const settings = getFormSettings();
    await startSubmission(settings);
}

// Function to stop form submission
window.stopFormSubmission = async function() {
    await stopSubmission();
}

function toggleAnswerMethod() {
    const manualRadio = document.getElementById("manual");
    const fileUploadRadio = document.getElementById("fileUpload");
    const aiGenerateRadio = document.getElementById("aiGenerate");
    const fileUploadSection = document.getElementById("file-upload-section");
    const aiGenerateSection = document.getElementById("ai-generate-section");
    const questionsContainer = document.getElementById("step-2-questions");

    // Determine selected method
    if (manualRadio?.checked) {
        window.answerMethod = "manual";
    } else if (fileUploadRadio?.checked) {
        window.answerMethod = "fileUpload";
    } else if (aiGenerateRadio?.checked) {
        window.answerMethod = "aiGenerate";
    }

    // Hide all optional sections first
    fileUploadSection?.classList.add("d-none");
    aiGenerateSection?.classList.add("d-none");

    if (window.answerMethod === "manual") {
        questionsContainer?.classList.remove("d-none");
        if (window.formQuestionsData) {
            window.renderQuestionsStep2?.(window.formQuestionsData);
        }
    } else if (window.answerMethod === "fileUpload") {
        fileUploadSection?.classList.remove("d-none");
        questionsContainer?.classList.add("d-none");
        window.fileUploaded = false;
    } else if (window.answerMethod === "aiGenerate") {
        aiGenerateSection?.classList.remove("d-none");
        questionsContainer?.classList.remove("d-none");
        if (window.formQuestionsData) {
            window.renderQuestionsStep2?.(window.formQuestionsData);
        }
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

    // Setup AI functionality
    setupAIFeatures();
});

function setupAIFeatures() {
    const validateBtn = document.getElementById('validate-api-key-btn');
    const generateBtn = document.getElementById('generate-ai-responses-btn');
    const apiKeyInput = document.getElementById('gemini-api-key');
    const statusDiv = document.getElementById('api-key-status');

    // Validate API key button
    validateBtn?.addEventListener('click', async () => {
        const apiKey = apiKeyInput?.value?.trim();
        if (!apiKey) {
            statusDiv.innerHTML = `<span class="text-warning"><i class="fas fa-exclamation-triangle"></i> ${t("pleaseEnterApiKey", "Please enter an API key")}</span>`;
            return;
        }

        statusDiv.innerHTML = `<span class="text-info"><i class="fas fa-spinner fa-spin"></i> ${t("validating", "Validating...")}</span>`;

        try {
            const response = await fetch('/validate_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });
            const result = await response.json();

            if (result.valid) {
                statusDiv.innerHTML = `<span class="text-success"><i class="fas fa-check-circle"></i> ${t("apiKeyValid", "API key is valid!")}</span>`;
                generateBtn.disabled = false;
                window.geminiApiKey = apiKey;
                localStorage.setItem('gemini_api_key', apiKey);
            } else {
                statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${result.error || t("invalidApiKey", "Invalid API key")}</span>`;
                generateBtn.disabled = true;
            }
        } catch (error) {
            statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> Error: ${error.message}</span>`;
            generateBtn.disabled = true;
        }
    });

    // Generate AI responses button
    generateBtn?.addEventListener('click', async () => {
        if (!window.currentFormId) {
            window.showPopup?.(t("pleaseExtractFormFirst", "Please extract a form first."));
            return;
        }

        const apiKey = window.geminiApiKey || apiKeyInput?.value?.trim();
        if (!apiKey) {
            window.showPopup?.(t("pleaseEnterValidateApiKey", "Please enter and validate your API key first."));
            return;
        }

        generateBtn.disabled = true;
        generateBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i> ${t("generating", "Generating...")}`;

        try {
            const response = await fetch('/generate_response', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    form_id: window.currentFormId,
                    use_ai: true,
                    api_key: apiKey
                })
            });
            const result = await response.json();

            if (result.success) {
                window.aiGeneratedResponses = result.responses;
                window.showPopup?.(`${t("aiResponsesGenerated", "AI responses generated!")} (${Object.keys(result.responses).length})`, 'success');

                // Show preview of generated responses
                const questionsContainer = document.getElementById("step-2-questions");
                if (questionsContainer) {
                    questionsContainer.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            <strong>${t("aiResponsesGenerated", "AI responses generated!")}</strong>
                        </div>
                        <div class="card p-3">
                            <h6>${t("generatedResponsesPreview", "Generated Responses Preview:")}</h6>
                            <pre style="max-height: 300px; overflow: auto; font-size: 12px;">${JSON.stringify(result.responses, null, 2)}</pre>
                        </div>
                    `;
                }
            } else {
                window.showPopup?.(result.error || t("failedToGenerateResponses", "Failed to generate responses"), 'error');
            }
        } catch (error) {
            window.showPopup?.("Error: " + error.message, 'error');
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = `<i class="fas fa-magic me-1"></i> ${t("generateAiResponses", "Generate AI Responses")}`;
        }
    });

    // Load saved API key from localStorage
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey && apiKeyInput) {
        apiKeyInput.value = savedKey;
    }
}

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
                labels: Array(10).fill(''),
                datasets: [{
                    label: 'CPU Usage',
                    data: Array(10).fill(0),
                    borderColor: '#007bff',
                    tension: 0.1
                }, {
                    label: 'Memory Usage',
                    data: Array(10).fill(0),
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
