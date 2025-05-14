function validatePercentages(input) {
    const parent = input.parentElement.parentElement;
    const inputs = parent.querySelectorAll('input[type="number"]');
    let total = 0;
    inputs.forEach(inp => total += parseInt(inp.value || 0));
    if (total > 100) {
        alert('Total percentage cannot exceed 100%');
        input.value = 0;
    }
}

function randomizePercentages(button) {
    const parent = button.parentElement;
    const inputs = parent.querySelectorAll('input[type="number"]');
    const count = inputs.length;
    let remaining = 100;
    let percentages = [];

    for (let i = 0; i < count - 1; i++) {
        const max = remaining - (count - i - 1) * 1;
        const value = Math.floor(Math.random() * (max + 1));
        percentages.push(value);
        remaining -= value;
    }
    percentages.push(remaining);

    inputs.forEach((inp, idx) => inp.value = percentages[idx]);
}