/**
 * Acadex Layout & UI Engine
 * Handles dynamic navigation, sidebar, and theme switching
 */

const Layout = {
    links: {
        admin: [
            { id: "dashboard", icon: '<i class="fas fa-chart-line"></i>', text: "Dashboard", href: "admin-dashboard.html" },
            { id: "faculty", icon: '<i class="fas fa-user-tie"></i>', text: "Faculty", href: "faculty-management.html" },
            { id: "students", icon: '<i class="fas fa-user-graduate"></i>', text: "Students", href: "student-management.html" },
            { id: "courses", icon: '<i class="fas fa-book"></i>', text: "Courses", href: "course-management.html" },
            { id: "structure", icon: '<i class="fas fa-sitemap"></i>', text: "Course Structure", href: "course-structure.html" },
            { id: "attendance", icon: '<i class="fas fa-calendar-check"></i>', text: "Attendance", href: "admin-attendance.html" },
            { id: "marks", icon: '<i class="fas fa-award"></i>', text: "Marks", href: "marks-management.html" },
            { id: "fees", icon: '<i class="fas fa-credit-card"></i>', text: "Fees", href: "fees-management.html" },
            { id: "timetable", icon: '<i class="fas fa-clock"></i>', text: "Timetable", href: "timetable-management.html" },
            { id: "assignments", icon: '<i class="fas fa-tasks"></i>', text: "Assignments", href: "admin-assignments.html" },
            { id: "announcements", icon: '<i class="fas fa-bullhorn"></i>', text: "Announcements", href: "announcements-management.html" }
        ],
        student: [
            { id: "dashboard", icon: '<i class="fas fa-home"></i>', text: "Dashboard", href: "student-dashboard.html" },
            { id: "timetable", icon: '<i class="fas fa-calendar-alt"></i>', text: "Timetable", href: "student-timetable.html" },
            { id: "attendance", icon: '<i class="fas fa-calendar-check"></i>', text: "Attendance", href: "student-attendance.html" },
            { id: "marks", icon: '<i class="fas fa-award"></i>', text: "Marks", href: "student-marks.html" },
            { id: "materials", icon: '<i class="fas fa-book"></i>', text: "Study Materials", href: "materials.html" },
            { id: "submissions", icon: '<i class="fas fa-tasks"></i>', text: "My Submissions", href: "student-submissions.html" },
            { id: "assignments", icon: '<i class="fas fa-envelope-open-text"></i>', text: "Assignments", href: "assignments.html" },
            { id: "announcements", icon: '<i class="fas fa-bullhorn"></i>', text: "Announcements", href: "announcements.html" },
            { id: "fees", icon: '<i class="fas fa-credit-card"></i>', text: "Fees", href: "student-fees.html" }
        ],
        faculty: [
            { id: "dashboard", icon: '<i class="fas fa-chart-bar"></i>', text: "Dashboard", href: "faculty-dashboard.html" },
            { id: "attendance", icon: '<i class="fas fa-calendar-check"></i>', text: "Attendance", href: "mark-attendance.html" },
            { id: "marks", icon: '<i class="fas fa-award"></i>', text: "Marks", href: "marks-management.html" },
            { id: "assignments", icon: '<i class="fas fa-tasks"></i>', text: "Assignments", href: "faculty-assignments.html" },
            { id: "timetable", icon: '<i class="fas fa-calendar-alt"></i>', text: "Timetable", href: "faculty-timetable.html" },
            { id: "materials", icon: '<i class="fas fa-file-upload"></i>', text: "Upload Material", href: "add-material.html" },
            { id: "announcements", icon: '<i class="fas fa-bullhorn"></i>', text: "Announcements", href: "announcements.html" }
        ]
    },

    init() {
        this.loadTheme();
        this.renderSidebar();
        this.renderNavbar();
        this.highlightActive();
        this.renderHamburger();
    },

    renderHamburger() {
        if (document.querySelector(".hamburger")) return;
        const btn = document.createElement("button");
        btn.className = "hamburger";
        btn.innerHTML = '<i class="fas fa-bars"></i>';
        btn.onclick = () => this.toggleSidebar();
        document.body.appendChild(btn);

        const overlay = document.createElement("div");
        overlay.className = "sidebar-overlay";
        overlay.onclick = () => this.toggleSidebar();
        document.body.appendChild(overlay);
    },

    toggleSidebar() {
        const sidebar = document.querySelector(".sidebar");
        const overlay = document.querySelector(".sidebar-overlay");
        if (sidebar) sidebar.classList.toggle("active");
        if (overlay) overlay.classList.toggle("active");
    },

    renderSidebar() {
        const sidebar = document.querySelector(".sidebar");
        if (!sidebar) return;

        const user = JSON.parse(localStorage.getItem("acadex_user"));
        const role = user ? user.role : "student";
        const navLinks = this.links[role] || [];

        sidebar.innerHTML = `
            <div class="sidebar-logo">ACADEX<span>.</span></div>
            <nav style="flex: 1;">
                ${navLinks.map(link => `
                    <a href="${link.href}" class="nav-link" id="nav-${link.id}">
                        <span class="nav-icon">${link.icon}</span> ${link.text}
                    </a>
                `).join('')}
            </nav>
            <div style="margin-top: auto; border-top: 2px solid var(--border); padding-top: 1.5rem;">
                <button class="btn btn-secondary" style="width: 100%; border-color: var(--danger); color: var(--danger); display: flex; align-items: center; justify-content: center; gap: 0.5rem;" onclick="authLogout()"><i class="fas fa-sign-out-alt"></i> Log Out</button>
            </div>
        `;
    },

    renderNavbar() {
        const main = document.querySelector(".main-content");
        if (!main) return;

        // Ensure Navbar is present
        let nav = document.querySelector(".navbar");
        if (!nav) {
            nav = document.createElement("header");
            nav.className = "navbar";
            main.insertBefore(nav, main.firstChild);
        }

        const user = JSON.parse(localStorage.getItem("acadex_user")) || { name: "User" };
        const currentTheme = localStorage.getItem("theme") || "light";

        nav.innerHTML = `
            <div class="welcome-text" style="display: flex; gap: 1rem; align-items: center; margin-right: auto;">
                <span style="font-weight: 700; font-size: 0.9rem; opacity: 0.6;">IDENTIFIED USER</span>
                <span style="font-weight: 800; color: var(--primary);">${user.name}</span>
            </div>
            
            <button class="theme-switch" onclick="Layout.toggleTheme()">
                <i class="fas fa-${currentTheme === 'light' ? 'moon' : 'sun'}"></i>
            </button>
            
            <div class="glass-card" style="padding: 0.5rem 1rem; margin: 0; display: flex; align-items: center; gap: 0.5rem; border-width: 2px;">
                <div style="width: 32px; height: 32px; background: var(--primary); border: 2px solid var(--border-bold); display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--text-on-accent);">
                    ${user.name.charAt(0).toUpperCase()}
                </div>
                <div style="flex-direction: column; display: flex;">
                    <div style="font-size: 0.6rem; font-weight: 900; text-transform: uppercase; color: var(--primary);">${user.role}</div>
                </div>
            </div>
        `;
    },

    highlightActive() {
        const path = window.location.pathname;
        const page = path.split("/").pop();
        
        const user = JSON.parse(localStorage.getItem("acadex_user"));
        const role = user ? user.role : "student";
        const navLinks = this.links[role] || [];

        navLinks.forEach(link => {
            if (page === link.href) {
                const el = document.getElementById(`nav-${link.id}`);
                if (el) el.classList.add("active");
            }
        });
    },

    toggleTheme() {
        const current = document.documentElement.getAttribute("data-theme") || "light";
        const target = current === "light" ? "dark" : "light";
        
        document.documentElement.setAttribute("data-theme", target);
        localStorage.setItem("theme", target);
        this.renderNavbar(); // Re-render to update icon
    },

    loadTheme() {
        const theme = localStorage.getItem("theme") || "light";
        document.documentElement.setAttribute("data-theme", theme);
    }
};

// Auto-init on load
document.addEventListener("DOMContentLoaded", () => Layout.init());
