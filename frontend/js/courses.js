/**
 * Acadex - Courses & Structure Service
 */
const CourseService = {
    // ── Data Handling ─────────────────────────────────────────────────────────
    async loadCourseData() {
        try {
            const data = await ApiClient.get("/courses/structure");
            window.courseData = data;
            localStorage.setItem("acadex_course_updated", Date.now());
            return data;
        } catch (error) {
            console.error("Failed to fetch course structure:", error);
            throw error;
        }
    },

    initSync() {
        window.addEventListener("storage", (event) => {
            if (event.key === "acadex_course_updated") {
                this.loadCourseData().then(() => {
                    if (typeof window.renderUI === "function") window.renderUI();
                });
            }
        });
    },

    async _handleMutation(request) {
        const data = await request;
        window.courseData = data;
        localStorage.setItem("acadex_course_updated", Date.now());
        if (typeof window.renderUI === "function") window.renderUI();
        return data;
    },

    // ── API Interactions ──────────────────────────────────────────────────────
    async getAll() {
        return await ApiClient.get("/courses/all");
    },
    async create(data) {
        return this._handleMutation(ApiClient.post("/courses/add", data));
    },
    async updateCourse(courseId, data) {
        return this._handleMutation(ApiClient.put("/courses/edit", { courseId, ...data }));
    },
    async addSemester(courseId, semesterNumber) {
        return this._handleMutation(ApiClient.post("/courses/add-semester", { courseId, semesterNumber }));
    },
    async updateSemester(courseId, semesterId, semesterNumber) {
        return this._handleMutation(ApiClient.put("/courses/edit-semester", { courseId, semesterId, semesterNumber }));
    },
    async getSemesters(courseId) {
        return await ApiClient.get(`/courses/semesters?courseId=${courseId}`);
    },
    async getMyCourses() {
        return await ApiClient.get("/courses/my");
    },
    async getCurrentStructure() {
        return await ApiClient.get("/courses/current-structure");
    },
    async addSubject(courseId, semesterId, data) {
        return this._handleMutation(ApiClient.post("/courses/add-subject", { courseId, semesterId, ...data }));
    },
    async updateSubject(courseId, semesterId, subjectId, data) {
        return this._handleMutation(ApiClient.put("/courses/edit-subject", { courseId, semesterId, subjectId, ...data }));
    },
    async getSubjects(courseId, semesterId) {
        return await ApiClient.get(`/courses/subjects?courseId=${courseId}&semesterId=${semesterId}`);
    },
    async assignFaculty(courseId, semesterId, subjectId, facultyId, facultyName) {
        return this._handleMutation(ApiClient.put("/courses/assign-faculty", { 
            courseId, semesterId, subjectId, facultyId, facultyName 
        }));
    },
    async getStructure() {
        if (window.courseData) return window.courseData;
        return await this.loadCourseData();
    },
    async deleteItem(path) {
        return this._handleMutation(ApiClient.delete(`/courses/delete?path=${path}`));
    },
    async seed() {
        return this._handleMutation(ApiClient.post("/courses/seed"));
    }
};
