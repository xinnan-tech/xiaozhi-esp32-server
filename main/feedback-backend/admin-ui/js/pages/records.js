// Records - 反馈记录列表
import { api } from '../api.js';

let currentPage = 1;
const pageSize = 20;

export async function renderRecords(container) {
    container.innerHTML = `
    <div class="card">
        <div class="filter-bar">
            <select id="filterStore" class="form-input" style="width:180px"><option value="">全部门店</option></select>
            <select id="filterEmployee" class="form-input" style="width:160px"><option value="">全部员工</option></select>
            <select id="filterSatisfaction" class="form-input">
                <option value="">全部满意度</option>
                <option value="very_satisfied">非常满意</option>
                <option value="satisfied">满意</option>
                <option value="unsatisfied">不满意</option>
                <option value="very_bad">很差</option>
            </select>
            <input type="date" id="filterStart" class="form-input" style="width:150px">
            <input type="date" id="filterEnd" class="form-input" style="width:150px">
            <button class="btn btn-primary btn-sm" id="filterBtn">查询</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th style="width:40px">#</th>
                        <th>门店</th>
                        <th>客户</th>
                        <th>满意度</th>
                        <th>原始文本</th>
                        <th>清洗文本</th>
                        <th>点评</th>
                        <th>时间</th>
                        <th style="width:60px">操作</th>
                    </tr>
                </thead>
                <tbody id="recordsBody">
                    <tr><td colspan="9" class="loading"><div class="spinner"></div></td></tr>
                </tbody>
            </table>
        </div>
        <div id="pagination" class="pagination"></div>
    </div>`;

    document.getElementById('filterBtn').addEventListener('click', () => {
        currentPage = 1;
        loadRecords();
    });
    document.getElementById('filterStore').addEventListener('change', async () => {
        await loadEmployeeOptions(document.getElementById('filterStore').value);
    });

    loadFilterOptions().then(loadRecords);
}

async function loadFilterOptions() {
    const storeSelect = document.getElementById('filterStore');
    if (!storeSelect) return;
    if (api.isStoreManager) {
        const storeId = api.storeId;
        const storeName = localStorage.getItem('feedback_admin_store_name') || storeId;
        storeSelect.innerHTML = `<option value="${escapeHtml(storeId)}">${escapeHtml(storeName)}</option>`;
        storeSelect.value = storeId;
        storeSelect.disabled = true;
        await loadEmployeeOptions(storeId);
        return;
    }
    try {
        const res = await api.getStores('page=1&page_size=100');
        const stores = res.data?.list || [];
        storeSelect.innerHTML = '<option value="">全部门店</option>' + stores.map(s => `<option value="${s.id}">${escapeHtml(s.storeName || s.store_name || s.id)}</option>`).join('');
    } catch (e) {
        storeSelect.innerHTML = '<option value="">全部门店</option>';
    }
    await loadEmployeeOptions('');
}

async function loadEmployeeOptions(storeId = '') {
    const empSelect = document.getElementById('filterEmployee');
    if (!empSelect) return;
    const params = new URLSearchParams({ page: 1, page_size: 100 });
    if (storeId) params.set('store_id', storeId);
    try {
        const res = await api.getEmployees(params.toString());
        const employees = res.data?.list || [];
        empSelect.innerHTML = '<option value="">全部员工</option>' + employees.map(e => `<option value="${e.id}">${escapeHtml(e.name || e.id)}${e.number ? `（${e.number}号）` : ''}</option>`).join('');
    } catch (e) {
        empSelect.innerHTML = '<option value="">全部员工</option>';
    }
}

async function loadRecords() {
    const tbody = document.getElementById('recordsBody');
    if (!tbody) return;

    const storeId = document.getElementById('filterStore')?.value || '';
    const employeeId = document.getElementById('filterEmployee')?.value || '';
    const satisfaction = document.getElementById('filterSatisfaction')?.value || '';
    const startDate = document.getElementById('filterStart')?.value || '';
    const endDate = document.getElementById('filterEnd')?.value || '';

    const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
    });
    if (storeId) params.set('store_id', storeId);
    if (employeeId) params.set('employee_id', employeeId);
    if (satisfaction) params.set('satisfaction', satisfaction);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);

    try {
        const res = await api.getRecords(params.toString());
        const data = res.data || {};

        if (!data.list || data.list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><div class="icon">📋</div><p>暂无反馈记录</p></td></tr>';
            return;
        }

        tbody.innerHTML = data.list.map((r, i) => `
        <tr>
            <td>${(currentPage - 1) * pageSize + i + 1}</td>
            <td><strong>${escapeHtml(r.storeName || r.storeId || '-')}</strong></td>
            <td>${renderCustomerCell(r)}</td>
            <td>${satisfactionBadge(r.satisfaction)}</td>
            <td title="${escapeHtml(r.rawAsrText)}">${truncate(r.rawAsrText, 40)}</td>
            <td title="${escapeHtml(r.cleanedText)}">${truncate(r.cleanedText, 40)}</td>
            <td title="${escapeHtml(r.reviewLong)}">${r.reviewLong ? '✅ ' + truncate(r.reviewLong, 30) : '-'}</td>
            <td style="white-space:nowrap">${formatDate(r.createDate)}</td>
            <td><button class="btn btn-secondary btn-sm view-record-btn" data-id="${r.id}">详情</button></td>
        </tr>`).join('');

        // Detail buttons
        tbody.querySelectorAll('.view-record-btn').forEach(btn => {
            btn.addEventListener('click', () => showRecordDetail(btn.dataset.id, data.list));
        });

        // Pagination
        renderPagination(data);

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state"><p>加载失败: ${e.message}</p></td></tr>`;
    }
}

function renderPagination(data) {
    const el = document.getElementById('pagination');
    if (!el) return;

    const total = data.total || 0;
    const totalPages = Math.ceil(total / pageSize);

    el.innerHTML = `
        <div class="pagination-info">共 ${total} 条记录，第 ${currentPage}/${totalPages || 1} 页</div>
        <div class="pagination-btns">
            <button ${currentPage <= 1 ? 'disabled' : ''} id="prevPage">上一页</button>
            <button class="active">${currentPage}</button>
            <button ${currentPage >= totalPages ? 'disabled' : ''} id="nextPage">下一页</button>
        </div>`;

    document.getElementById('prevPage')?.addEventListener('click', () => {
        if (currentPage > 1) { currentPage--; loadRecords(); }
    });
    document.getElementById('nextPage')?.addEventListener('click', () => {
        if (currentPage < totalPages) { currentPage++; loadRecords(); }
    });
}

function renderCustomerCell(r) {
    const name = r.memberName || r.customerName || '-';
    const phone = r.memberPhone ? maskPhone(r.memberPhone) : (r.phoneTail ? `尾号${r.phoneTail}` : '');
    const status = r.memberMatchStatus === 'conflict'
        ? '<div class="muted" style="color:#D97706">尾号冲突，按称呼区分</div>'
        : r.memberMatchStatus === 'not_found'
            ? '<div class="muted" style="color:#DC2626">未匹配客户档案</div>'
            : '';
    return `<strong>${escapeHtml(name)}</strong>${phone ? `<div class="muted">${escapeHtml(phone)}</div>` : ''}${status}`;
}

function maskPhone(phone) {
    const s = String(phone || '');
    return s.length >= 7 ? `${s.slice(0, 3)}****${s.slice(-4)}` : s;
}

function renderCustomerDetail(r) {
    const candidates = r.memberMatchCandidates || [];
    const candidateText = candidates.length
        ? candidates.map(c => `${c.name || '-'} ${maskPhone(c.phone || '')}${c.nickname ? `（${c.nickname}）` : ''}`).join('；')
        : '-';
    const statusMap = { matched: '已匹配', conflict: '尾号冲突', not_found: '未匹配' };
    return `${escapeHtml(r.memberName || r.customerName || '-')}
        ${r.memberPhone ? ` <span class="muted">${escapeHtml(maskPhone(r.memberPhone))}</span>` : r.phoneTail ? ` <span class="muted">尾号${escapeHtml(r.phoneTail)}</span>` : ''}
        <div class="muted">匹配状态：${escapeHtml(statusMap[r.memberMatchStatus] || '-')}</div>
        <div class="muted">候选客户：${escapeHtml(candidateText)}</div>`;
}

function showRecordDetail(id, records) {
    const r = records.find(rec => rec.id === id);
    if (!r) return;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card">
        <div class="modal-header">
            <h3>反馈记录详情</h3>
            <button class="modal-close" id="closeDetail">&times;</button>
        </div>
        <div class="modal-body">
            <div class="detail-row"><div class="detail-label">ID</div><div class="detail-value">${escapeHtml(r.id)}</div></div>
            <div class="detail-row"><div class="detail-label">会话ID</div><div class="detail-value">${escapeHtml(r.sessionId || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">门店</div><div class="detail-value">${escapeHtml(r.storeName || r.storeId || '-')} <span class="muted">${escapeHtml(r.storeId || '')}</span></div></div>
            <div class="detail-row"><div class="detail-label">员工</div><div class="detail-value">${escapeHtml(r.employeeName || '-')} ${r.employeeNumber ? `（${r.employeeNumber}号）` : ''} <span class="muted">${escapeHtml(r.employeeId || '')}</span></div></div>
            <div class="detail-row"><div class="detail-label">客户</div><div class="detail-value">${renderCustomerDetail(r)}</div></div>
            <div class="detail-row"><div class="detail-label">设备MAC</div><div class="detail-value">${escapeHtml(r.deviceMac || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">满意度</div><div class="detail-value">${satisfactionBadge(r.satisfaction)}</div></div>
            <div class="detail-row"><div class="detail-label">原始文本</div><div class="detail-value" style="white-space:pre-wrap">${escapeHtml(r.rawAsrText || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">清洗文本</div><div class="detail-value" style="white-space:pre-wrap">${escapeHtml(r.cleanedText || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">QA结果</div><div class="detail-value" style="white-space:pre-wrap;font-size:12px">${escapeHtml(r.qaJson || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">标准点评</div><div class="detail-value" style="color:#059669">${escapeHtml(r.reviewLong || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">精简短评</div><div class="detail-value" style="color:#059669">${escapeHtml(r.reviewShort || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">创建时间</div><div class="detail-value">${formatDate(r.createDate)}</div></div>
            <div class="detail-row"><div class="detail-label">CRM绑定</div><div class="detail-value">客户：${escapeHtml(r.memberId || '-')}　到店：${escapeHtml(r.visitId || '-')}　销卡：${escapeHtml(r.cardCloseId || '-')}</div></div>
            <div class="detail-row"><div class="detail-label">CRM操作</div><div class="detail-value">
                <button class="btn btn-secondary btn-sm" id="bindMemberBtn">绑定客户/到店</button>
                <button class="btn btn-primary btn-sm" id="createSuggestionBtn">创建建议</button>
                <button class="btn btn-danger btn-sm" id="createIssueBtn">创建问题</button>
            </div></div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" id="closeDetailBtn">关闭</button>
        </div>
    </div>`;

    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('closeDetail').addEventListener('click', close);
    document.getElementById('closeDetailBtn').addEventListener('click', close);
    document.getElementById('bindMemberBtn').addEventListener('click', () => showBindFeedbackDialog(r));
    document.getElementById('createSuggestionBtn').addEventListener('click', () => showCreateSuggestionDialog(r));
    document.getElementById('createIssueBtn').addEventListener('click', () => showCreateIssueDialog(r));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
}

function showSmallModal(title, body, onSave) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card">
        <div class="modal-header"><h3>${title}</h3><button class="modal-close">&times;</button></div>
        <div class="modal-body">${body}<div class="login-error" id="recordCrmError"></div></div>
        <div class="modal-footer"><button class="btn btn-secondary" id="recordCrmCancel">取消</button><button class="btn btn-primary" id="recordCrmSave">保存</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    overlay.querySelector('.modal-close').onclick = close;
    overlay.querySelector('#recordCrmCancel').onclick = close;
    overlay.querySelector('#recordCrmSave').onclick = async () => {
        try { await onSave(); close(); alert('操作成功'); }
        catch (e) { document.getElementById('recordCrmError').textContent = e.message || '操作失败'; }
    };
}

function inputVal(id) { return document.getElementById(id)?.value.trim(); }
function memberPicker(prefix, label = '客户') {
    return `<div class="form-group member-combobox" id="${prefix}MemberBox"><label class="form-label">${label}</label><input id="${prefix}MemberKeyword" class="form-input" autocomplete="off" placeholder="输入姓名/手机号搜索并选择"><input id="${prefix}Member" type="hidden"><div id="${prefix}MemberDropdown" class="member-dropdown"></div><input id="${prefix}MemberManual" class="form-input member-manual" placeholder="客户ID备用输入（可选）"></div>`;
}
function pickedMember(prefix) { return inputVal(`${prefix}Member`) || inputVal(`${prefix}MemberManual`); }
function fillMemberPicker(prefix, defaultMemberId = '') {
    const input = document.getElementById(`${prefix}MemberKeyword`);
    const dropdown = document.getElementById(`${prefix}MemberDropdown`);
    const idEl = document.getElementById(`${prefix}Member`);
    const manualEl = document.getElementById(`${prefix}MemberManual`);
    if (defaultMemberId && manualEl) manualEl.value = defaultMemberId;
    if (!input || !dropdown || !idEl) return;
    let timer = null;
    const search = async () => {
        const kw = input.value.trim();
        idEl.value = '';
        if (!kw) { dropdown.innerHTML = ''; dropdown.classList.remove('open'); return; }
        try {
            const res = await api.getCrmMembers(new URLSearchParams({ page: 1, page_size: 10, keyword: kw }).toString());
            const list = res.data?.list || [];
            dropdown.innerHTML = list.length ? list.map(m => `<div class="member-option" data-id="${m.id}" data-label="${escapeHtml((m.name || '-') + ' · ' + (m.phone || '-'))}"><strong>${escapeHtml(m.name || '-')}</strong><span>${escapeHtml(m.phone || '-')}</span></div>`).join('') : '<div class="member-option disabled">未找到客户</div>';
            dropdown.classList.add('open');
            dropdown.querySelectorAll('.member-option[data-id]').forEach(opt => opt.onclick = () => {
                idEl.value = opt.dataset.id;
                input.value = opt.dataset.label;
                if (manualEl) manualEl.value = '';
                dropdown.classList.remove('open');
                input.dispatchEvent(new CustomEvent('member-selected', { detail: { id: opt.dataset.id } }));
            });
        } catch (e) { dropdown.innerHTML = `<div class="member-option disabled">搜索失败：${escapeHtml(e.message)}</div>`; dropdown.classList.add('open'); }
    };
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 250); });
    input.addEventListener('focus', () => { if (dropdown.innerHTML) dropdown.classList.add('open'); });
    document.addEventListener('click', (e) => { if (!e.target.closest(`#${prefix}MemberBox`)) dropdown.classList.remove('open'); });
}

function showBindFeedbackDialog(r) {
    showSmallModal('绑定反馈到CRM', `
        ${memberPicker('bind', '选择客户')}
        <div class="form-group"><label class="form-label">到店记录ID</label><input id="bindVisitId" class="form-input" value="${escapeHtml(r.visitId || '')}"></div>
        <div class="form-group"><label class="form-label">销卡记录ID</label><input id="bindCardCloseId" class="form-input" value="${escapeHtml(r.cardCloseId || '')}"></div>`,
        () => api.bindCrmFeedback(r.id, { memberId: pickedMember('bind'), visitId: inputVal('bindVisitId'), cardCloseId: inputVal('bindCardCloseId') })
    );
    fillMemberPicker('bind', r.memberId || '');
}

function showCreateSuggestionDialog(r) {
    const content = r.cleanedText || r.rawAsrText || '';
    showSmallModal('从反馈创建建议', `
        <div class="form-group"><label class="form-label">建议内容</label><textarea id="recordSuggestionContent" class="form-input">${escapeHtml(content)}</textarea></div>
        <div class="form-group"><label class="form-label">分类</label><input id="recordSuggestionCategory" class="form-input" placeholder="服务/环境/价格/项目"></div>
        ${memberPicker('recordSuggestion', '提出客户（可选）')}`,
        () => api.createCrmSuggestion({ content: inputVal('recordSuggestionContent'), category: inputVal('recordSuggestionCategory'), memberId: pickedMember('recordSuggestion'), feedbackRecordId: r.id, storeId: r.storeId })
    );
    fillMemberPicker('recordSuggestion', r.memberId || '');
}

function showCreateIssueDialog(r) {
    const content = r.cleanedText || r.rawAsrText || '';
    showSmallModal('从反馈创建问题', `
        <div class="form-group"><label class="form-label">问题标题</label><input id="recordIssueTitle" class="form-input" value="客户反馈待修复问题"></div>
        <div class="form-row"><div class="form-group"><label class="form-label">分类</label><input id="recordIssueCategory" class="form-input" value="feedback"></div><div class="form-group"><label class="form-label">严重度</label><select id="recordIssueSeverity" class="form-input"><option value="medium">中</option><option value="high">高</option><option value="critical">严重</option><option value="low">低</option></select></div></div>
        <div class="form-group"><label class="form-label">问题描述</label><textarea id="recordIssueDesc" class="form-input">${escapeHtml(content)}</textarea></div>
        ${memberPicker('recordIssue', '关联客户（可选）')}`,
        () => api.createCrmIssue({ title: inputVal('recordIssueTitle'), category: inputVal('recordIssueCategory'), severity: inputVal('recordIssueSeverity'), description: inputVal('recordIssueDesc'), memberId: pickedMember('recordIssue'), feedbackRecordId: r.id, storeId: r.storeId })
    );
    fillMemberPicker('recordIssue', r.memberId || '');
}
