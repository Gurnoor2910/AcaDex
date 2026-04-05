/**
 * Acadex Attendance Service (Advanced v2)
 * Handles unified marking, multi-role fetching, and reporting.
 */

const AttendanceService = {
    // Shared: Mark attendance (Admin/Faculty)
    async mark(data) {
        // data: { studentId, status, date, subject }
        return await ApiClient.post("/attendance/mark", data);
    },

    // Student: Get my personal records
    async getMyAttendance() {
        return await ApiClient.get("/attendance/student");
    },

    // Admin/Faculty: Get class/all attendance with filters
    async getClassAttendance(date = "", subject = "") {
        let url = "/attendance/class";
        const params = new URLSearchParams();
        if (date) params.append("date", date);
        if (subject) params.append("subject", subject);
        
        const queryString = params.toString();
        if (queryString) url += "?" + queryString;
        
        return await ApiClient.get(url);
    },

    // Utility: Calculate Stats
    calculateStats(records) {
        if (!records || records.length === 0) return { percentage: 0, total: 0, present: 0, absent: 0 };
        const total = records.length;
        const present = records.filter(r => r.status.toLowerCase() === "present").length;
        const absent = total - present;
        const percentage = ((present / total) * 100).toFixed(1);
        
        return { percentage, total, present, absent };
    },

    // Utility: Group by Student (for reports)
    groupByStudent(records) {
        const groups = {};
        records.forEach(r => {
            const sid = r.studentId || "unknown";
            if (!groups[sid]) {
                groups[sid] = {
                    name: r.studentName || "Unknown",
                    email: r.studentEmail || "N/A",
                    records: []
                };
            }
            groups[sid].records.push(r);
        });
        return groups;
    },

    // Edit: Update existing record
    async update(data) {
        // data: { studentId, recordId, status, date, subject }
        return await ApiClient.put("/attendance/edit", data);
    }
};
