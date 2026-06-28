// Dashboard - 统计概览
import { api } from '../api.js';

export async function renderDashboard(container) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载中...</p></div>';

    try {
        const [overviewRes, dailyRes, storeRes, employeeKpiRes] = await Promise.all([
            api.getOverview(),
            api.getDailyStats(),
            api.getStoreStats(),
            api.getEmployeeKpi(),
        ]);

        const overview = overviewRes.data || {};
        const daily = dailyRes.data || [];
        const storeStats = storeRes.data || [];
        const employeeKpi = employeeKpiRes.data || [];

        container.innerHTML = `
        <!-- Stat Cards -->
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-icon blue">📋</div>
                <div class="stat-info">
                    <div class="stat-label">总反馈数</div>
                    <div class="stat-value">${overview.total_records || 0}</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">😊</div>
                <div class="stat-info">
                    <div class="stat-label">满意率</div>
                    <div class="stat-value">${overview.satisfaction_rate || 0}%</div>
                    <div class="stat-sub">满意 ${overview.satisfied || 0} + 非常满意 ${overview.very_satisfied || 0}</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon yellow">😕</div>
                <div class="stat-info">
                    <div class="stat-label">不满意</div>
                    <div class="stat-value">${overview.unsatisfied || 0}</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon red">😡</div>
                <div class="stat-info">
                    <div class="stat-label">很差</div>
                    <div class="stat-value">${overview.very_bad || 0}</div>
                </div>
            </div>
        </div>

        <div class="dashboard-chart-grid">
            <!-- Satisfaction Distribution -->
            <div class="card">
                <div class="card-title">满意度分布</div>
                <div id="satChart" class="chart-container"></div>
            </div>

            <!-- Daily Trend -->
            <div class="card">
                <div class="card-title">每日反馈趋势</div>
                <div id="trendChart" class="chart-container"></div>
            </div>
        </div>

        <!-- Store Stats Table -->
        <div class="card" style="margin-top:20px;">
            <div class="card-title">门店统计</div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>门店</th>
                            <th>编码</th>
                            <th>反馈数</th>
                            <th>满意率</th>
                            <th>非常满意</th>
                            <th>满意</th>
                            <th>不满意</th>
                            <th>很差</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${storeStats.length === 0 ? '<tr><td colspan="8" class="empty-state">暂无数据</td></tr>' :
                        storeStats.map(s => {
                            const storeName = s.storeName || s.store_name || '-';
                            const storeCode = s.storeCode || s.store_code || '-';
                            const totalRecords = s.totalRecords ?? s.total_records ?? 0;
                            const satisfactionRate = s.satisfactionRate ?? s.satisfaction_rate ?? 0;
                            const satisfactionDistribution = s.satisfactionDistribution || s.satisfaction_distribution || {};
                            return `
                        <tr>
                            <td>${escapeHtml(storeName)}</td>
                            <td>${storeCode}</td>
                            <td><strong>${totalRecords}</strong></td>
                            <td><strong style="color:${satisfactionRate >= 80 ? '#059669' : satisfactionRate >= 50 ? '#D97706' : '#DC2626'}">${satisfactionRate}%</strong></td>
                            <td>${satisfactionDistribution.very_satisfied || 0}</td>
                            <td>${satisfactionDistribution.satisfied || 0}</td>
                            <td>${satisfactionDistribution.unsatisfied || 0}</td>
                            <td>${satisfactionDistribution.very_bad || 0}</td>
                        </tr>`;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card" style="margin-top:20px;">
            <div class="card-title">员工KPI（好评 / 中评 / 差评）</div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>员工</th><th>工号</th><th>总反馈</th><th>好评</th><th>中评</th><th>差评</th><th>好评率</th><th>操作</th></tr></thead>
                    <tbody>
                        ${employeeKpi.length === 0 ? '<tr><td colspan="8" class="empty-state">暂无员工评价数据</td></tr>' : employeeKpi.map(e => `
                        <tr>
                            <td>${escapeHtml(e.employeeName || '-')}</td>
                            <td>${escapeHtml(e.employeeNumber || '-')}</td>
                            <td><strong>${e.total || 0}</strong></td>
                            <td><span class="badge badge-green">${e.good || 0}</span></td>
                            <td><span class="badge badge-yellow">${e.middle || 0}</span></td>
                            <td><span class="badge badge-red">${e.bad || 0}</span></td>
                            <td><strong style="color:${(e.goodRate || 0) >= 80 ? '#059669' : (e.goodRate || 0) >= 50 ? '#D97706' : '#DC2626'}">${e.goodRate || 0}%</strong></td>
                            <td><button class="btn btn-secondary btn-sm employee-records-btn" data-id="${escapeHtml(e.employeeId || '')}" data-name="${escapeHtml(e.employeeName || '')}">评价明细</button></td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        </div>`;

        document.querySelectorAll('.employee-records-btn').forEach(btn => {
            btn.addEventListener('click', () => showEmployeeRecords(btn.dataset.id, btn.dataset.name));
        });

        // Render simple charts (no ECharts dependency - pure canvas)
        renderSatChart(overview);
        renderTrendChart(daily);

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><p>加载失败: ${e.message}</p></div>`;
    }
}

function showEmployeeRecords(employeeId, employeeName) {
    if (!employeeId) return;
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card" style="max-width:820px">
        <div class="modal-header"><h3>${escapeHtml(employeeName || '员工')}评价明细</h3><button class="modal-close" id="empRecClose">&times;</button></div>
        <div class="modal-body">
            <div class="filter-bar">
                <select id="empRecGroup" class="form-input">
                    <option value="">全部评价</option>
                    <option value="good">好评</option>
                    <option value="middle">中评</option>
                    <option value="bad">差评</option>
                </select>
                <button class="btn btn-primary btn-sm" id="empRecSearch">查询</button>
            </div>
            <div id="empRecBody" class="loading"><div class="spinner"></div></div>
        </div>
        <div class="modal-footer"><button class="btn btn-secondary" id="empRecCloseBtn">关闭</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('empRecClose').onclick = close;
    document.getElementById('empRecCloseBtn').onclick = close;
    document.getElementById('empRecSearch').onclick = () => loadEmployeeRecords(employeeId);
    loadEmployeeRecords(employeeId);
}

async function loadEmployeeRecords(employeeId) {
    const body = document.getElementById('empRecBody');
    if (!body) return;
    body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const params = new URLSearchParams({ employee_id: employeeId, page: 1, page_size: 50 });
    const group = document.getElementById('empRecGroup')?.value;
    if (group) params.set('satisfaction_group', group);
    try {
        const res = await api.getEmployeeRecords(params.toString());
        const list = res.data?.list || [];
        body.innerHTML = list.length ? `<div class="table-wrap"><table><thead><tr><th>满意度</th><th>点评/反馈</th><th>时间</th></tr></thead><tbody>${list.map(r => `<tr><td>${satisfactionBadge(r.satisfaction)}</td><td><div>${escapeHtml(r.reviewLong || r.reviewShort || truncate(r.cleanedText || r.rawAsrText || '-', 160))}</div><div class="muted">反馈ID：${escapeHtml(r.id)}</div></td><td>${formatDate(r.createDate)}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty-state">暂无评价明细</div>';
    } catch (e) {
        body.innerHTML = `<div class="empty-state">加载失败：${escapeHtml(e.message)}</div>`;
    }
}

function renderSatChart(overview) {
    const el = document.getElementById('satChart');
    if (!el) return;

    const dist = overview.satisfactionDistribution || overview.satisfaction_distribution || {};
    const data = [
        { label: '非常满意', value: dist.very_satisfied || 0, color: '#059669', bg: '#ECFDF5' },
        { label: '满意', value: dist.satisfied || 0, color: '#10B981', bg: '#F0FDF4' },
        { label: '不满意', value: dist.unsatisfied || 0, color: '#F59E0B', bg: '#FFFBEB' },
        { label: '很差', value: dist.very_bad || 0, color: '#EF4444', bg: '#FEF2F2' },
    ];

    const total = data.reduce((s, d) => s + d.value, 0);
    if (total === 0) {
        el.innerHTML = '<div class="empty-state"><p>暂无满意度数据</p></div>';
        return;
    }

    el.innerHTML = `
        <div class="sat-summary">
            <div class="sat-total">${total}</div>
            <div><div class="sat-total-label">总反馈</div><div class="sat-rate">满意率 ${overview.satisfaction_rate || 0}%</div></div>
        </div>
        <div class="sat-bars">
            ${data.map(d => {
                const percent = total > 0 ? Math.round(d.value / total * 100) : 0;
                return `
                <div class="sat-row">
                    <div class="sat-row-head">
                        <span class="sat-dot" style="background:${d.color}"></span>
                        <span class="sat-name">${d.label}</span>
                        <span class="sat-num">${d.value} · ${percent}%</span>
                    </div>
                    <div class="sat-track" style="background:${d.bg}"><div class="sat-fill" style="width:${percent}%;background:${d.color}"></div></div>
                </div>`;
            }).join('')}
        </div>`;
}

function renderTrendChart(daily) {
    const el = document.getElementById('trendChart');
    if (!el) return;

    if (!daily || daily.length === 0) {
        el.innerHTML = '<div class="empty-state"><p>暂无趋势数据</p></div>';
        return;
    }

    const recent = daily.slice(-14);
    const maxVal = Math.max(...recent.map(d => d.count || 0), 1);
    el.innerHTML = `
        <div class="trend-bars">
            ${recent.map(d => {
                const value = d.count || 0;
                const height = Math.max(8, Math.round(value / maxVal * 150));
                const dateStr = d.date ? d.date.substring(5) : '';
                return `
                <div class="trend-item" title="${dateStr}: ${value}">
                    <div class="trend-value">${value}</div>
                    <div class="trend-bar-wrap"><div class="trend-bar" style="height:${height}px"></div></div>
                    <div class="trend-date">${dateStr}</div>
                </div>`;
            }).join('')}
        </div>`;
}
