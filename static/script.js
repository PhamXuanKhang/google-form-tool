// create logger class to debug
class Logger {
    static log(message) {
        console.log(`[LOG] ${new Date().toISOString()}: ${message}`);
    }

    static info(message) {
        console.info(`[INFO] ${new Date().toISOString()}: ${message}`);
    }

    static warn(message) {
        console.warn(`[WARN] ${new Date().toISOString()}: ${message}`);
    }

    static error(message) {
        console.error(`[ERROR] ${new Date().toISOString()}: ${message}`);
    }
}

// Change form details to page details
function saveFormDetails() {
    const pageCount = document.getElementById('page-count').value;
    if (pageCount == 0) {
        alert("Please enter a valid info");
        return;
    }

    // Hidden the form pages after user click
    document.getElementById('form-details').style.display = 'none';
    document.getElementById('page-details').style.display = 'block';

    // Delete the available content if have
    const pageContainer = document.getElementById('page-container');
    pageContainer.innerHTML = '';

    // Create block for each page
    for (let i = 1; i <= pageCount; i++) {
        const section = document.createElement('div');
        section.className = "card";
        section.innerHTML = `
            <div class="card-header">
                <h3>Page ${i}</h3>
            </div>
            <div class="card-body">
                <div id="fields-container-${i}"></div>
                <button type="button" class="btn btn-primary add-field-button" onclick="addField(${i})">Add Field</button>
            </div>
        `;
        pageContainer.appendChild(section);
    }
}

// Add more fields
function addField(pageNumber) {
    const fieldsContainer = document.getElementById(`fields-container-${pageNumber}`);

    const newField = document.createElement('div');
    newField.className = "field-container mb-3 mt-3";
    newField.innerHTML = `
        <div class="mb-3">
            <label class="form-label" for="xpath-${pageNumber}">XPath:</label>
            <div class="d-flex align-items-center">
                <input class="form-control" style="width: calc(60%);" type="text" id="xpath-${pageNumber}" name="xpath-${pageNumber}" placeholder="Enter XPath">
                <button type="button" class="btn btn-info btn-sm ms-2" onclick="showInstructions(event)">?</button>
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label" for="content-${pageNumber}">Content:</label>
            <textarea class="form-control" id="content-${pageNumber}" name="content-${pageNumber}" rows="4"></textarea>
        </div>
        <div class="mb-3">
            <label class="form-label" for="type-${pageNumber}">Type:</label>
            <select class="form-select" id="type-${pageNumber}" name="type-${pageNumber}">
                <option value="name">Name</option>
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="date">Date</option>
                <option value="other">Other</option>
            </select>
        </div>
    `;

    fieldsContainer.insertBefore(newField, fieldsContainer.querySelector('.add-field-button'));

}

// Create a popup to show instruction
function showInstructions(event) {
    document.querySelectorAll('.instruction-popup').forEach(popup => popup.remove());

    let popup = document.createElement('div');
    popup.className = 'instruction-popup';
    popup.innerHTML = "Right click on html element and copy XPATH or enter like '//textarea'.";
    
    document.body.appendChild(popup);
    popup.style.display = 'block';

    // Position the popup near the button
    let button = event.currentTarget;
    let rect = button.getBoundingClientRect();
    popup.style.top = (rect.bottom + window.scrollY) + 'px';
    popup.style.left = (rect.left + window.scrollX) + 'px';

    // Remove the popup when clicking anywhere else
    function handleClickOutside(e) {
        if (!popup.contains(e.target) && e.target !== button) {
            popup.remove();
            document.removeEventListener('click', handleClickOutside);
        }
    }

    document.addEventListener('click', handleClickOutside);
}

function savePageDetails() {
    // Save page details and move to prefill links
    document.getElementById('page-details').style.display = 'none';
    document.getElementById('prefill-links').style.display = 'block';
}

document.getElementById('submit-button').addEventListener('click', async () => {
    // Collect data
    const formCount = parseInt(document.getElementById('form-count').value);
    const money = parseInt(document.getElementById('money').value);
    const prefillLink = document.getElementById('prefill-link').value;
    
    // Get all pages and fields
    const pages = [];
    const pageContainers = document.querySelectorAll('#page-container > div.card');

    pageContainers.forEach((pageContainer, pageIndex) => {
        const fields = [];
        const fieldContainers = pageContainer.querySelectorAll('.field-container');

        fieldContainers.forEach((fieldContainer) => {
            const xpath = fieldContainer.querySelector(`input[name="xpath-${pageIndex + 1}"]`).value;
            const fieldType = fieldContainer.querySelector(`select[name="type-${pageIndex + 1}"]`).value;
            const content = fieldContainer.querySelector(`textarea[name="content-${pageIndex + 1}"]`).value;

            fields.push({
                xpath: xpath,
                field_type: fieldType,
                value: content
            });
        });

        pages.push({ fields: fields });
    });
    Logger.info("Prepared data for transfer")

    // Build FormModel object prepare for api
    const formData = {
        pages: pages,
        num_forms: formCount,
        money: money,
        links: prefillLink
    };

    // Send POST request to endpoint to submit form
    try {await fetch('/submit-form/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    });
    updateProgress();
    }catch(error){
        Logger.error("submit form", error);
    } 

    // Show progress and filling control
    document.getElementById('prefill-links').style.display = 'none';
    document.getElementById('submit-button').style.display = 'none';
    document.getElementById('filling').style.display = 'block';
});

// POST request to start
document.getElementById('start-button').addEventListener('click', async () => {
    try{await fetch('/start-fill/', { method: 'POST' });
    }catch(error){
        Logger.error("start", error)
    }
});

// PATCH request to stop
document.getElementById('stop-button').addEventListener('click', async () => {
    try{await fetch('/stop-fill/', { method: 'PATCH' });
    }catch(error){
        Logger.error("stop", error)
    }
});

// POST request to continue
document.getElementById('continue-button').addEventListener('click', async () => {
    try{await fetch('/continue-fill/', { method: 'POST' });
    }catch(error){
        Logger.error("continue", error)
    }  
});

// PATCH request to change mode
try {document.querySelectorAll('input[name="option"]').forEach(radio => 
    radio.addEventListener('change', () => {
        fetch('/change-mode/?mode=${radio.value}', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' }
        });
    })
);
}catch(error){
    Logger.error("change mode", error)
}

// change time from second to ISO type
function secondsToHms(seconds) {
    return new Date(seconds * 1000).toISOString().substring(11, 19);
}

// method to update progress each 10s after start
async function updateProgress() {
    try{const response = await fetch('/progress-fill', { method: 'GET' });
    const data = await response.json();
    const progress = data.progress;
    const state_num = data.state_num
    const time = data.time;
    const money = data.money;

    const progressFilling = document.getElementById('progress-filling');
    const progressText = document.getElementById('progress-text');
    const timeDisplay = document.getElementById('time-display');
    const moneyDisplay = document.getElementById('money-display');
    
    progressFilling.style.width = `${progress*100}%`;
    progressText.textContent = `${Math.round(progress * 100)}% : ${state_num} forms`;
    timeDisplay.textContent = `Time: ${secondsToHms(time)}`;
    moneyDisplay.textContent = `Money: ${money}k VND`;

    if (progress < 1) {
        setTimeout(updateProgress, 10000);
    }else{
        document.getElementById('restart-button').style.display = 'block';
    }
    }catch(error){
        Logger.error("update progress", error)
    }
}

document.getElementById('restart-button').addEventListener('click', function() {
    location.reload();
});