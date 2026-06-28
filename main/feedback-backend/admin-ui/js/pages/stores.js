// Stores - 门店管理
import { api } from '../api.js';

let currentPage = 1;
const pageSize = 20;

export async function renderStores(container) {
    container.innerHTML = `
    <div class="card">
        <div class="filter-bar">
            <input type="text" id="filterStoreName" class="form-input" placeholder="门店名称" style="width:160px">
            <button class="btn btn-primary btn-sm" id="filterBtn">查询</button>
            <div style="flex:1"></div>
            <button class="btn btn-primary btn-sm" id="addStoreBtn">+ 新增门店</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>编码</th>
                        <th>门店名称</th>
                        <th>店长</th>
                        <th>智能体ID</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="storesBody">
                    <tr><td colspan="8" class="loading"><div class="spinner"></div></td></tr>
                </tbody>
            </table>
        </div>
        <div id="pagination" class="pagination"></div>
    </div>`;

    document.getElementById('filterBtn').addEventListener('click', () => { currentPage = 1; loadStores(); });
    document.getElementById('addStoreBtn').addEventListener('click', () => showStoreForm());
    loadStores();
}

async function loadStores() {
    const tbody = document.getElementById('storesBody');
    if (!tbody) return;

    const storeName = document.getElementById('filterStoreName')?.value.trim() || '';
    const params = new URLSearchParams({ page: currentPage, page_size: pageSize });
    if (storeName) params.set('store_name', storeName);

    try {
        const res = await api.getStores(params.toString());
        const data = res.data || {};

        if (!data.list || data.list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><p>暂无门店</p></td></tr>';
            return;
        }

        tbody.innerHTML = data.list.map(s => `
        <tr>
            <td style="font-size:11px;color:#9CA3AF">${escapeHtml(s.id).substring(0,8)}...</td>
            <td><strong>${escapeHtml(s.storeCode)}</strong></td>
            <td>${escapeHtml(s.storeName)}</td>
            <td>${escapeHtml(s.manager || '-')}</td>
            <td style="font-size:11px">${escapeHtml(s.agentId || '-')}</td>
            <td>${statusBadge(s.status)}</td>
            <td style="white-space:nowrap">${formatDate(s.createDate)}</td>
            <td>
                <button class="btn btn-secondary btn-sm edit-store-btn" data-id="${s.id}">编辑</button>
                <button class="btn btn-danger btn-sm del-store-btn" data-id="${s.id}">删除</button>
            </td>
        </tr>`).join('');

        tbody.querySelectorAll('.edit-store-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const store = data.list.find(s => s.id === btn.dataset.id);
                if (store) showStoreForm(store);
            });
        });

        tbody.querySelectorAll('.del-store-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('确定删除该门店？')) return;
                await api.deleteStore(btn.dataset.id);
                loadStores();
            });
        });

        const total = data.total || 0;
        const totalPages = Math.ceil(total / pageSize);
        document.getElementById('pagination').innerHTML = `
            <div class="pagination-info">共 ${total} 条</div>
            <div class="pagination-btns">
                <button ${currentPage <= 1 ? 'disabled' : ''} id="prevPage">上一页</button>
                <button class="active">${currentPage}</button>
                <button ${currentPage >= totalPages ? 'disabled' : ''} id="nextPage">下一页</button>
            </div>`;
        document.getElementById('prevPage')?.addEventListener('click', () => { if (currentPage > 1) { currentPage--; loadStores(); } });
        document.getElementById('nextPage')?.addEventListener('click', () => { if (currentPage < totalPages) { currentPage++; loadStores(); } });

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state"><p>加载失败: ${e.message}</p></td></tr>`;
    }
}

function showStoreForm(store = null) {
    const isEdit = !!store;
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card">
        <div class="modal-header">
            <h3>${isEdit ? '编辑门店' : '新增门店'}</h3>
            <button class="modal-close" id="closeForm">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">门店编码 (6位数字)</label>
                    <input type="text" id="formStoreCode" class="form-input" value="${store?.storeCode || ''}" maxlength="6" ${isEdit ? 'readonly' : ''}>
                </div>
                <div class="form-group">
                    <label class="form-label">门店名称</label>
                    <input type="text" id="formStoreName" class="form-input" value="${store?.storeName || ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">店长</label>
                    <input type="text" id="formManager" class="form-input" value="${store?.manager || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">智能体 ID</label>
                    <input type="text" id="formAgentId" class="form-input" value="${store?.agentId || ''}">
                </div>
            </div>
            <div id="formError" style="color:var(--danger);font-size:13px;min-height:20px;margin-top:8px"></div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelBtn">取消</button>
            <button class="btn btn-primary" id="saveBtn">保存</button>
        </div>
    </div>`;

    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('closeForm').addEventListener('click', close);
    document.getElementById('cancelBtn').addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

    document.getElementById('saveBtn').addEventListener('click', async () => {
        const errEl = document.getElementById('formError');
        errEl.textContent = '';

        const code = document.getElementById('formStoreCode').value.trim();
        const name = document.getElementById('formStoreName').value.trim();
        const manager = document.getElementById('formManager').value.trim();
        const agentId = document.getElementById('formAgentId').value.trim();

        if (!code || !name) {
            errEl.textContent = '门店编码和名称不能为空';
            return;
        }
        if (!/^\d{6}$/.test(code)) {
            errEl.textContent = '门店编码必须为6位数字';
            return;
        }

        try {
            if (isEdit) {
                await api.updateStore(store.id, {
                    store_code: code, store_name: name, manager, agent_id: agentId || null
                });
            } else {
                await api.createStore({ store_code: code, store_name: name, manager, agent_id: agentId || null });
            }
            close();
            loadStores();
        } catch (e) {
            errEl.textContent = '保存失败: ' + e.message;
        }
    });
}
