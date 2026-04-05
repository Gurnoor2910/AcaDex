/**
 * Acadex Faculty Management Service
 * Handles interaction with the Faculty API
 */

const FacultyService = {
    async loadAll(containerId) {
        const container = document.getElementById(containerId);
        try {
            const faculty = await ApiClient.get("/admin/get-faculty");
            if (!faculty || faculty.length === 0) {
                container.innerHTML = '<tr><td colspan="5" style="text-align: center;">No faculty registered.</td></tr>';
                return;
            }
            container.innerHTML = faculty.map(f => `
                <tr>
                    <td style="font-family: monospace; font-weight: 800;">#${(f.uid || '').substring(0, 8)}</td>
                    <td style="font-weight: 800; text-transform: uppercase;">${f.name}</td>
                    <td style="font-size: 0.85rem; font-weight: 600;">${f.email}</td>
                    <td><span class="status-pill pill-primary">${(f.department || 'GENERAL').toUpperCase()}</span></td>
                    <td style="text-align: right;">
                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                           <button onclick="openEditModal(${JSON.stringify(f).replace(/"/g, '&quot;')})" class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.7rem;">ADJUST</button>
                           <button onclick="deleteFaculty('${f.uid}')" class="btn btn-secondary" style="border-color: var(--danger); color: var(--danger); padding: 0.4rem 0.8rem; font-size: 0.7rem;">REMOVE</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Faculty load error:", err);
            container.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger);">Error fetching faculty directory.</td></tr>';
        }
    },

    async register(data) {
        return await ApiClient.post("/admin/add-faculty", data);
    },

    async delete(id) {
        return await ApiClient.request(`/admin/delete-faculty?facultyId=${id}`, { method: 'DELETE' });
    }
};
