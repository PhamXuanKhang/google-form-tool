let currentStep = 1;
const totalSteps = 4;


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

        if (answerMethod === "manual" && window.formQuestionsData) {
            renderQuestionsStep2(window.formQuestionsData);
        } else if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup("Please upload a file with answer data.");
        }
    }else if (currentStep === 2) {
        if (answerMethod === "fileUpload" && !fileUploaded) {
            return showPopup("Please upload a file with answer data.");
        }
    }

    goToStep(currentStep + 1);
}


function prevStep() {
    goToStep(currentStep - 1);
}


function showPopup(message) {
    document.getElementById("toast-message").textContent = message;
    const toast = new bootstrap.Toast(document.getElementById("warningToast"));
    toast.show();
}