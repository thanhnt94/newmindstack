/**
 * Stats Charts Manager
 * Handles initializing and rendering charts for the Analytics Dashboard.
 * Relies on Chart.js being loaded.
 */

const StatsCharts = {
    charts: {}, // Store chart instances

    init: function () {
        // Find all elements with data-chart-config attribute
        document.querySelectorAll('[data-chart-config]').forEach(element => {
            this.renderChart(element);
        });
    },

    renderChart: function (canvasElement) {
        if (!canvasElement) return;

        const chartId = canvasElement.id;
        const configStr = canvasElement.dataset.chartConfig;

        if (!configStr) {
            console.warn(`No config found for chart ${chartId}`);
            return;
        }

        try {
            const config = JSON.parse(configStr);

            // Destroy existing chart if present
            if (this.charts[chartId]) {
                this.charts[chartId].destroy();
            }

            // Create new chart
            const ctx = canvasElement.getContext('2d');
            this.charts[chartId] = new Chart(ctx, config);

        } catch (e) {
            console.error(`Failed to render chart ${chartId}:`, e);
            console.error('Config String:', configStr);
        }
    },

    updateChart: function (elementId, newData) {
        // Helper to update chart data dynamically (if needed via AJAX)
        const chart = this.charts[elementId];
        if (chart) {
            chart.data = newData;
            chart.update();
        }
    }
};

// Auto-init when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    StatsCharts.init();
});
