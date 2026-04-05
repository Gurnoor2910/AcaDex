/**
 * Acadex Marks Service
 * Handles unified marks marking, multi-role fetching, and reporting.
 */

const MarksService = {
    async addMark(data) {
        return await ApiClient.post("/marks/", data);
    },

    async getMyMarks() {
        return await ApiClient.get("/marks/student");
    },

    async getClassMarks(subject = "", examType = "", date = "") {
        let url = "/marks/class";
        const params = new URLSearchParams();
        if (subject) params.append("subject", subject);
        if (examType) params.append("examType", examType);
        if (date) params.append("date", date);
        
        const queryString = params.toString();
        if (queryString) url += "?" + queryString;
        return await ApiClient.get(url);
    },

    async updateMark(data) {
        return await ApiClient.put("/marks/", data);
    },
    
    async deleteMark(studentId, recordId) {
        return await ApiClient.delete(`/marks/?studentId=${studentId}&recordId=${recordId}`);
    },

    calculateStats(records) {
        if (!records || records.length === 0) return { totalScore: 0, totalMax: 0, percentage: 0 };
        
        let totalScore = 0;
        let totalMax = 0;
        
        records.forEach(r => {
            totalScore += parseFloat(r.score) || 0;
            totalMax += parseFloat(r.maxMarks) || 0;
        });
        
        const percentage = totalMax > 0 ? ((totalScore / totalMax) * 100).toFixed(1) : 0;
        
        return { totalScore, totalMax, percentage };
    },
    
    getGrade(score, maxScore) {
        const percentage = (score / maxScore) * 100;
        if (percentage >= 90) return 'A+';
        if (percentage >= 80) return 'A';
        if (percentage >= 70) return 'B';
        if (percentage >= 60) return 'C';
        if (percentage >= 50) return 'D';
        return 'F';
    }
};
