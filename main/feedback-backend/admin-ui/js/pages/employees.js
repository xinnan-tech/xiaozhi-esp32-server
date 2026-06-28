// Employees - 员工管理
import { api } from '../api.js';

let currentPage = 1;
const pageSize = 20;

export async function renderEmployees(container) {
    container.innerHTML = `
    <div class="card">
        <div class="filter-bar">
            <input type="text" id="filterStoreId" class="form-input" placeholder="门店ID" style="width:160px">
            <input type="text" id="filterName" class="form-input" placeholder="员工姓名" style="width:120px">
            <button class="btn btn-primary btn-sm" id="filterBtn">查询</button>
            <div style="flex:1"></div>
            <button class="btn btn-primary btn-sm" id="addEmpBtn">+ 新增员工</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>姓名</th>
                        <th>工号</th>
                        <th>门店ID</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="empsBody">
                    <tr><td colspan="8" class="loading"><div class="spinner"></div></td></tr>
                </tbody>
            </table>
        </div>
        <div id="pagination" class="pagination"></div>
    </div>`;

    document.getElementById('filterBtn').addEventListener('click', () => { currentPage = 1; loadEmployees(); });
    document.getElementById('addEmpBtn').addEventListener('click', () => showEmployeeForm());
    loadEmployees();
}

async function loadEmployees() {
    const tbody = document.getElementById('empsBody');
    if (!tbody) return;

    const storeId = document.getElementById('filterStoreId')?.value.trim() || '';
    const name = document.getElementById('filterName')?.value.trim() || '';
    const params = new URLSearchParams({ page: currentPage, page_size: pageSize });
    if (storeId) params.set('store_id', storeId);
    if (name) params.set('name', name);

    try {
        const res = await api.getEmployees(params.toString());
        const data = res.data || {};

        if (!data.list || data.list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><p>暂无员工</p></td></tr>';
            return;
        }

        tbody.innerHTML = data.list.map(e => `
        <tr>
            <td style="font-size:11px;color:#9CA3AF">${escapeHtml(e.id).substring(0,8)}...</td>
            <td><strong>${escapeHtml(e.name)}</strong></td>
            <td>${e.number}</td>
            <td style="font-size:11px">${escapeHtml(e.storeId)}</td>
            <td>${employeeTypeBadge(e.employeeType)}</td>
            <td>${statusBadge(e.status)}</td>
            <td style="white-space:nowrap">${formatDate(e.createDate)}</td>
            <td>
                <button class="btn btn-secondary btn-sm edit-emp-btn" data-id="${e.id}">编辑</button>
                <button class="btn btn-danger btn-sm del-emp-btn" data-id="${e.id}">删除</button>
            </td>
        </tr>`).join('');

        tbody.querySelectorAll('.edit-emp-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const emp = data.list.find(e => e.id === btn.dataset.id);
                if (emp) showEmployeeForm(emp);
            });
        });

        tbody.querySelectorAll('.del-emp-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('确定删除该员工？')) return;
                await api.deleteEmployee(btn.dataset.id);
                loadEmployees();
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
        document.getElementById('prevPage')?.addEventListener('click', () => { if (currentPage > 1) { currentPage--; loadEmployees(); } });
        document.getElementById('nextPage')?.addEventListener('click', () => { if (currentPage < totalPages) { currentPage++; loadEmployees(); } });

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state"><p>加载失败: ${e.message}</p></td></tr>`;
    }
}

function showEmployeeForm(emp = null) {
    const isEdit = !!emp;
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card">
        <div class="modal-header">
            <h3>${isEdit ? '编辑员工' : '新增员工'}</h3>
            <button class="modal-close" id="closeForm">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">员工姓名</label>
                    <input type="text" id="formName" class="form-input" value="${emp?.name || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">工号</label>
                    <input type="number" id="formNumber" class="form-input" value="${emp?.number || ''}" min="1">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">门店 ID</label>
                    <input type="text" id="formStoreId" class="form-input" value="${emp?.storeId || ''}" ${isEdit ? 'readonly' : ''}>
                </div>
                <div class="form-group">
                    <label class="form-label">员工类型</label>
                    <select id="formType" class="form-input">
                        <option value="normal" ${emp?.employeeType === 'normal' ? 'selected' : ''}>普通员工</option>
                        <option value="manager" ${emp?.employeeType === 'manager' ? 'selected' : ''}>店长</option>
                        <option value="excellent" ${emp?.employeeType === 'excellent' ? 'selected' : ''}>优秀员工</option>
                        <option value="intern" ${emp?.employeeType === 'intern' ? 'selected' : ''}>实习生</option>
                    </select>
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

        const name = document.getElementById('formName').value.trim();
        const number = parseInt(document.getElementById('formNumber').value);
        const storeId = document.getElementById('formStoreId').value.trim();
        const empType = document.getElementById('formType').value;

        if (!name || !number || !storeId) {
            errEl.textContent = '姓名、工号、门店ID 不能为空';
            return;
        }

        try {
            if (isEdit) {
                await api.updateEmployee(emp.id, { name, number, employee_type: empType });
            } else {
                await api.createEmployee({ name, number, store_id: storeId, employee_type: empType });
            }
            close();
            loadEmployees();
        } catch (e) {
            errEl.textContent = '保存失败: ' + e.message;
        }
    });
}
