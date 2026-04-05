/**
 * Acadex - Dashboard Service
 * Fetches and renders complex dashboard metrics and charts.
 */
const DashboardService = {
    async fetchAdminData() {
        return await ApiClient.get("/dashboard/admin");
    },
    async fetchFacultyData() {
        return await ApiClient.get("/dashboard/faculty");
    },
    async fetchStudentData() {
        return await ApiClient.get("/dashboard/student");
    },

    renderChart(id, type, data, options = {}) {
        const ctx = document.getElementById(id);
        if (!ctx) return null;
        
        // Clean existing chart if any
        if (window.charts && window.charts[id]) {
            window.charts[id].destroy();
        }

        const newChart = new Chart(ctx, {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#94a3b8' } }
                },
                ...options
            }
        });

        if (!window.charts) window.charts = {};
        window.charts[id] = newChart;
        return newChart;
    }
};
