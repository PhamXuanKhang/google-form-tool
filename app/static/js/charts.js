/**
 * Shared chart helpers (Chart.js must be loaded first).
 * - Keeps chart text, grid lines and slice borders on the current theme.
 * - Draws "target versus actual" bars for one choice question.
 */
(function () {
    function token(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function syncChartTheme() {
        if (!window.Chart) return;
        Chart.defaults.color = token('--gf-text-muted');
        Chart.defaults.borderColor = token('--gf-border');
        Chart.defaults.elements.arc.borderColor = token('--gf-surface');
        Object.values(Chart.instances || {}).forEach((chart) => {
            if (chart.$gfRecolor) chart.$gfRecolor();
            chart.update();
        });
    }

    /**
     * @param {HTMLCanvasElement} canvas
     * @param {Array<{text: string, rate: number, target: number|null}>} options
     * @param {{target: string, actual: string}} labels
     */
    function targetVsActual(canvas, options, labels) {
        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: options.map((option) => option.text),
                datasets: [
                    { label: labels.target, data: options.map((option) => option.target ?? 0), borderRadius: 4 },
                    { label: labels.actual, data: options.map((option) => option.rate), borderRadius: 4 },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 200 },
                scales: { y: { beginAtZero: true, ticks: { callback: (value) => `${value}%` } } },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12 } },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}%` } },
                },
            },
        });
        chart.$gfRecolor = () => {
            chart.data.datasets[0].backgroundColor = token('--gf-border-strong');
            chart.data.datasets[1].backgroundColor = token('--gf-accent');
        };
        chart.$gfRecolor();
        chart.update();
        return chart;
    }

    syncChartTheme();
    document.addEventListener('themechange', syncChartTheme);
    window.GFCharts = { syncChartTheme, targetVsActual };
})();
