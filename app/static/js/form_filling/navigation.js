import { showPopup } from './form_extract.js';

let currentStep = 1;
const totalSteps = 4;

function t(key, fallback) {
    return window.i18n?.[key] || fallback;
}

// Get references to global variables
let answerMethod;
let fileUploaded;

document.addEventListener('DOMContentLoaded', () => {
    // Get values from window object that are set in main.js
    answerMethod = window.answerMethod || "manual";
    fileUploaded = window.fileUploaded || false;
});

function goToStep(step) {
    if (step < 1 || step > totalSteps) return;

    for (let i = 1; i <= totalSteps; i++) {
        document.getElementById(`step-${i}`).classList.add("d-none");
        document.getElementById(`sidebar-step-${i}`).classList.remove("active");
        document.getElementById(`badge-step-${i}`).classList.replace("bg-dark", "bg-secondary");
    }

    document.getElementById(`step-${step}`).classList.remove("d-none");
    document.getElementById(`sidebar-step-${step}`).classList.add("active");
    document.getElementById(`badge-step-${step}`).classList.replace("bg-secondary", "bg-dark");

    currentStep = step;

    if (step === 3) {
        syncSettingsFromExistingFormCount();
    }
}


function nextStep() {
    if (currentStep === 1) {
        const urlInput = document.getElementById("form-url-input");
        const previewContainer = document.getElementById("form-preview-container");
        const urlValue = urlInput.value.trim();
        const hasPreview = previewContainer.classList.contains("preview-loaded");

        if (!urlValue) return showPopup(t("pleaseEnterGoogleFormUrl", "Please enter a Google Form URL."));
        if (!hasPreview) return showPopup(t("pleaseExtractBeforeContinuing", "Please extract the form before continuing."));

        // Get current values from window
        answerMethod = window.answerMethod || "manual";
        fileUploaded = window.fileUploaded || false;
        
        if (answerMethod === "manual" && window.formQuestionsData) {
            window.renderQuestionsStep2(window.formQuestionsData);
        } else if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup(t("pleaseUploadAnswerFile", "Please upload a file with answer data."));
        }
    } else if (currentStep === 2) {
        // Get current value from window
        fileUploaded = window.fileUploaded || false;
        answerMethod = window.answerMethod || "manual";
        
        if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup(t("pleaseUploadAnswerFile", "Please upload a file with answer data."));
        }
    } else if (currentStep === 3) {
        const validationError = validateSettingsStep();
        if (validationError) {
            return showPopup(validationError);
        }
    }

    goToStep(currentStep + 1);
}


function prevStep() {
    goToStep(currentStep - 1);
}

function syncSettingsFromExistingFormCount() {
    const settingsFormCount = document.getElementById("settings-form-count");
    const existingFormCount = document.getElementById("form-count");

    if (settingsFormCount && existingFormCount && !settingsFormCount.dataset.syncedFromStep2) {
        settingsFormCount.value = existingFormCount.value || settingsFormCount.value;
        settingsFormCount.dataset.syncedFromStep2 = "true";
    }
}

function validateSettingsStep() {
    const settings = window.getFormSettings?.();
    if (!settings) {
        return null;
    }

    const submissions = settings.num_submissions;
    const threads = settings.concurrent_threads;
    const minDelay = settings.min_delay;
    const maxDelay = settings.max_delay;

    if (!Number.isInteger(submissions) || submissions < 1 || submissions > 500) {
        return t("settingsSubmissionsRange", "Number of submissions must be between 1 and 500.");
    }
    if (!Number.isInteger(threads) || threads < 1 || threads > 10) {
        return t("settingsThreadsRange", "Concurrent threads must be between 1 and 10.");
    }
    if (threads > submissions) {
        return t("settingsThreadsTooHigh", "Concurrent threads cannot be greater than submissions.");
    }
    if (!Number.isFinite(minDelay) || !Number.isFinite(maxDelay) || minDelay < 0 || maxDelay < 0) {
        return t("settingsDelayInvalid", "Delays must be non-negative numbers.");
    }
    if (maxDelay < minDelay) {
        return t("settingsDelayRange", "Maximum delay must be greater than or equal to minimum delay.");
    }

    return null;
}

window.validateSettingsStep = validateSettingsStep;

// Make the functions globally available
window.goToStep = goToStep;
window.nextStep = nextStep;
window.prevStep = prevStep;
