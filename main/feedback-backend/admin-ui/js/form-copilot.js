// AI 表单助手：根据 Agent action 自动跳转、打开表单、填字段，并支持多轮修改/保存

const FORM_FIELD_MAP = {
    'crm.member.create': {
        name: 'mName', 姓名: 'mName',
        phone: 'mPhone', 手机号: 'mPhone', 电话: 'mPhone',
        wechat: 'mWechat', 微信: 'mWechat', 微信号: 'mWechat',
        level: 'mLevel', 客户等级: 'mLevel', 等级: 'mLevel',
        health: 'mHealth', 身体: 'mHealth', 身体问题: 'mHealth', 症状: 'mHealth',
        allergies: 'mAllergies', 过敏: 'mAllergies', 过敏史: 'mAllergies',
        notes: 'mNotes', 备注: 'mNotes',
    },
    'crm.product.create': {
        productName: 'pName', 产品名称: 'pName', 名称: 'pName', 产品: 'pName',
        category: 'pCategory', 分类: 'pCategory', 类别: 'pCategory',
        productType: 'pType', 类型: 'pType',
        defaultCount: 'pCount', 默认次数: 'pCount', 次数: 'pCount', 数量: 'pCount',
        price: 'pPrice', 价格: 'pPrice', 单价: 'pPrice', 金额: 'pPrice',
        description: 'pDesc', 说明: 'pDesc', 备注: 'pDesc',
    },
    'crm.appointment.create': {
        employee: 'aptEmp', 员工: 'aptEmp', 技师: 'aptEmp',
        startAt: 'aptStart', 开始时间: 'aptStart', 时间: 'aptStart', 预约时间: 'aptStart',
        durationMinutes: 'aptDuration', 时长: 'aptDuration', 服务时长: 'aptDuration',
        notes: 'aptNotes', 备注: 'aptNotes',
    },
    'crm.body_status.create': {
        weight: 'bsWeight', 体重: 'bsWeight',
        waistline: 'bsWaist', 腰围: 'bsWaist',
        metricName: 'bsMetricName', 标签: 'bsMetricName', 身体标签: 'bsMetricName', 指标: 'bsMetricName',
        metricStatus: 'bsMetricStatus', 状态: 'bsMetricStatus', 效果: 'bsMetricStatus',
        metricValue: 'bsMetricValue', 数值: 'bsMetricValue', 好转数值: 'bsMetricValue',
        notes: 'bsNotes', 描述: 'bsNotes', 备注: 'bsNotes',
    },
};

const REQUIRED_FIELDS = {
    'crm.member.create': [ ['mName', '客户姓名'], ['mPhone', '手机号'] ],
    'crm.product.create': [ ['pName', '产品名称'], ['pPrice', '价格/单价'] ],
    'crm.appointment.create': [ ['aptMember', '客户'], ['aptEmp', '员工'], ['aptStart', '预约时间'] ],
    'crm.body_status.create': [ ['bsMember', '客户'] ],
};

export const FormCopilot = {
    current: null,

    execute(action) {
        if (!action || action.type !== 'open_form') return false;
        const route = action.route || 'crm';
        if (window.location.hash !== `#/${route}`) window.location.hash = `#/${route}`;
        setTimeout(() => this.openForm(action.form, action.payload || {}), 250);
        return true;
    },

    openForm(form, payload) {
        const forms = window.CrmForms || {};
        const fn = forms[form];
        if (!fn) { alert(`表单未注册：${form}`); return; }
        this.current = { form, payload: payload || {}, openedAt: Date.now() };
        fn(payload || {});
        setTimeout(() => this.showStatus(), 200);
    },

    handleUserMessage(text) {
        if (!this.current) return null;
        const msg = (text || '').trim();
        if (!msg) return null;
        if (/^(保存|提交|确认保存|可以保存|确定保存)$/i.test(msg)) {
            const missing = this.getMissingFields();
            if (missing.length) return '还缺：' + missing.join('、') + '。请补充后再保存。';
            if (!confirm('确认保存当前表单吗？')) return '已取消保存，你可以继续修改。';
            const ok = this.submitCurrent();
            return ok ? '已帮你点击保存。' : '当前没有可提交的表单。';
        }
        if (/^(还缺什么|缺什么|表单状态|填了什么)$/i.test(msg)) return this.showStatus();
        const updates = this.extractFieldUpdates(msg, this.current.form);
        if (!Object.keys(updates).length) return null;
        this.fill(updates);
        return '已更新：' + Object.keys(updates).map(id => this.fieldLabel(id)).join('、') + '。' + this.missingHint();
    },

    showStatus() {
        const missing = this.getMissingFields();
        const filled = this.getFilledFields();
        return `当前表单：${this.current?.form || '-'}。已填：${filled.length ? filled.join('、') : '暂无'}。${missing.length ? '还缺：' + missing.join('、') : '必填项已齐，可以说“保存”。'}`;
    },

    getMissingFields() {
        const list = REQUIRED_FIELDS[this.current?.form] || [];
        return list.filter(([id]) => !this.getValue(id)).map(([, label]) => label);
    },

    getFilledFields() {
        const map = FORM_FIELD_MAP[this.current?.form] || {};
        const seen = new Set();
        const labels = [];
        Object.entries(map).forEach(([label, id]) => {
            if (seen.has(id)) return;
            seen.add(id);
            if (this.getValue(id)) labels.push(this.fieldLabel(id));
        });
        return labels;
    },

    missingHint() {
        const missing = this.getMissingFields();
        return missing.length ? `还缺：${missing.join('、')}。` : '必填项已齐，可以说“保存”。';
    },

    fieldLabel(id) {
        const labels = {
            mName: '姓名', mPhone: '手机号', mWechat: '微信', mLevel: '客户等级', mHealth: '身体问题', mAllergies: '过敏', mNotes: '备注',
            pName: '产品名称', pCategory: '分类', pType: '类型', pCount: '次数', pPrice: '价格', pDesc: '说明',
            aptMember: '客户', aptEmp: '员工', aptStart: '预约时间', aptDuration: '时长', aptNotes: '备注',
            bsMember: '客户', bsWeight: '体重', bsWaist: '腰围', bsMetricName: '身体标签', bsMetricStatus: '状态', bsMetricValue: '数值', bsNotes: '描述',
        };
        return labels[id] || id;
    },

    extractFieldUpdates(text, form) {
        const map = FORM_FIELD_MAP[form] || {};
        const updates = {};
        const normalized = text.replace(/改成|换成|改为|设置为|写成/g, '为');
        Object.entries(map).forEach(([key, id]) => {
            const patterns = [ new RegExp(`${key}[：:为是 ]+([^，,。；;]+)`), new RegExp(`把${key}[改设写]?为([^，,。；;]+)`) ];
            for (const p of patterns) { const m = normalized.match(p); if (m) { updates[id] = m[1].trim(); break; } }
        });
        const phone = normalized.match(/1\d{10}/); if (phone && map.phone) updates[map.phone] = phone[0];
        const vip = normalized.match(/(VIP|vip|老客|新客)/); if (vip && map.level) updates[map.level] = vip[1].toUpperCase ? vip[1].toUpperCase() : vip[1];
        const price = normalized.match(/(?:价格|单价|金额)\D*(\d+(?:\.\d+)?)/); if (price && map.price) updates[map.price] = price[1];
        const count = normalized.match(/(?:次数|默认次数|数量)\D*(\d+)/); if (count && map.defaultCount) updates[map.defaultCount] = count[1];
        const duration = normalized.match(/(?:时长|服务时长)\D*(\d+)/); if (duration && map.durationMinutes) updates[map.durationMinutes] = duration[1];
        if (form === 'crm.product.create') {
            if (/套餐/.test(normalized)) updates.pType = 'package';
            if (/实物|产品/.test(normalized)) updates.pType = 'product';
            if (/服务|项目/.test(normalized)) updates.pType = 'service';
        }
        if (form === 'crm.appointment.create') {
            const dt = this.parseDateTimeHint(normalized);
            if (dt) updates.aptStart = dt;
        }
        if (form === 'crm.body_status.create') {
            const status = normalized.match(/(没啥效果|有改善|有好转|明显好转)/);
            if (status) updates.bsMetricStatus = status[1];
        }
        return updates;
    },

    parseDateTimeHint(text) {
        if (!/(今天|明天|后天|上午|下午|晚上|点)/.test(text)) return '';
        const d = new Date();
        if (text.includes('明天')) d.setDate(d.getDate() + 1);
        if (text.includes('后天')) d.setDate(d.getDate() + 2);
        const cn = { '一':1, '二':2, '两':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10 };
        const m = text.match(/(\d{1,2}|[一二两三四五六七八九十])点/);
        let hour = m ? (/^\d+$/.test(m[1]) ? Number(m[1]) : cn[m[1]] || 10) : 10;
        if (text.includes('下午') && hour < 12) hour += 12;
        const y = d.getFullYear(), mo = String(d.getMonth()+1).padStart(2,'0'), da = String(d.getDate()).padStart(2,'0');
        return `${y}-${mo}-${da}T${String(hour).padStart(2,'0')}:00`;
    },

    submitCurrent() {
        const btn = document.getElementById('crmSave') || document.getElementById('recordCrmSave');
        if (!btn) return false;
        btn.click();
        this.current = null;
        return true;
    },

    fill(fields) { Object.entries(fields || {}).forEach(([id, value]) => this.setValue(id, value)); },
    getValue(id) { return document.getElementById(id)?.value?.trim() || ''; },
    setValue(id, value) {
        const el = document.getElementById(id);
        if (!el || value === undefined || value === null) return;
        if (Array.isArray(value)) value = value.join('\n');
        if (typeof value === 'object') value = JSON.stringify(value, null, 2);
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    },
    setMember(prefix, member) {
        if (!member) return;
        this.setValue(`${prefix}Member`, member.id || member.memberId || '');
        this.setValue(`${prefix}MemberManual`, member.id || member.memberId || '');
        this.setValue(`${prefix}MemberKeyword`, member.label || member.name || member.phone || '');
    },
};

window.FormCopilot = FormCopilot;
