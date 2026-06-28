// Main Admin SPA Application
import { api } from './api.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderRecords } from './pages/records.js?v=20260625-records-fix';
import { renderStores } from './pages/stores.js';
import { renderEmployees } from './pages/employees.js';
import { renderAgentConfigs } from './pages/agent-configs.js';
import { renderCrm } from './pages/crm.js';
import { initAiAssistant } from './ai-assistant.js?v=20260625-longchat-default';
import './form-copilot.js';

// ---- Router ----
function getRoute() {
    const hash = window.location.hash || '#/dashboard';
    const [path] = hash.substring(2).split('?');
    return path;
}

function navigate(route) {
    window.location.hash = `#/${route}`;
}

// ---- Auth Check ----
function isLoggedIn() {
    return !!api.token;
}

function getNavItems() {
    const items = [
        { route: 'dashboard', icon: '📊', label: '统计概览' },
        { route: 'crm', icon: '💎', label: 'CRM管理' },
        { route: 'records', icon: '📋', label: '反馈记录' },
        { route: 'employees', icon: '👥', label: '员工管理' },
    ];
    if (!api.isStoreManager) {
        items.splice(2, 0, { route: 'stores', icon: '🏪', label: '门店管理' });
        items.push({ route: 'agent-configs', icon: '🤖', label: '智能体配置' });
    }
    return items;
}

// ---- Render App Shell ----
function renderApp() {
    let route = getRoute();
    const app = document.getElementById('app');

    if (!isLoggedIn()) {
        renderLogin(app);
        return;
    }

    const username = localStorage.getItem('feedback_admin_user') || 'admin';
    const displayName = localStorage.getItem('feedback_admin_display_name') || username;
    const storeName = localStorage.getItem('feedback_admin_store_name') || '';
    const navItems = getNavItems();
    if (!navItems.some(i => i.route === route)) {
        route = 'dashboard';
        window.location.hash = '#/dashboard';
    }

    app.innerHTML = `
    <div class="layout">
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-brand">
                <h1>反馈系统</h1>
                <p>${api.isStoreManager ? (storeName || '店长后台') : '管理后台'} v1.0</p>
            </div>
            <nav class="sidebar-nav">
                ${navItems.map(item => `
                    <a class="nav-item ${route === item.route ? 'active' : ''}" href="#/${item.route}">
                        <span class="icon">${item.icon}</span>
                        <span>${item.label}</span>
                    </a>
                `).join('')}
            </nav>
            <div class="sidebar-footer">
                <div>${escapeHtml(displayName)}</div>
                <div>${api.isStoreManager ? '店长账号' : '管理员'}</div>
                <a href="#" id="changePasswordLink">改密码</a> &middot; <a href="#" id="logoutLink">退出</a>
            </div>
        </aside>
        <div class="main">
            <header class="topbar">
                <button class="mobile-menu-btn" id="mobileMenuBtn">☰</button>
                <div class="topbar-title" id="pageTitle">${navItems.find(i => i.route === route)?.label || ''}</div>
                <div class="topbar-actions">
                    <button class="notify-btn" id="notifyBtn">🔔<span id="notifyBadge" class="notify-badge" style="display:none">0</span></button>
                    <div class="topbar-user">${escapeHtml(displayName)}</div>
                </div>
            </header>
            <div class="content" id="pageContent"></div>
        </div>
    </div>`;

    document.getElementById('logoutLink').addEventListener('click', (e) => {
        e.preventDefault();
        api.logout();
        renderApp();
    });
    document.getElementById('changePasswordLink').addEventListener('click', (e) => {
        e.preventDefault();
        showChangePasswordDialog();
    });
    document.getElementById('mobileMenuBtn')?.addEventListener('click', () => {
        document.getElementById('sidebar')?.classList.toggle('open');
    });
    document.querySelectorAll('.nav-item').forEach(a => {
        a.addEventListener('click', () => document.getElementById('sidebar')?.classList.remove('open'));
    });

    initAiAssistant();
    document.getElementById('notifyBtn')?.addEventListener('click', showNotificationsDialog);
    loadNotificationBadge();

    const content = document.getElementById('pageContent');
    switch (route) {
        case 'dashboard': renderDashboard(content); break;
        case 'crm': renderCrm(content); break;
        case 'records': renderRecords(content); break;
        case 'stores': renderStores(content); break;
        case 'employees': renderEmployees(content); break;
        case 'agent-configs': renderAgentConfigs(content); break;
        default: renderDashboard(content);
    }
}

async function loadNotificationBadge() {
    try {
        const res = await api.getNotifications('page=1&page_size=5&status=unread');
        const unread = res.data?.unread || 0;
        const badge = document.getElementById('notifyBadge');
        if (badge) {
            badge.textContent = unread > 99 ? '99+' : String(unread);
            badge.style.display = unread > 0 ? '' : 'none';
        }
    } catch (e) {}
}

async function showNotificationsDialog() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card notify-modal">
        <div class="modal-header"><h3>通知消息</h3><button class="modal-close" id="notifyClose">&times;</button></div>
        <div class="modal-body" id="notifyBody"><div class="loading"><div class="spinner"></div></div></div>
        <div class="modal-footer"><button class="btn btn-secondary" id="notifyReadAll">全部已读</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('notifyClose').addEventListener('click', close);
    document.getElementById('notifyReadAll').addEventListener('click', async () => {
        await api.markAllNotificationsRead();
        await loadNotificationBadge();
        close();
    });
    try {
        const res = await api.getNotifications('page=1&page_size=30');
        const list = res.data?.list || [];
        document.getElementById('notifyBody').innerHTML = list.length ? list.map(n => `
            <button class="notify-item ${n.status === 'unread' ? 'unread' : ''}" data-id="${n.id}" data-route="${n.targetRoute || ''}">
                <strong>${escapeHtml(n.title)}</strong>
                <span>${escapeHtml(n.content || '')}</span>
                <small>${formatDate(n.createDate)}</small>
            </button>`).join('') : '<div class="empty-state">暂无通知</div>';
        document.querySelectorAll('.notify-item').forEach(btn => {
            btn.addEventListener('click', async () => {
                await api.markNotificationRead(btn.dataset.id);
                await loadNotificationBadge();
                close();
                if (btn.dataset.route === 'crm:appointments') {
                    window.location.hash = '#/crm?tab=appointments';
                }
            });
        });
    } catch (e) {
        document.getElementById('notifyBody').innerHTML = `<div class="empty-state">加载通知失败：${escapeHtml(e.message || '')}</div>`;
    }
}

// ---- Login Page ----
function renderLogin(container) {
    container.innerHTML = `
    <div class="login-page">
        <div class="login-card">
            <h1>反馈系统</h1>
            <p>管理后台登录</p>
            <div class="form-group">
                <input type="text" id="loginUser" class="form-input" placeholder="管理员账号 / 门店编码">
            </div>
            <div class="form-group">
                <input type="password" id="loginPass" class="form-input" placeholder="密码">
            </div>
            <button class="btn btn-primary" id="loginBtn">登 录</button>
            <div class="login-tip">店长首次登录：门店编码 / 门店编码</div>
            <div class="login-error" id="loginError"></div>
        </div>
    </div>`;

    const doLogin = async () => {
        const u = document.getElementById('loginUser').value.trim();
        const p = document.getElementById('loginPass').value;
        const errEl = document.getElementById('loginError');
        errEl.textContent = '';
        try {
            await api.login(u, p);
            renderApp();
        } catch (e) {
            errEl.textContent = '用户名或密码错误';
        }
    };

    document.getElementById('loginBtn').addEventListener('click', doLogin);
    document.getElementById('loginPass').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') doLogin();
    });
}

function showChangePasswordDialog() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card">
        <div class="modal-header">
            <h3>修改密码</h3>
            <button class="modal-close" id="closePwd">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-group"><label class="form-label">原密码</label><input type="password" id="oldPwd" class="form-input"></div>
            <div class="form-group"><label class="form-label">新密码</label><input type="password" id="newPwd" class="form-input" placeholder="至少 6 位"></div>
            <div class="form-group"><label class="form-label">确认新密码</label><input type="password" id="newPwd2" class="form-input"></div>
            <div class="login-error" id="pwdError"></div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelPwd">取消</button>
            <button class="btn btn-primary" id="savePwd">保存</button>
        </div>
    </div>`;
    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('closePwd').addEventListener('click', close);
    document.getElementById('cancelPwd').addEventListener('click', close);
    document.getElementById('savePwd').addEventListener('click', async () => {
        const oldPwd = document.getElementById('oldPwd').value;
        const newPwd = document.getElementById('newPwd').value;
        const newPwd2 = document.getElementById('newPwd2').value;
        const err = document.getElementById('pwdError');
        err.textContent = '';
        if (newPwd.length < 6) { err.textContent = '新密码至少 6 位'; return; }
        if (newPwd !== newPwd2) { err.textContent = '两次新密码不一致'; return; }
        try {
            await api.changePassword(oldPwd, newPwd);
            alert('密码已修改，请重新登录');
            api.logout();
            close();
            renderApp();
        } catch (e) {
            err.textContent = e.message || '修改失败';
        }
    });
}

// ---- Helpers (global) ----
window.escapeHtml = function(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
};

window.formatDate = function(d) {
    if (!d) return '-';
    return d.replace('T', ' ').substring(0, 19);
};

window.satisfactionBadge = function(s) {
    const map = {
        very_satisfied: { label: '非常满意', cls: 'badge-green' },
        satisfied: { label: '满意', cls: 'badge-green' },
        unsatisfied: { label: '不满意', cls: 'badge-yellow' },
        very_bad: { label: '很差', cls: 'badge-red' },
    };
    const info = map[s] || { label: s || '-', cls: 'badge-gray' };
    return `<span class="badge ${info.cls}">${info.label}</span>`;
};

window.statusBadge = function(s) {
    return s === 1
        ? '<span class="badge badge-green">启用</span>'
        : '<span class="badge badge-red">禁用</span>';
};

window.employeeTypeBadge = function(t) {
    const map = {
        manager: { label: '店长', cls: 'badge-blue' },
        excellent: { label: '优秀员工', cls: 'badge-green' },
        intern: { label: '实习生', cls: 'badge-yellow' },
        normal: { label: '普通员工', cls: 'badge-gray' },
    };
    const info = map[t] || { label: t, cls: 'badge-gray' };
    return `<span class="badge ${info.cls}">${info.label}</span>`;
};

window.truncate = function(s, len = 50) {
    if (!s) return '-';
    return s.length > len ? s.substring(0, len) + '...' : s;
};

// ---- Init ----
window.addEventListener('hashchange', renderApp);
window.addEventListener('load', renderApp);
