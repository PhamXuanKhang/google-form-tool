import { extractFromUrl } from './form_extract.js';

let answerMethod = "manual";
let fileUploaded = false;


function toggleAnswerMethod() {
    const manualRadio = document.getElementById("manual");
    const fileUploadSection = document.getElementById("file-upload-section");
    const questionsContainer = document.getElementById("step-2-questions");

    answerMethod = manualRadio.checked ? "manual" : "fileUpload";
    
    if (answerMethod === "manual") {
        fileUploadSection.classList.add("d-none");
        questionsContainer.classList.remove("d-none");
        // Render questions for manual input if form data exists
        if (window.formQuestionsData) {
            renderQuestionsStep2(window.formQuestionsData);
        }
    } else {
        fileUploadSection.classList.remove("d-none");
        questionsContainer.classList.add("d-none"); // Hide until file is uploaded
        fileUploaded = false; // Reset file upload state
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
});


document.getElementById('extract-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const formUrlInput = document.getElementById('form-url-input');
    extractFromUrl(formUrlInput.value);
});


document.getElementById('file-upload-form')?.addEventListener('submit', async function (event) {
    event.preventDefault();
    showPopup("This function is not implemented yet. Please use the manual input method for now.")
});


document.querySelectorAll(".email-generator").forEach(container => {
    const domainSelect = container.querySelector(".email-domain");
    const generateBtn = container.querySelector(".generate-email-btn");
    const textarea = container.querySelector(".email-textarea");

    generateBtn.addEventListener("click", () => {
        const domain = domainSelect.value;
        const count = parseInt(document.getElementById("form-count").value || 10);
        textarea.value = generateEmails(domain, count);
    });
});