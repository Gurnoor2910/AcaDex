/**
 * Acadex - Announcements Service
 */
const AnnouncementService = {
    async create(data) {
        return await ApiClient.post("/announcements/", data);
    },
    async getAll() {
        return await ApiClient.get("/announcements/");
    },
    async getForStudent() {
        return await ApiClient.get("/announcements/"); // Unified
    },
    async getById(id) {
        return await ApiClient.get(`/announcements/view?id=${id}`);
    },
    async update(id, data) {
        return await ApiClient.put("/announcements/", { id, ...data });
    },
    async delete(id) {
        return await ApiClient.delete(`/announcements/?id=${id}`);
    },
    async seed() {
        return await ApiClient.post("/announcements/seed");
    },

    getPriorityColor(priority) {
        switch(priority) {
            case 'High': return '#ef4444'; // Red
            case 'Medium': return '#f59e0b'; // Amber
            case 'Low': return '#22c55e'; // Green
            default: return 'var(--text-secondary)';
        }
    }
};
