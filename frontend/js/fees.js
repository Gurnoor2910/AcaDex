/**
 * Acadex - Ledger-Based Fees Management Service
 */
const FeesService = {
    /**
     * Admin: Create a new fee ledger record (semester/year)
     */
    async createRecord(studentId, details) {
        return await ApiClient.post("/fees/create-record", { studentId, ...details });
    },

    /**
     * Student: Get full fee ledger including transactions
     */
    async getLedger(studentId = null) {
        const url = studentId ? `/fees/history?studentId=${studentId}` : "/fees/history";
        return await ApiClient.get(url);
    },

    /**
     * Student: Submit a new transaction for a specific record
     */
    async submitTransaction(recordId, amount, method, notes = "") {
        return await ApiClient.post("/fees/pay", { recordId, amount, paymentMethod: method, notes });
    },

    /**
     * Admin: Approve a specific transaction
     */
    async approveTransaction(studentId, recordId, txnId) {
        return await ApiClient.put("/fees/approve-transaction", { studentId, recordId, txnId });
    },

    /**
     * Admin: List all overdue records across system
     */
    async listOverdue() {
        return await ApiClient.get("/fees/overdue");
    },

    /**
     * Helper to get status color class for Records
     */
    getRecordStatus(status) {
        switch (status) {
            case 'paid': return { text: "Paid", color: "#22c55e", bg: "rgba(34, 197, 94, 0.1)" };
            case 'partial': return { text: "Partial", color: "#3b82f6", bg: "rgba(59, 130, 246, 0.1)" };
            case 'pending': return { text: "Reviewing", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)" };
            case 'overdue': return { text: "Overdue", color: "#ef4444", bg: "rgba(239, 68, 68, 0.1)" };
            default: return { text: "Unpaid", color: "#64748b", bg: "rgba(100, 116, 139, 0.1)" };
        }
    },

    /**
     * Helper to get status color class for Transactions
     */
    getTxnStatus(status) {
        switch (status) {
            case 'approved': return { text: "Approved", color: "#22c55e", bg: "rgba(34, 197, 94, 0.1)" };
            case 'rejected': return { text: "Rejected", color: "#ef4444", bg: "rgba(239, 68, 68, 0.1)" };
            default: return { text: "Pending", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)" };
        }
    }
};
