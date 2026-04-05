/**
 * Acadex Student Tracking Service
 */
const StudentService = {
    /**
     * Admin: Fetch all registered students
     */
    async listStudents() {
        return await ApiClient.get("/admin/get-students");
    },

    /**
     * Admin: Delete a student record
     */
    async deleteStudent(studentId) {
        if (!confirm("Are you sure? This delete is permanent.")) return;
        return await ApiClient.request(`/admin/delete-student?studentId=${studentId}`, { method: 'DELETE' });
    }
};
