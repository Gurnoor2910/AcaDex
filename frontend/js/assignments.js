/**
 * Acadex - Assignments & Materials Service
 */
const MaterialService = {
    async create(data) {
        return await ApiClient.post("/materials/add", data);
    },
    async getAll() {
        return await ApiClient.get("/materials/");
    },
    async update(id, data) {
        return await ApiClient.put("/materials/edit", { id, ...data });
    },
    async delete(id) {
        return await ApiClient.delete(`/materials/delete?id=${id}`);
    }
};

const AssignmentService = {
    async create(data) {
        return await ApiClient.post("/assignments/add", data);
    },
    async getAll() {
        return await ApiClient.get("/assignments/");
    },
    async update(id, data) {
        return await ApiClient.put("/assignments/edit", { id, ...data });
    },
    async delete(id) {
        return await ApiClient.delete(`/assignments/delete?id=${id}`);
    },
    async submit(assignmentId, fileUrl) {
        return await ApiClient.post("/assignments/submit", { assignmentId, fileUrl });
    },
    async getSubmissions(assignmentId) {
        return await ApiClient.get(`/assignments/submissions?assignmentId=${assignmentId}`);
    },
    async getMySubmissions() {
        return await ApiClient.get("/assignments/my-submissions");
    },
    async grade(assignmentId, studentId, marks, feedback) {
        return await ApiClient.put("/assignments/grade", { assignmentId, studentId, marks, feedback });
    },
    async seed() {
        return await ApiClient.post("/assignments/seed");
    }
};
