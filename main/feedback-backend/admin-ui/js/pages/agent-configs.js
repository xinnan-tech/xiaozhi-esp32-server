// Agent Configs - 智能体配置管理
import { api } from '../api.js';

let currentPage = 1;
const pageSize = 20;

export async function renderAgentConfigs(container) {
    container.innerHTML = `
    <div class="card">
        <div class="filter-bar">
            <div style="flex:1"></div>
            <button class="btn btn-primary btn-sm" id="addConfigBtn">+ 新增配置</button>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>配置名称</th>
                        <th>智能体ID</th>
                        <th>对话轮次</th>
                        <th>问题数</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="configsBody">
                    <tr><td colspan="8" class="loading"><div class="spinner"></div></td></tr>
                </tbody>
            </table>
        </div>
        <div id="pagination" class="pagination"></div>
    </div>`;

    document.getElementById('addConfigBtn').addEventListener('click', () => showConfigForm());
    loadConfigs();
}

async function loadConfigs() {
    const tbody = document.getElementById('configsBody');
    if (!tbody) return;

    try {
        const res = await api.getAgentConfigs(`page=${currentPage}&page_size=${pageSize}`);
        const data = res.data || {};

        if (!data.list || data.list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><p>暂无智能体配置</p></td></tr>';
            return;
        }

        tbody.innerHTML = data.list.map(c => `
        <tr>
            <td style="font-size:11px;color:#9CA3AF">${escapeHtml(c.id).substring(0,8)}...</td>
            <td><strong>${escapeHtml(c.agentName)}</strong></td>
            <td style="font-size:11px">${escapeHtml(c.agentId || '-')}</td>
            <td>${c.dialogueRounds}</td>
            <td>${c.questions ? c.questions.length : 0}</td>
            <td>${statusBadge(c.status)}</td>
            <td style="white-space:nowrap">${formatDate(c.createDate)}</td>
            <td>
                <button class="btn btn-secondary btn-sm edit-cfg-btn" data-id="${c.id}">编辑</button>
                <button class="btn btn-danger btn-sm del-cfg-btn" data-id="${c.id}">删除</button>
            </td>
        </tr>`).join('');

        tbody.querySelectorAll('.edit-cfg-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cfg = data.list.find(c => c.id === btn.dataset.id);
                if (cfg) showConfigForm(cfg);
            });
        });

        tbody.querySelectorAll('.del-cfg-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('确定删除该配置？')) return;
                await api.deleteAgentConfig(btn.dataset.id);
                loadConfigs();
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
        document.getElementById('prevPage')?.addEventListener('click', () => { if (currentPage > 1) { currentPage--; loadConfigs(); } });
        document.getElementById('nextPage')?.addEventListener('click', () => { if (currentPage < totalPages) { currentPage++; loadConfigs(); } });

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state"><p>加载失败: ${e.message}</p></td></tr>`;
    }
}

function showConfigForm(config = null) {
    const isEdit = !!config;
    const questions = config?.questions || [];
    const llmConfig = config?.llmConfig || {};

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card" style="max-width:600px">
        <div class="modal-header">
            <h3>${isEdit ? '编辑智能体配置' : '新增智能体配置'}</h3>
            <button class="modal-close" id="closeForm">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">配置名称</label>
                    <input type="text" id="formName" class="form-input" value="${config?.agentName || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">智能体 ID</label>
                    <input type="text" id="formAgentId" class="form-input" value="${config?.agentId || ''}">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">对话轮次 (1-20)</label>
                <input type="number" id="formRounds" class="form-input" value="${config?.dialogueRounds || 7}" min="1" max="20" style="width:100px">
            </div>
            <div class="form-group">
                <label class="form-label">问题列表 (每行一个问题)</label>
                <textarea id="formQuestions" class="form-input" rows="6" style="resize:vertical">${questions.join('\n')}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">LLM 配置 (JSON)</label>
                <textarea id="formLLM" class="form-input" rows="4" style="resize:vertical;font-family:monospace;font-size:12px">${llmConfig.provider ? JSON.stringify(llmConfig, null, 2) : ''}</textarea>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px">格式: {"provider":"openai","api_key":"...","base_url":"...","model":"..."}</div>
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

        const agentName = document.getElementById('formName').value.trim();
        const agentId = document.getElementById('formAgentId').value.trim() || null;
        const dialogueRounds = parseInt(document.getElementById('formRounds').value) || 7;
        const questionsText = document.getElementById('formQuestions').value.trim();
        const llmText = document.getElementById('formLLM').value.trim();

        if (!agentName) {
            errEl.textContent = '配置名称不能为空';
            return;
        }

        const questions = questionsText ? questionsText.split('\n').map(q => q.trim()).filter(Boolean) : null;

        let llmConfig = null;
        if (llmText) {
            try {
                llmConfig = JSON.parse(llmText);
            } catch {
                errEl.textContent = 'LLM 配置 JSON 格式错误';
                return;
            }
        }

        try {
            if (isEdit) {
                await api.updateAgentConfig(config.id, {
                    agent_name: agentName, agent_id: agentId,
                    dialogue_rounds: dialogueRounds, questions, llm_config: llmConfig
                });
            } else {
                await api.createAgentConfig({
                    agent_name: agentName, agent_id: agentId,
                    dialogue_rounds: dialogueRounds, questions, llm_config: llmConfig
                });
            }
            close();
            loadConfigs();
        } catch (e) {
            errEl.textContent = '保存失败: ' + e.message;
        }
    });
}
