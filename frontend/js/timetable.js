/**
 * Acadex - Advanced Multi-Course Timetable Service
 */
const TimetableService = {
    DAYS: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    SLOTS: ["09:00-10:00", "10:00-11:00", "11:15-12:15", "12:15-01:15", "02:00-03:00", "03:00-04:00", "04:00-05:00"],
    
    // Core API Methods
    async create(data) { return await ApiClient.post("/timetable/", data); },
    async getAll() { return await ApiClient.get("/timetable/"); },
    async getMyFacultyTT() { return await ApiClient.get("/timetable/"); },
    async getMyStudentTT() { return await ApiClient.get("/timetable/"); },
    async update(data) { return await ApiClient.put("/timetable/", data); },
    async delete(id) { return await ApiClient.delete(`/timetable/?id=${id}`); },
    async seed() { return await ApiClient.post("/timetable/seed"); },

    /**
     * Advanced Grid Renderer
     */
    renderGridView(containerId, list, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const { onEdit = null, showAll = true, highlightCurrent = true } = options;
        const now = new Date();
        const currentDay = this.DAYS[now.getDay() - 1] || "";
        const currentTime = now.getHours() + ":" + now.getMinutes().toString().padStart(2, '0');

        // Generate Legend
        const uniqueCourses = [...new Set(list.map(e => e.course))].filter(Boolean);
        this.renderLegend(containerId + "-legend", uniqueCourses);

        let html = `
            <div class="tt-wrapper">
                <table class="tt-grid">
                    <thead>
                        <tr>
                            <th class="sticky-col">Time</th>
                            ${this.DAYS.map(d => `<th class="${d === currentDay ? 'current-day' : ''}">${d}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;

        this.SLOTS.forEach(slot => {
            html += `<tr><td class="time-slot sticky-col">${slot}</td>`;
            this.DAYS.forEach(day => {
                const entries = list.filter(e => e.day === day && e.timeSlot === slot);
                
                if (entries.length > 0) {
                    html += `<td><div class="slot-container">`;
                    entries.forEach(entry => {
                        const isBroken = !entry.courseId || !entry.subjectId;
                        const statusClass = this.getTimeStatus(day, slot, currentDay, currentTime);
                        const courseColor = this.getCourseColor(entry.course);
                        
                        html += `
                            <div class="tt-block ${statusClass} ${isBroken ? 'broken' : ''}" 
                                 style="--course-color: ${courseColor};"
                                 onclick="${onEdit ? `window.openEditModal('${entry.id}')` : ''}"
                                 title="${entry.subjectName}\nFaculty: ${entry.facultyName}\nRoom: ${entry.room}">
                                <div class="tt-course-tag">${entry.course}</div>
                                <div class="tt-subject">${entry.subjectName || entry.subject}</div>
                                <div class="tt-meta">
                                    <span><i class="fas fa-user-tie"></i> ${entry.facultyName || 'No Faculty'}</span>
                                    <span><i class="fas fa-map-marker-alt"></i> ${entry.room || 'TBD'}</span>
                                </div>
                                ${isBroken ? '<div class="err-tag"><i class="fas fa-exclamation-triangle"></i> Link Error</div>' : ''}
                            </div>
                        `;
                    });
                    html += `</div></td>`;
                } else {
                    html += `<td class="empty-cell"></td>`;
                }
            });
            html += `</tr>`;
        });

        html += `</tbody></table></div>`;
        container.innerHTML = html;
    },

    /**
     * Render Course Legend
     */
    renderLegend(containerId, courses) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = `
            <div class="tt-legend">
                ${courses.map(c => `
                    <div class="legend-item">
                        <span class="legend-dot" style="background: ${this.getCourseColor(c)}"></span>
                        <span class="legend-text">${c}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    /**
     * Color Assignment Utility
     */
    getCourseColor(courseName) {
        if (!courseName) return "#64748b";
        const presets = {
            "BCA": "#3b82f6",
            "BBA": "#10b981",
            "MBA": "#8b5cf6",
            "B.Tech CS": "#f59e0b",
            "M.Tech": "#ef4444"
        };
        if (presets[courseName]) return presets[courseName];
        
        let hash = 0;
        for (let i = 0; i < courseName.length; i++) hash += courseName.charCodeAt(i);
        const palette = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899"];
        return palette[hash % palette.length];
    },

    /**
     * Time-based Highlighting Logic
     */
    getTimeStatus(day, slot, currentDay, currentTime) {
        if (day !== currentDay) return "upcoming";
        const [start, end] = slot.split('-');
        if (currentTime < start) return "upcoming";
        if (currentTime > end) return "past";
        return "current-slot pulsate";
    }
};
