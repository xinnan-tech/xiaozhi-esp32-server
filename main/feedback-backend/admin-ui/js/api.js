// Admin API Client
const API_BASE = window.location.hostname === 'feedback-admin.new123.vip'
    ? 'https://feedback-admin.new123.vip:8443/api/v1'
    : window.location.origin + '/api/v1';

class AdminAPI {
    constructor() {
        this.token = localStorage.getItem('feedback_admin_token');
    }

    // ---- Auth ----
    async login(username, password) {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (!res.ok) throw new Error('Login failed');
        const data = await res.json();
        this.token = data.access_token;
        localStorage.setItem('feedback_admin_token', data.access_token);
        localStorage.setItem('feedback_admin_user', data.username);
        localStorage.setItem('feedback_admin_role', data.role || 'super_admin');
        localStorage.setItem('feedback_admin_display_name', data.display_name || data.username);
        if (data.store_id) localStorage.setItem('feedback_admin_store_id', data.store_id);
        else localStorage.removeItem('feedback_admin_store_id');
        if (data.store_code) localStorage.setItem('feedback_admin_store_code', data.store_code);
        else localStorage.removeItem('feedback_admin_store_code');
        if (data.store_name) localStorage.setItem('feedback_admin_store_name', data.store_name);
        else localStorage.removeItem('feedback_admin_store_name');
        return data;
    }

    logout() {
        this.token = null;
        localStorage.removeItem('feedback_admin_token');
        localStorage.removeItem('feedback_admin_user');
        localStorage.removeItem('feedback_admin_role');
        localStorage.removeItem('feedback_admin_display_name');
        localStorage.removeItem('feedback_admin_store_id');
        localStorage.removeItem('feedback_admin_store_code');
        localStorage.removeItem('feedback_admin_store_name');
    }

    get role() {
        return localStorage.getItem('feedback_admin_role') || 'super_admin';
    }

    get isStoreManager() {
        return this.role === 'store_manager';
    }

    get storeId() {
        return localStorage.getItem('feedback_admin_store_id') || '';
    }

    get headers() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
        };
    }

    async request(url, options = {}) {
        const res = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers: { ...this.headers, ...options.headers }
        });
        if (res.status === 401) {
            this.logout();
            window.location.reload();
            throw new Error('Unauthorized');
        }
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try {
                const data = await res.json();
                msg = data.detail || data.msg || msg;
            } catch (e) {}
            throw new Error(msg);
        }
        return res.json();
    }

    async changePassword(oldPassword, newPassword) {
        return this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
        });
    }

    // ---- Stats ----
    async getOverview(params = '') {
        return this.request(`/stats/overview${params ? '?' + params : ''}`);
    }

    async getDailyStats(params = '') {
        return this.request(`/stats/daily${params ? '?' + params : ''}`);
    }

    async getStoreStats(params = '') {
        return this.request(`/stats/by-store${params ? '?' + params : ''}`);
    }

    async getEmployeeKpi(params = '') {
        return this.request(`/stats/employee-kpi${params ? '?' + params : ''}`);
    }

    async getEmployeeRecords(params = '') {
        return this.request(`/stats/employee-records${params ? '?' + params : ''}`);
    }

    // ---- Records ----
    async getRecords(params = '') {
        return this.request(`/record/list${params ? '?' + params : ''}`);
    }

    // ---- CRM ----
    async getCrmOverview() { return this.request('/crm/overview'); }
    async getMekai66Fields() { return this.request('/crm/mekai66-fields'); }
    async getCrmMembers(params = '') { return this.request(`/crm/member/list${params ? '?' + params : ''}`); }
    async getCrmMember(id) { return this.request(`/crm/member/${id}`); }
    async createCrmMember(data) { return this.request('/crm/member', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async updateCrmMember(id, data) { return this.request(`/crm/member/${id}`, { method: 'PUT', body: JSON.stringify({ data }) }); }
    async getCrmVisits(params = '') { return this.request(`/crm/visit/list${params ? '?' + params : ''}`); }
    async createCrmVisit(data) { return this.request('/crm/visit', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async updateCrmVisit(id, data) { return this.request(`/crm/visit/${id}`, { method: 'PUT', body: JSON.stringify({ data }) }); }
    async getCrmAccounts(params = '') { return this.request(`/crm/account/list${params ? '?' + params : ''}`); }
    async getCrmAccountTransactions(params = '') { return this.request(`/crm/account/transactions${params ? '?' + params : ''}`); }
    async createCrmAccount(data) { return this.request('/crm/account', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async consumeCrmAccount(id, data) { return this.request(`/crm/account/${id}/consume`, { method: 'POST', body: JSON.stringify({ data }) }); }
    async closeCrmCard(data) { return this.request('/crm/card-close', { method: 'POST', body: JSON.stringify({ data }) }); }
    async getCrmCardCloses(params = '') { return this.request(`/crm/card-close/list${params ? '?' + params : ''}`); }
    // ---- Appointment ----
    async getAppointmentCalendar(params = '') { return this.request(`/appointment/calendar${params ? '?' + params : ''}`); }
    async getAppointmentAvailability(params = '') { return this.request(`/appointment/availability${params ? '?' + params : ''}`); }
    async createAppointment(data) { return this.request('/appointment', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async confirmAppointment(id, data = {}) { return this.request(`/appointment/${id}/confirm`, { method: 'POST', body: JSON.stringify({ data }) }); }
    async cancelAppointment(id, data = {}) { return this.request(`/appointment/${id}/cancel`, { method: 'POST', body: JSON.stringify({ data }) }); }
    async completeAppointment(id, data = {}) { return this.request(`/appointment/${id}/complete`, { method: 'POST', body: JSON.stringify({ data }) }); }

    async getCrmBodyStatuses(params = '') { return this.request(`/crm/body-status/list${params ? '?' + params : ''}`); }
    async createCrmBodyStatus(data) { return this.request('/crm/body-status', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }

    async getCrmProducts(params = '') { return this.request(`/crm/product/list${params ? '?' + params : ''}`); }
    async createCrmProduct(data) { return this.request('/crm/product', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async getCrmMemberProducts(params = '') { return this.request(`/crm/member-product/list${params ? '?' + params : ''}`); }
    async purchaseCrmProduct(data) { return this.request('/crm/member-product/purchase', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async consumeCrmProduct(id, data) { return this.request(`/crm/member-product/${id}/consume`, { method: 'POST', body: JSON.stringify({ data }) }); }
    async getCrmProductConsumes(params = '') { return this.request(`/crm/product-consume/list${params ? '?' + params : ''}`); }

    async getCrmSuggestions(params = '') { return this.request(`/crm/suggestion/list${params ? '?' + params : ''}`); }
    async createCrmSuggestion(data) { return this.request('/crm/suggestion', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async updateCrmSuggestionStatus(id, data) { return this.request(`/crm/suggestion/${id}/status`, { method: 'POST', body: JSON.stringify({ data }) }); }
    async getCrmIssues(params = '') { return this.request(`/crm/issue/list${params ? '?' + params : ''}`); }
    async createCrmIssue(data) { return this.request('/crm/issue', { method: 'POST', body: JSON.stringify({ data: this.withStore(data) }) }); }
    async updateCrmIssue(id, data) { return this.request(`/crm/issue/${id}`, { method: 'PUT', body: JSON.stringify({ data }) }); }
    async bindCrmFeedback(id, data) { return this.request(`/crm/feedback/${id}/bind`, { method: 'POST', body: JSON.stringify({ data }) }); }

    // ---- AI Agent ----
    async agentChat(message, history = []) {
        return this.request('/agent/chat', {
            method: 'POST',
            body: JSON.stringify({ message, history })
        });
    }

    async agentFeedback(data) {
        return this.request('/agent/feedback', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // ---- Notifications ----
    async getNotifications(params = '') {
        return this.request(`/notification/list${params ? '?' + params : ''}`);
    }

    async markNotificationRead(id) {
        return this.request(`/notification/${id}/read`, { method: 'POST' });
    }

    async markAllNotificationsRead() {
        return this.request('/notification/read-all', { method: 'POST' });
    }

    withStore(data) {
        if (this.isStoreManager && this.storeId && !data.storeId && !data.store_id) return { ...data, storeId: this.storeId };
        return data;
    }

    // ---- Stores ----
    async getStores(params = '') {
        return this.request(`/store/list${params ? '?' + params : ''}`);
    }

    async createStore(data) {
        return this.request('/store', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateStore(id, data) {
        return this.request(`/store/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteStore(id) {
        return this.request(`/store/delete?store_id=${id}`, { method: 'POST' });
    }

    // ---- Employees ----
    async getEmployees(params = '') {
        return this.request(`/employee/list${params ? '?' + params : ''}`);
    }

    async createEmployee(data) {
        return this.request('/employee', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateEmployee(id, data) {
        return this.request(`/employee/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteEmployee(id) {
        return this.request(`/employee/delete?employee_id=${id}`, { method: 'POST' });
    }

    // ---- Agent Config ----
    async getAgentConfigs(params = '') {
        return this.request(`/agent-config/list${params ? '?' + params : ''}`);
    }

    async createAgentConfig(data) {
        return this.request('/agent-config', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateAgentConfig(id, data) {
        return this.request(`/agent-config/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteAgentConfig(id) {
        return this.request(`/agent-config/delete?config_id=${id}`, { method: 'POST' });
    }
}

export const api = new AdminAPI();
