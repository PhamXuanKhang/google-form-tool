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

// Function to collect form settings from the UI
function getFormSettings() {
    // Get form count
    const formCount = parseInt(document.getElementById("form-count").value || 10);
    
    // Get form URL from session (was entered in step 1)
    const formUrl = document.getElementById('form-url-input').value;
    
    // Create settings object
    return {
        form_url: formUrl,
        form_id: window.currentFormId, // This will be set when form is extracted
        num_submissions: formCount,
        concurrent_threads: 2, // Default to 2 threads
        min_delay: 1, // Default minimum delay between submissions (seconds)
        max_delay: 5, // Default maximum delay between submissions (seconds)
        // Add any other settings needed
    };
}

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
    const fileUploadSection = document.getElementById("file-upload-section");
    const questionsContainer = document.getElementById("step-2-questions");

    window.answerMethod = manualRadio.checked ? "manual" : "fileUpload";
    
    if (window.answerMethod === "manual") {
        fileUploadSection.classList.add("d-none");
        questionsContainer.classList.remove("d-none");
        // Render questions for manual input if form data exists
        if (window.formQuestionsData) {
            window.renderQuestionsStep2(window.formQuestionsData);
        }
    } else {
        fileUploadSection.classList.remove("d-none");
        questionsContainer.classList.add("d-none"); // Hide until file is uploaded
        window.fileUploaded = false; // Reset file upload state
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

document.getElementById('extract-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const formUrlInput = document.getElementById('form-url-input');
    extractFromUrl(formUrlInput.value);
});

document.getElementById('file-upload-form')?.addEventListener('submit', async function (event) {
    event.preventDefault();
    window.showPopup("This function is not implemented yet. Please use the manual input method for now.")
});

// Initialize charts for monitoring
function initializeCharts() {
    // Create submission status chart
    const submissionCtx = document.getElementById('submission-chart')?.getContext('2d');
    if (submissionCtx) {
        window.submissionChart = new Chart(submissionCtx, {
            type: 'doughnut',
            data: {
                labels: ['Success', 'Failed', 'Pending'],
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