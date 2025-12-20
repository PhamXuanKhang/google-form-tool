import { showPopup } from './form_extract.js';

let currentStep = 1;
const totalSteps = 4;

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
}


function nextStep() {
    if (currentStep === 1) {
        const urlInput = document.getElementById("form-url-input");
        const previewContainer = document.getElementById("form-preview-container");
        const urlValue = urlInput.value.trim();
        const hasPreview = previewContainer.classList.contains("preview-loaded");

        if (!urlValue) return showPopup("Please enter a Google Form URL.");
        if (!hasPreview) return showPopup("Please extract the form before continuing.");

        // Get current values from window
        answerMethod = window.answerMethod || "manual";
        fileUploaded = window.fileUploaded || false;
        
        if (answerMethod === "manual" && window.formQuestionsData) {
            window.renderQuestionsStep2(window.formQuestionsData);
        } else if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup("Please upload a file with answer data.");
        }
    }else if (currentStep === 2) {
        // Get current value from window
        fileUploaded = window.fileUploaded || false;
        answerMethod = window.answerMethod || "manual";
        
        if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup("Please upload a file with answer data.");
        }
    }

    goToStep(currentStep + 1);
}


function prevStep() {
    goToStep(currentStep - 1);
}

// Make the functions globally available
window.goToStep = goToStep;
window.nextStep = nextStep;
window.prevStep = prevStep;