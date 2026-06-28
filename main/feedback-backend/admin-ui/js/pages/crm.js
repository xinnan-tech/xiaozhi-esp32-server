// CRM 管理
import { api } from '../api.js';

let currentTab = 'overview';
let currentPage = 1;
let memberKeyword = '';
let appointmentDate = dateInput(new Date());
let appointmentView = 'day';
const pageSize = 20;
const MEKAI66_FIELDS = [
    ['name','姓名','基础信息'],['nickname','昵称/常用称呼','基础信息'],['gender','性别','基础信息'],['birthday','生日','基础信息'],['age','年龄','基础信息'],['hometown','籍贯/老家','基础信息'],['address','居住地址/小区','基础信息'],['phone','手机号','基础信息'],['wechat','微信号','基础信息'],['education','学历','基础信息'],
    ['marital_status','婚姻状态','家庭关系'],['spouse_name','配偶姓名','家庭关系'],['spouse_job','配偶职业','家庭关系'],['children','子女情况','家庭关系'],['children_school','子女学校/年级','家庭关系'],['parents','父母情况','家庭关系'],['family_anniversary','家庭纪念日','家庭关系'],['family_focus','家庭关注点','家庭关系'],['pet','宠物','家庭关系'],['emergency_contact','紧急联系人','家庭关系'],
    ['company','公司/单位','工作事业'],['industry','行业','工作事业'],['position','职位','工作事业'],['job_responsibility','工作职责','工作事业'],['income_level','收入水平','工作事业'],['work_pressure','工作压力','工作事业'],['work_schedule','作息/上下班时间','工作事业'],['business_needs','事业需求/目标','工作事业'],['decision_style','决策风格','工作事业'],['social_circle','社交圈','工作事业'],
    ['hobbies','兴趣爱好','生活方式'],['sports','运动习惯','生活方式'],['travel','旅游偏好','生活方式'],['diet','饮食偏好','生活方式'],['tea_drink','茶饮偏好','生活方式'],['music','音乐偏好','生活方式'],['reading','阅读/学习偏好','生活方式'],['shopping','购物偏好','生活方式'],['brands','喜欢品牌','生活方式'],['taboo_topics','忌讳话题','生活方式'],
    ['consumption_power','消费能力','消费习惯'],['consumption_frequency','消费频次','消费习惯'],['budget','预算区间','消费习惯'],['preferred_projects','偏好项目','消费习惯'],['disliked_projects','不喜欢项目','消费习惯'],['price_sensitivity','价格敏感度','消费习惯'],['promotion_preference','优惠偏好','消费习惯'],['referral_willingness','转介绍意愿','消费习惯'],['decision_factor','购买决策因素','消费习惯'],['loss_risk','流失风险点','消费习惯'],
    ['skin_type','皮肤类型','健康美容'],['beauty_concerns','美容关注点','健康美容'],['body_discomfort','身体不适','健康美容'],['chronic_disease','慢性病/疾病史','健康美容'],['allergy','过敏史','健康美容'],['contraindication','护理禁忌','健康美容'],['sleep','睡眠情况','健康美容'],['menstruation','经期/备孕/孕产情况','健康美容'],
    ['preferred_employee','偏好技师','服务偏好'],['service_strength','服务力度偏好','服务偏好'],['chat_preference','聊天偏好','服务偏好'],['room_preference','房间/环境偏好','服务偏好'],['temperature_preference','温度偏好','服务偏好'],['appointment_preference','预约时间偏好','服务偏好'],['last_important_event','最近重要事件','关系维护'],['next_followup','下次跟进重点','关系维护'],
].map(([key, label, category]) => ({ key, label, category }));

export async function renderCrm(container) {
    const query = (window.location.hash.split('?')[1] || '');
    const params = new URLSearchParams(query);
    if (params.get('tab')) currentTab = params.get('tab');
    container.innerHTML = `
    <div class="crm-tabs">
        ${tabBtn('overview', '📊', 'CRM看板')}
        ${tabBtn('members', '👤', '客户档案')}
        ${tabBtn('appointments', '📅', '预约日历')}
        ${tabBtn('visits', '🕒', '到店记录')}
        ${tabBtn('products', '🧴', '产品管理')}
        ${tabBtn('memberProducts', '🎁', '客户套餐')}
        ${tabBtn('productConsumes', '📉', '套餐消费')}
        ${tabBtn('cardCloses', '🚪', '销卡管理')}
        ${tabBtn('suggestions', '💡', '建议管理')}
    </div>
    <div id="crmContent"></div>`;
    container.querySelectorAll('.crm-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            currentTab = btn.dataset.tab;
            currentPage = 1;
            renderCrm(container);
        });
    });
    await loadTab();
}

function tabBtn(tab, icon, label) {
    return `<button class="crm-tab ${currentTab === tab ? 'active' : ''}" data-tab="${tab}">${icon} ${label}</button>`;
}

async function loadTab() {
    const el = document.getElementById('crmContent');
    if (!el) return;
    if (currentTab === 'overview') return loadOverview(el);
    if (currentTab === 'members') return loadMembers(el);
    if (currentTab === 'appointments') return loadAppointments(el);
    if (currentTab === 'bodyStatus') return loadBodyStatus(el);
    if (currentTab === 'visits') return loadVisits(el);
    if (currentTab === 'products') return loadProducts(el);
    if (currentTab === 'memberProducts') return loadMemberProducts(el);
    if (currentTab === 'productConsumes') return loadProductConsumes(el);
    if (currentTab === 'accounts') return loadAccounts(el);
    if (currentTab === 'transactions') return loadTransactions(el);
    if (currentTab === 'cardCloses') return loadCardCloses(el);
    if (currentTab === 'suggestions') return loadSuggestions(el);
    if (currentTab === 'issues') return loadIssues(el);
}

async function loadOverview(el) {
    el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const res = await api.getCrmOverview();
        const d = res.data || {};
        el.innerHTML = `
        <div class="stat-grid">
            ${stat('👤', '客户数', d.members || 0, 'blue')}
            ${stat('🕒', '到店记录', d.visits || 0, 'green')}
            ${stat('💳', '有效账户', d.activeAccounts || 0, 'blue')}
            ${stat('💰', '账户余额', `¥${d.accountBalance || 0}`, 'green')}
            ${stat('🚪', '销卡记录', d.cardCloses || 0, 'yellow')}
            ${stat('💡', '待处理建议', d.pendingSuggestions || 0, 'yellow')}
            ${stat('✅', '已采纳建议', d.adoptedSuggestions || 0, 'green')}
        </div>
        <div class="card"><div class="card-title">使用说明</div>
            <p class="muted">当前主视角：客户档案、身体变化、已购产品/套餐、套餐消耗、建议闭环。到店记录和流水作为支撑数据保留。</p>
        </div>`;
    } catch (e) { el.innerHTML = error(e); }
}

function stat(icon, label, value, color) {
    return `<div class="stat-card"><div class="stat-icon ${color}">${icon}</div><div class="stat-info"><div class="stat-label">${label}</div><div class="stat-value">${value}</div></div></div>`;
}

async function loadMembers(el) {
    el.innerHTML = listShell('客户档案', '新增客户', 'memberAddBtn', `
        <input id="crmKeyword" class="form-input" placeholder="姓名/手机号" style="width:180px" value="${escapeHtml(memberKeyword)}">
        <button class="btn btn-primary btn-sm" id="crmSearchBtn">查询</button>
    `, ['姓名','手机号','美容/健康','到店','消费','时间','操作']);
    document.getElementById('memberAddBtn').onclick = () => showMemberDialog();
    document.getElementById('crmSearchBtn').onclick = () => {
        memberKeyword = document.getElementById('crmKeyword')?.value.trim() || '';
        currentPage = 1;
        loadMembers(el);
    };
    document.getElementById('crmKeyword').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') document.getElementById('crmSearchBtn').click();
    });
    const params = new URLSearchParams({ page: currentPage, page_size: pageSize });
    if (memberKeyword) params.set('keyword', memberKeyword);
    try {
        const res = await api.getCrmMembers(params.toString());
        const data = res.data || {};
        renderRows(data, m => `
        <tr><td><strong>${escapeHtml(m.name || '-')}</strong><div class="muted">${escapeHtml(m.level || '')}</div></td>
        <td>${escapeHtml(m.phone || '-')}</td><td>${tags(m.beautyConcerns)}${tags(m.healthIssues)}</td>
        <td>${m.totalVisits || 0}</td><td>¥${m.totalSpent || 0}</td><td>${formatDate(m.updateDate)}</td>
        <td><button class="btn btn-secondary btn-sm" data-detail="${m.id}">详情</button></td></tr>`);
        bindDetailButtons(data.list || []);
    } catch (e) { tableError(e, 7); }
}

async function loadBodyStatus(el) {
    el.innerHTML = listShell('身体变化状态', '新增状态', 'bodyAddBtn', '', ['客户','日期','体重','腰围','标签','状态','数值','描述']);
    document.getElementById('bodyAddBtn').onclick = () => showBodyStatusDialog();
    try {
        const res = await api.getCrmBodyStatuses(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, b => `<tr><td><strong>${escapeHtml(b.memberName || '-')}</strong><div class="muted">${escapeHtml(b.memberId)}</div></td><td>${formatDate(b.recordDate)}</td><td>${b.weight ?? '-'}</td><td>${b.waistline ?? '-'}</td><td>${escapeHtml(b.metrics?.name || '-')}</td><td>${escapeHtml(b.metrics?.status || '-')}</td><td>${escapeHtml(b.metrics?.value || '-')}</td><td>${escapeHtml(b.notes || '-')}</td></tr>`);
    } catch (e) { tableError(e, 8); }
}

async function loadAppointments(el) {
    const range = appointmentRange(appointmentDate, appointmentView);
    el.innerHTML = `
    <div class="card">
        <div class="filter-bar">
            <div class="card-title" style="margin:0;flex:1">预约日历</div>
            <select id="aptView" class="form-input" style="width:100px"><option value="day">日</option><option value="week">周</option><option value="month">月</option></select>
            <input id="aptDate" type="date" class="form-input" style="width:150px" value="${appointmentDate}">
            <select id="aptEmployee" class="form-input" style="width:160px"><option value="">全部员工</option></select>
            <button class="btn btn-primary btn-sm" id="aptSearch">查询</button>
            <button class="btn btn-secondary btn-sm" id="aptAvailability">查看空档</button>
            <button class="btn btn-primary btn-sm" id="aptCreate">新增预约</button>
        </div>
        <div id="aptBoard" class="appointment-board"><div class="loading"><div class="spinner"></div></div></div>
    </div>`;
    document.getElementById('aptView').value = appointmentView;
    await loadAppointmentEmployees();
    document.getElementById('aptSearch').onclick = () => { appointmentDate = val('aptDate'); appointmentView = val('aptView'); loadAppointments(el); };
    document.getElementById('aptAvailability').onclick = () => showAvailabilityDialog();
    document.getElementById('aptCreate').onclick = () => showAppointmentDialog();
    await renderAppointmentBoard(range);
}

function appointmentRange(baseDate, view) {
    const d = new Date(baseDate + 'T00:00:00');
    if (view === 'day') return { start: dateInput(d), end: dateInput(d) };
    if (view === 'week') {
        const start = new Date(d); start.setDate(d.getDate() - ((d.getDay() + 6) % 7));
        const end = new Date(start); end.setDate(start.getDate() + 6);
        return { start: dateInput(start), end: dateInput(end) };
    }
    const start = new Date(d.getFullYear(), d.getMonth(), 1);
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
    return { start: dateInput(start), end: dateInput(end) };
}

async function loadAppointmentEmployees() {
    const sel = document.getElementById('aptEmployee'); if (!sel) return;
    try {
        const res = await api.getEmployees('page=1&page_size=100');
        const list = res.data?.list || [];
        sel.innerHTML = '<option value="">全部员工</option>' + list.map(e => `<option value="${e.id}">${escapeHtml(e.name)}${e.number ? `（${e.number}号）` : ''}</option>`).join('');
    } catch (e) {}
}

async function renderAppointmentBoard(range) {
    const board = document.getElementById('aptBoard'); if (!board) return;
    const params = new URLSearchParams({ start_date: range.start, end_date: range.end });
    const emp = document.getElementById('aptEmployee')?.value || '';
    if (emp) params.set('employee_id', emp);
    try {
        const res = await api.getAppointmentCalendar(params.toString());
        const data = res.data || { resources: [], events: [] };
        if (appointmentView === 'day') {
            board.innerHTML = `<div class="appointment-range">${range.start} · ${data.events.length || 0} 个预约</div>${renderDayEventSummary(data.events)}${renderResourceDayCalendar(data.resources, data.events)}`;
            bindAppointmentActions(board, range);
            setTimeout(() => {
                const first = board.querySelector('.resource-event');
                const cal = board.querySelector('.resource-calendar');
                if (first && cal) cal.scrollTop = Math.max(0, first.offsetTop - 80);
            }, 50);
        } else if (window.FullCalendar) {
            renderFullCalendar(board, range, data);
        } else {
            board.innerHTML = `
                <div class="appointment-range">${range.start} 至 ${range.end} · ${data.events.length || 0} 个预约</div>
                ${appointmentView === 'month' ? renderMonthCalendar(range, data.events) : appointmentView === 'week' ? renderWeekCalendar(range, data.events) : renderDayCalendar(data.resources, data.events)}`;
            bindAppointmentActions(board, range);
        }
    } catch (e) {
        board.innerHTML = `<div class="empty-state">加载预约失败：${escapeHtml(e.message)}</div>`;
    }
}

function renderFullCalendar(board, range, data) {
    board.innerHTML = `<div class="appointment-range">${range.start} 至 ${range.end} · ${data.events.length || 0} 个预约</div><div id="fullCalendarBox" class="fullcalendar-box"></div>`;
    const initialView = appointmentView === 'month' ? 'dayGridMonth' : appointmentView === 'week' ? 'timeGridWeek' : 'timeGridDay';
    const calendar = new FullCalendar.Calendar(document.getElementById('fullCalendarBox'), {
        initialView,
        initialDate: appointmentDate,
        locale: 'zh-cn',
        height: 'auto',
        nowIndicator: true,
        slotMinTime: '09:00:00',
        slotMaxTime: '21:00:00',
        headerToolbar: false,
        eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
        events: data.events.map(ev => ({
            id: ev.id,
            title: ev.title || '-',
            start: (ev.start || '').replace(' ', 'T'),
            end: (ev.end || '').replace(' ', 'T'),
            className: [`fc-status-${ev.status || 'pending'}`],
            extendedProps: ev,
        })),
        eventClick(info) {
            const ev = info.event.extendedProps;
            showAppointmentActionDialog(ev, range);
        },
        dateClick(info) {
            appointmentDate = info.dateStr.slice(0, 10);
            showAppointmentDialog();
        },
    });
    calendar.render();
}

function showAppointmentActionDialog(ev, range) {
    modal('预约操作', `<div class="detail-row"><div class="detail-label">预约</div><div class="detail-value">${escapeHtml(ev.title || '-')}</div></div><div class="detail-row"><div class="detail-label">时间</div><div class="detail-value">${formatDate(ev.start)} - ${String(ev.end || '').substring(11,16)}</div></div><div class="detail-row"><div class="detail-label">状态</div><div class="detail-value">${escapeHtml(ev.status || '-')}</div></div><div class="filter-bar"><button class="btn btn-secondary" id="aptDlgConfirm">确认</button><button class="btn btn-primary" id="aptDlgComplete">完成</button><button class="btn btn-danger" id="aptDlgCancel">取消</button></div>`, async () => {});
    document.getElementById('aptDlgConfirm').onclick = async () => { await api.confirmAppointment(ev.id); document.querySelector('.modal-overlay')?.remove(); await renderAppointmentBoard(range); };
    document.getElementById('aptDlgCancel').onclick = async () => { const reason = prompt('取消原因') || ''; await api.cancelAppointment(ev.id, { reason }); document.querySelector('.modal-overlay')?.remove(); await renderAppointmentBoard(range); };
    document.getElementById('aptDlgComplete').onclick = async () => { const consume = confirm('是否完成并扣减关联套餐1次？'); await api.completeAppointment(ev.id, consume ? { consume: true, consumeCount: 1 } : {}); document.querySelector('.modal-overlay')?.remove(); await renderAppointmentBoard(range); };
}

function bindAppointmentActions(board, range) {
    board.querySelectorAll('[data-jump-apt]').forEach(btn => btn.onclick = () => {
        const target = board.querySelector(`[data-apt-open="${btn.dataset.jumpApt}"]`);
        const cal = board.querySelector('.resource-calendar');
        if (target && cal) cal.scrollTop = Math.max(0, target.offsetTop - 80);
    });
    board.querySelectorAll('[data-apt-open]').forEach(el => el.onclick = (event) => {
        event.stopPropagation();
        const id = el.dataset.aptOpen;
        showAppointmentActionDialog({ id, title: el.textContent, start: '', end: '', status: '' }, range);
    });
    board.querySelectorAll('.resource-slot').forEach(slot => slot.onclick = () => {
        appointmentDate = val('aptDate') || appointmentDate;
        showAppointmentDialog('', slot.dataset.emp, `${appointmentDate}T${slot.dataset.time}`);
    });
    board.querySelectorAll('[data-apt-confirm]').forEach(btn => btn.onclick = async () => { await api.confirmAppointment(btn.dataset.aptConfirm); await renderAppointmentBoard(range); });
    board.querySelectorAll('[data-apt-cancel]').forEach(btn => btn.onclick = async () => { const reason = prompt('取消原因') || ''; await api.cancelAppointment(btn.dataset.aptCancel, { reason }); await renderAppointmentBoard(range); });
    board.querySelectorAll('[data-apt-complete]').forEach(btn => btn.onclick = async () => { const consume = confirm('是否完成并扣减关联套餐1次？'); await api.completeAppointment(btn.dataset.aptComplete, consume ? { consume: true, consumeCount: 1 } : {}); await renderAppointmentBoard(range); });
}

function renderDayEventSummary(events) {
    if (!events.length) return '<div class="appointment-day-summary empty">当天暂无预约</div>';
    return `<div class="appointment-day-summary">${events.map(ev => `<button type="button" data-jump-apt="${ev.id}" class="appointment-summary-chip"><strong>${String(ev.start || '').slice(11,16)}</strong> ${escapeHtml(ev.title || '-')}</button>`).join('')}</div>`;
}

function renderResourceDayCalendar(resources, events) {
    const startHour = 9, endHour = 21, slotHeight = 44;
    const totalSlots = (endHour - startHour) * 2;
    const times = Array.from({ length: totalSlots + 1 }, (_, i) => {
        const minutes = startHour * 60 + i * 30;
        return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
    });
    const eventsByEmp = {};
    events.forEach(ev => { (eventsByEmp[ev.resourceId] ||= []).push(ev); });
    return `<div class="resource-calendar" style="--slot-h:${slotHeight}px"><div class="resource-time-axis"><div class="resource-corner">时间</div>${times.slice(0, -1).map(t => `<div class="resource-time">${t}</div>`).join('')}</div><div class="resource-columns">${resources.map(r => `<div class="resource-column"><div class="resource-head">${escapeHtml(r.title)}${r.number ? `（${r.number}号）` : ''}</div><div class="resource-slots">${times.slice(0, -1).map((t, idx) => `<div class="resource-slot" data-emp="${r.id}" data-time="${t}"></div>`).join('')}${(eventsByEmp[r.id] || []).map(ev => resourceEventBlock(ev, startHour, slotHeight)).join('')}</div></div>`).join('')}</div></div>`;
}

function resourceEventBlock(ev, startHour, slotHeight) {
    const sm = timeToMinutes(ev.start), em = timeToMinutes(ev.end);
    const top = Math.max(0, (sm - startHour * 60) / 30 * slotHeight);
    const height = Math.max(slotHeight, (em - sm) / 30 * slotHeight - 4);
    return `<div class="resource-event status-${ev.status}" style="top:${top}px;height:${height}px" data-apt-open="${ev.id}"><strong>${escapeHtml(ev.title || '-')}</strong><br><span>${String(ev.start || '').slice(11,16)}-${String(ev.end || '').slice(11,16)}</span></div>`;
}

function timeToMinutes(dt) {
    const t = String(dt || '').slice(11, 16).split(':');
    return (Number(t[0]) || 0) * 60 + (Number(t[1]) || 0);
}

function renderDayCalendar(resources, events) {
    const eventsByEmp = {};
    events.forEach(ev => { (eventsByEmp[ev.resourceId] ||= []).push(ev); });
    return `<div class="calendar-day-grid">${resources.map(r => `<div class="calendar-employee-col"><div class="calendar-employee-head">${escapeHtml(r.title)}${r.number ? `（${r.number}号）` : ''}</div>${(eventsByEmp[r.id] || []).length ? (eventsByEmp[r.id] || []).map(eventCard).join('') : '<div class="appointment-empty">暂无预约</div>'}</div>`).join('')}</div>`;
}

function renderWeekCalendar(range, events) {
    const days = dateRangeList(range.start, range.end);
    const byDay = groupEventsByDay(events);
    return `<div class="calendar-week-grid">${days.map(d => `<div class="calendar-day-cell"><div class="calendar-day-head">${formatDayLabel(d)}</div>${(byDay[d] || []).length ? byDay[d].map(compactEventCard).join('') : '<div class="calendar-no-event">空</div>'}</div>`).join('')}</div>`;
}

function renderMonthCalendar(range, events) {
    const start = new Date(range.start + 'T00:00:00');
    const first = new Date(start.getFullYear(), start.getMonth(), 1);
    const gridStart = new Date(first); gridStart.setDate(first.getDate() - first.getDay());
    const byDay = groupEventsByDay(events);
    const cells = [];
    for (let i = 0; i < 42; i++) { const d = new Date(gridStart); d.setDate(gridStart.getDate() + i); cells.push(dateInput(d)); }
    return `<div class="calendar-month"><div class="calendar-weekdays">${['日','一','二','三','四','五','六'].map(w => `<div>周${w}</div>`).join('')}</div><div class="calendar-month-grid">${cells.map(d => `<div class="calendar-month-cell ${d.slice(5,7) !== range.start.slice(5,7) ? 'muted-month' : ''}"><div class="calendar-month-date">${Number(d.slice(8,10))}</div>${(byDay[d] || []).slice(0,3).map(compactEventCard).join('')}${(byDay[d] || []).length > 3 ? `<div class="calendar-more">+${(byDay[d] || []).length - 3}更多</div>` : ''}</div>`).join('')}</div></div>`;
}

function groupEventsByDay(events) {
    const m = {};
    events.forEach(e => { const d = String(e.start || '').slice(0, 10); (m[d] ||= []).push(e); });
    return m;
}
function dateRangeList(start, end) {
    const arr = []; const s = new Date(start + 'T00:00:00'); const e = new Date(end + 'T00:00:00');
    for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) arr.push(dateInput(d));
    return arr;
}
function formatDayLabel(d) { const x = new Date(d + 'T00:00:00'); return `${x.getMonth()+1}/${x.getDate()} 周${'日一二三四五六'[x.getDay()]}`; }
function compactEventCard(ev) { return `<div class="calendar-compact-event status-${ev.status}" title="${escapeHtml(ev.title || '')}"><span>${String(ev.start || '').slice(11,16)}</span> ${escapeHtml(ev.title || '-')}</div>`; }

function eventCard(ev) {
    return `<div class="appointment-event status-${ev.status}"><div><strong>${escapeHtml(ev.title || '-')}</strong></div><div>${formatDate(ev.start)} - ${String(ev.end || '').substring(11,16)}</div><div class="muted">${escapeHtml(ev.status || '')}</div><div class="appointment-actions"><button class="btn btn-secondary btn-sm" data-apt-confirm="${ev.id}">确认</button><button class="btn btn-primary btn-sm" data-apt-complete="${ev.id}">完成</button><button class="btn btn-danger btn-sm" data-apt-cancel="${ev.id}">取消</button></div></div>`;
}

async function showAvailabilityDialog() {
    const date = val('aptDate') || appointmentDate;
    const emp = val('aptEmployee');
    const params = new URLSearchParams({ date, duration_minutes: 60 });
    if (emp) params.set('employee_id', emp);
    try {
        const res = await api.getAppointmentAvailability(params.toString());
        const slots = res.data?.slots || [];
        modal('可预约空档', `<div class="slot-grid">${slots.map(s => `<div class="slot-item ${s.available ? 'available' : 'busy'}"><strong>${escapeHtml(s.employeeName)}</strong><br>${s.start}-${s.end}<br>${s.available ? '可约' : '已占用'}</div>`).join('') || '暂无空档'}</div>`, async () => {});
    } catch (e) { alert('加载空档失败：' + e.message); }
}

async function showAppointmentDialog(defaultMemberId = '', defaultEmployeeId = '', defaultStartAt = '') {
    let employees = [];
    try { employees = (await api.getEmployees('page=1&page_size=100')).data?.list || []; } catch (e) {}
    modal('新增预约', `
        ${memberPicker('apt')}
        <div class="form-row"><div class="form-group"><label class="form-label">员工</label><select id="aptEmp" class="form-input">${employees.map(e => `<option value="${e.id}" ${e.id === (defaultEmployeeId || val('aptEmployee')) ? 'selected' : ''}>${escapeHtml(e.name)}${e.number ? `（${e.number}号）` : ''}</option>`).join('')}</select></div><div class="form-group"><label class="form-label">客户已购套餐/产品</label><select id="aptMp" class="form-input"><option value="">请先选择客户</option></select></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">开始时间</label><input id="aptStart" type="datetime-local" class="form-input" value="${defaultStartAt || appointmentDate + 'T10:00'}"></div><div class="form-group"><label class="form-label">时长分钟</label><input id="aptDuration" type="number" class="form-input" value="60"></div></div>
        <div id="aptProductInfo" class="muted" style="margin-bottom:12px">选择客户后展示客户剩余套餐。</div>
        <div class="form-group"><label class="form-label">备注</label><textarea id="aptNotes" class="form-input"></textarea></div>`,
        () => {
            const opt = document.getElementById('aptMp')?.selectedOptions?.[0];
            appointmentDate = (val('aptStart') || appointmentDate).slice(0, 10);
            appointmentView = 'day';
            return api.createAppointment({ memberId: pickedMember('apt'), employeeId: val('aptEmp'), memberProductId: val('aptMp'), productName: opt?.dataset?.name || '', startAt: val('aptStart'), durationMinutes: val('aptDuration'), storeNotes: val('aptNotes'), source: 'admin' });
        }
    );
    fillMemberPicker('apt');
    wireAppointmentMemberPicker();
    if (defaultMemberId) {
        document.getElementById('aptMemberManual').value = defaultMemberId;
        loadAppointmentMemberProducts(defaultMemberId);
    }
}

function wireAppointmentMemberPicker() {
    const input = document.getElementById('aptMemberKeyword');
    const manual = document.getElementById('aptMemberManual');
    input?.addEventListener('member-selected', (e) => loadAppointmentMemberProducts(e.detail.id));
    manual?.addEventListener('change', () => loadAppointmentMemberProducts(manual.value));
}

async function loadAppointmentMemberProducts(memberId) {
    const sel = document.getElementById('aptMp');
    const info = document.getElementById('aptProductInfo');
    if (!sel || !memberId) return;
    try {
        const res = await api.getCrmMemberProducts(new URLSearchParams({ page: 1, page_size: 100, member_id: memberId, status: 1 }).toString());
        const list = res.data?.list || [];
        sel.innerHTML = list.length ? list.map(p => `<option value="${p.id}" data-name="${escapeHtml(p.productName)}" data-duration="${p.durationMinutes || 60}">${escapeHtml(p.productName)} · 剩余${p.balanceCount || 0}/${p.totalCount || 0}次 · ¥${p.balanceAmount || 0}</option>`).join('') : '<option value="">该客户暂无可用套餐</option>';
        if (list.length) {
            document.getElementById('aptDuration').value = sel.selectedOptions[0].dataset.duration || 60;
            info.textContent = `当前选择：${sel.selectedOptions[0].textContent}`;
        } else {
            info.textContent = '该客户暂无可用套餐，也可以先去客户详情购买产品/套餐。';
        }
        sel.onchange = () => {
            document.getElementById('aptDuration').value = sel.selectedOptions[0]?.dataset.duration || 60;
            info.textContent = `当前选择：${sel.selectedOptions[0]?.textContent || '-'}`;
        };
    } catch (e) {
        info.textContent = '加载客户套餐失败：' + e.message;
    }
}

async function loadVisits(el) {
    el.innerHTML = listShell('到店记录', '新增到店', 'visitAddBtn', '', ['客户ID','员工ID','到店','离店','耗时','项目','消费','满意度']);
    document.getElementById('visitAddBtn').onclick = () => showVisitDialog();
    try {
        const res = await api.getCrmVisits(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, v => `<tr><td><strong>${escapeHtml(v.memberName || '-')}</strong><div class="muted">${escapeHtml(v.memberId || '-')}</div></td><td>${escapeHtml(v.employeeId || '-')}</td><td>${formatDate(v.arriveAt)}</td><td>${formatDate(v.leaveAt)}</td><td>${v.durationMinutes || '-'} 分钟</td><td>${tags(v.serviceItems)}</td><td>¥${v.consumptionAmount || 0}</td><td>${satisfactionBadge(v.satisfaction)}</td></tr>`);
    } catch (e) { tableError(e, 8); }
}

async function loadProducts(el) {
    el.innerHTML = listShell('产品管理', '新增产品', 'productAddBtn', '', ['名称','分类','类型','价格','默认次数','状态','操作']);
    document.getElementById('productAddBtn').onclick = () => showProductDialog();
    try {
        const res = await api.getCrmProducts(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, p => `<tr><td><strong>${escapeHtml(p.productName)}</strong><div class="muted">${escapeHtml(p.description || '')}</div></td><td>${escapeHtml(p.category || '-')}</td><td>${escapeHtml(p.productType || '-')}</td><td>¥${p.price || 0}</td><td>${p.defaultCount || 0}</td><td>${statusBadge(p.status)}</td><td><button class="btn btn-primary btn-sm" data-buy-product="${p.id}" data-name="${escapeHtml(p.productName)}" data-count="${p.defaultCount || 0}" data-price="${p.price || 0}">客户购买</button></td></tr>`);
        document.querySelectorAll('[data-buy-product]').forEach(btn => btn.onclick = () => showPurchaseDialog(btn.dataset.buyProduct, btn.dataset.name, btn.dataset.count, btn.dataset.price));
    } catch (e) { tableError(e, 7); }
}

async function loadMemberProducts(el) {
    el.innerHTML = listShell('客户已购产品/套餐', '', '', '', ['客户','产品/套餐','剩余次数','剩余金额','有效期','状态','操作']);
    try {
        const res = await api.getCrmMemberProducts(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, p => `<tr><td><strong>${escapeHtml(p.memberName || '-')}</strong><div class="muted">${escapeHtml(p.memberId)}</div></td><td>${escapeHtml(p.productName)}</td><td>${p.balanceCount || 0}/${p.totalCount || 0}</td><td>¥${p.balanceAmount || 0}/¥${p.totalAmount || 0}</td><td>${p.validEnd || '-'}</td><td>${packageStatus(p.status)}</td><td><button class="btn btn-primary btn-sm" data-consume-product="${p.id}" data-name="${escapeHtml(p.productName)}">消费</button></td></tr>`);
        document.querySelectorAll('[data-consume-product]').forEach(btn => btn.onclick = () => showProductConsumeDialog(btn.dataset.consumeProduct, btn.dataset.name));
    } catch (e) { tableError(e, 7); }
}

async function loadProductConsumes(el) {
    el.innerHTML = listShell('产品/套餐消费记录', '', '', '', ['客户','已购产品ID','到店ID','消费次数','消费金额','剩余次数','剩余金额','备注','时间']);
    try {
        const res = await api.getCrmProductConsumes(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, c => `<tr><td><strong>${escapeHtml(c.memberName || '-')}</strong><div class="muted">${escapeHtml(c.memberId)}</div></td><td>${escapeHtml(c.memberProductId)}</td><td>${escapeHtml(c.visitId || '-')}</td><td>${c.consumeCount || 0}</td><td>¥${c.consumeAmount || 0}</td><td>${c.balanceCountAfter || 0}</td><td>¥${c.balanceAmountAfter || 0}</td><td>${escapeHtml(c.notes || '-')}</td><td>${formatDate(c.createDate)}</td></tr>`);
    } catch (e) { tableError(e, 9); }
}

async function loadAccounts(el) {
    el.innerHTML = listShell('账户管理', '开卡/建账户', 'accountAddBtn', '', ['客户ID','卡名称','类型','余额','次数','有效期','状态','操作']);
    document.getElementById('accountAddBtn').onclick = () => showAccountDialog();
    try {
        const res = await api.getCrmAccounts(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, a => `<tr><td><strong>${escapeHtml(a.memberName || '-')}</strong><div class="muted">${escapeHtml(a.memberId)}</div></td><td>${escapeHtml(a.cardName || '-')}</td><td>${escapeHtml(a.accountType)}</td><td>¥${a.balanceAmount || 0}</td><td>${a.balanceCount || 0}/${a.totalCount || 0}</td><td>${a.validEnd || '-'}</td><td>${accountStatus(a.status)}</td><td><button class="btn btn-primary btn-sm" data-consume-account="${a.id}" data-card="${escapeHtml(a.cardName || '')}">消费</button> <button class="btn btn-danger btn-sm" data-close-account="${a.id}">销卡</button></td></tr>`);
        document.querySelectorAll('[data-consume-account]').forEach(btn => btn.onclick = () => showConsumeDialog(btn.dataset.consumeAccount, btn.dataset.card));
        document.querySelectorAll('[data-close-account]').forEach(btn => btn.onclick = () => showCloseDialog(btn.dataset.closeAccount));
    } catch (e) { tableError(e, 8); }
}

async function loadTransactions(el) {
    el.innerHTML = listShell('账户流水', '', '', '', ['客户','账户ID','类型','金额','次数','变动前','变动后','备注','时间']);
    try {
        const res = await api.getCrmAccountTransactions(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, t => `<tr><td><strong>${escapeHtml(t.memberName || '-')}</strong><div class="muted">${escapeHtml(t.memberId)}</div></td><td>${escapeHtml(t.accountId)}</td><td>${txType(t.transactionType)}</td><td>${t.amount || 0}</td><td>${t.countChange || 0}</td><td>¥${t.balanceBefore || 0}</td><td>¥${t.balanceAfter || 0}</td><td>${escapeHtml(t.notes || '-')}</td><td>${formatDate(t.createDate)}</td></tr>`);
    } catch (e) { tableError(e, 9); }
}

async function loadCardCloses(el) {
    el.innerHTML = listShell('销卡管理', '', '', '', ['客户ID','账户ID','原因','退款','剩余次数','状态','反馈ID','时间']);
    try {
        const res = await api.getCrmCardCloses(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, c => `<tr><td><strong>${escapeHtml(c.memberName || '-')}</strong><div class="muted">${escapeHtml(c.memberId)}</div></td><td>${escapeHtml(c.accountId)}</td><td>${escapeHtml(c.reason || '-')}</td><td>¥${c.refundAmount || 0}</td><td>${c.remainingCount || 0}</td><td>${escapeHtml(c.status)}</td><td>${escapeHtml(c.feedbackRecordId || '-')}</td><td>${formatDate(c.createDate)}</td></tr>`);
    } catch (e) { tableError(e, 8); }
}

async function loadSuggestions(el) {
    el.innerHTML = listShell('建议管理', '新增建议', 'suggestionAddBtn', '', ['内容','标签','优先级','提出人','来源','次数','状态','处理说明','时间','操作']);
    document.getElementById('suggestionAddBtn').onclick = () => showSuggestionDialog();
    try {
        const res = await api.getCrmSuggestions(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, s => `<tr><td>${escapeHtml(s.content)}<div class="muted">${escapeHtml(s.category || '-')}</div></td><td>${tags(s.tags)}</td><td>${priorityBadge(s.priority)}</td><td><strong>${escapeHtml(s.submitterName || s.memberName || '-')}</strong><div class="muted">${escapeHtml(s.memberName && s.submitterName && s.memberName !== s.submitterName ? s.memberName : s.memberId || '-')}</div></td><td>${escapeHtml(s.source || '-')}</td><td>${s.frequency || 1}</td><td>${suggestionStatusBadge(s.status)}</td><td>${escapeHtml(s.handleNotes || '-')}</td><td>${formatDate(s.createDate)}</td><td><button class="btn btn-primary btn-sm" data-sug-adopting="${s.id}">采纳中</button> <button class="btn btn-primary btn-sm" data-sug-adopt="${s.id}">已采纳</button> <button class="btn btn-secondary btn-sm" data-sug-ignore="${s.id}">忽略</button></td></tr>`);
        document.querySelectorAll('[data-sug-adopting]').forEach(btn => btn.onclick = () => showSuggestionStatusDialog(btn.dataset.sugAdopting, 'adopting'));
        document.querySelectorAll('[data-sug-adopt]').forEach(btn => btn.onclick = () => showSuggestionStatusDialog(btn.dataset.sugAdopt, 'adopted'));
        document.querySelectorAll('[data-sug-ignore]').forEach(btn => btn.onclick = () => showSuggestionStatusDialog(btn.dataset.sugIgnore, 'ignored'));
    } catch (e) { tableError(e, 10); }
}

async function loadIssues(el) {
    el.innerHTML = listShell('问题修复', '新增问题', 'issueAddBtn', '', ['标题','分类','严重度','状态','负责人','修复方案','时间','操作']);
    document.getElementById('issueAddBtn').onclick = () => showIssueDialog();
    try {
        const res = await api.getCrmIssues(new URLSearchParams({ page: currentPage, page_size: pageSize }).toString());
        renderRows(res.data || {}, i => `<tr><td>${escapeHtml(i.title)}</td><td>${escapeHtml(i.category || '-')}</td><td>${escapeHtml(i.severity)}</td><td>${escapeHtml(i.status)}</td><td>${escapeHtml(i.assignedTo || '-')}</td><td>${escapeHtml(i.fixPlan || '-')}</td><td>${formatDate(i.createDate)}</td><td><button class="btn btn-primary btn-sm" data-issue-fixed="${i.id}">标记修复</button></td></tr>`);
        document.querySelectorAll('[data-issue-fixed]').forEach(btn => btn.onclick = () => updateIssue(btn.dataset.issueFixed, { status: 'fixed' }));
    } catch (e) { tableError(e, 8); }
}

function listShell(title, addText, addId, filters, headers) {
    return `<div class="card"><div class="filter-bar"><div class="card-title" style="margin:0;flex:1">${title}</div>${filters || ''}${addText ? `<button class="btn btn-primary btn-sm" id="${addId}">${addText}</button>` : ''}</div><div class="table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody id="crmTableBody"><tr><td colspan="${headers.length}" class="loading"><div class="spinner"></div></td></tr></tbody></table></div><div id="crmPagination" class="pagination"></div></div>`;
}

function renderRows(data, rowFn) {
    const tbody = document.getElementById('crmTableBody');
    const list = data.list || [];
    if (!list.length) { tbody.innerHTML = `<tr><td colspan="20" class="empty-state">暂无数据</td></tr>`; return; }
    tbody.innerHTML = list.map(rowFn).join('');
    renderPagination(data);
}
function renderPagination(data) {
    const el = document.getElementById('crmPagination'); if (!el) return;
    const total = data.total || 0; const totalPages = Math.ceil(total / pageSize) || 1;
    el.innerHTML = `<div class="pagination-info">共 ${total} 条，第 ${currentPage}/${totalPages} 页</div><div class="pagination-btns"><button ${currentPage<=1?'disabled':''} id="crmPrev">上一页</button><button class="active">${currentPage}</button><button ${currentPage>=totalPages?'disabled':''} id="crmNext">下一页</button></div>`;
    document.getElementById('crmPrev')?.addEventListener('click', () => { currentPage--; loadTab(); });
    document.getElementById('crmNext')?.addEventListener('click', () => { currentPage++; loadTab(); });
}
function tableError(e, colspan) { document.getElementById('crmTableBody').innerHTML = `<tr><td colspan="${colspan}" class="empty-state">加载失败：${escapeHtml(e.message)}</td></tr>`; }
function error(e) { return `<div class="empty-state">加载失败：${escapeHtml(e.message)}</div>`; }
function tags(arr) { if (!arr) return ''; if (typeof arr === 'string') return `<span class="badge badge-gray">${escapeHtml(arr)}</span>`; return (arr || []).map(x => `<span class="badge badge-blue" style="margin-right:4px">${escapeHtml(x)}</span>`).join(''); }
function accountStatus(s) { return s === 1 ? '<span class="badge badge-green">使用中</span>' : s === 0 ? '<span class="badge badge-red">已销卡</span>' : '<span class="badge badge-yellow">已过期</span>'; }
function packageStatus(s) { return s === 1 ? '<span class="badge badge-green">使用中</span>' : s === 0 ? '<span class="badge badge-gray">已用完</span>' : '<span class="badge badge-yellow">已过期</span>'; }
function priorityBadge(p) { const map = { urgent: ['紧急','badge-red'], high: ['高','badge-yellow'], medium: ['中','badge-blue'], low: ['低','badge-gray'] }; const it = map[p] || map.medium; return `<span class="badge ${it[1]}">${it[0]}</span>`; }
function suggestionStatusBadge(s) { const map = { pending: ['待处理','badge-yellow'], adopting: ['采纳中','badge-blue'], adopted: ['已采纳','badge-green'], ignored: ['已忽略','badge-gray'], duplicate: ['重复','badge-gray'] }; const it = map[s] || [s || '-', 'badge-gray']; return `<span class="badge ${it[1]}">${it[0]}</span>`; }
function txType(t) {
    const map = { recharge: '充值/开卡', consume: '消费', refund: '退款', close: '销卡', adjust: '调整' };
    const cls = t === 'consume' || t === 'close' ? 'badge-yellow' : 'badge-green';
    return `<span class="badge ${cls}">${map[t] || escapeHtml(t || '-')}</span>`;
}

function modal(title, body, onSave) {
    const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="modal-card"><div class="modal-header"><h3>${title}</h3><button class="modal-close">&times;</button></div><div class="modal-body">${body}<div class="login-error" id="crmModalErr"></div></div><div class="modal-footer"><button class="btn btn-secondary" id="crmCancel">取消</button><button class="btn btn-primary" id="crmSave">保存</button></div></div>`;
    document.body.appendChild(overlay); const close = () => document.body.removeChild(overlay);
    overlay.querySelector('.modal-close').onclick = close; overlay.querySelector('#crmCancel').onclick = close;
    overlay.querySelector('#crmSave').onclick = async () => { try { await onSave(); close(); loadTab(); } catch(e) { document.getElementById('crmModalErr').textContent = e.message || '保存失败'; } };
}
function val(id) { return document.getElementById(id)?.value.trim(); }
function dateInput(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}
function jsonList(s) { return s ? s.split(/[，,\n]/).map(x => x.trim()).filter(Boolean) : []; }
function fillMemberPicker(prefix) {
    const input = document.getElementById(`${prefix}MemberKeyword`);
    const dropdown = document.getElementById(`${prefix}MemberDropdown`);
    const idEl = document.getElementById(`${prefix}Member`);
    const manualEl = document.getElementById(`${prefix}MemberManual`);
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
        } catch (e) {
            dropdown.innerHTML = `<div class="member-option disabled">搜索失败：${escapeHtml(e.message)}</div>`;
            dropdown.classList.add('open');
        }
    };
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 250); });
    input.addEventListener('focus', () => { if (dropdown.innerHTML) dropdown.classList.add('open'); });
    document.addEventListener('click', (e) => { if (!e.target.closest(`#${prefix}MemberBox`)) dropdown.classList.remove('open'); });
}
function memberPicker(prefix, label = '客户') {
    return `<div class="form-group member-combobox" id="${prefix}MemberBox"><label class="form-label">${label}</label><input id="${prefix}MemberKeyword" class="form-input" autocomplete="off" placeholder="输入姓名/手机号搜索并选择"><input id="${prefix}Member" type="hidden"><div id="${prefix}MemberDropdown" class="member-dropdown"></div><input id="${prefix}MemberManual" class="form-input member-manual" placeholder="客户ID备用输入（可选）"></div>`;
}
function pickedMember(prefix) { return val(`${prefix}Member`) || val(`${prefix}MemberManual`); }
function mekai66Form(prefix, values = {}) {
    const groups = {};
    MEKAI66_FIELDS.forEach(f => { (groups[f.category] ||= []).push(f); });
    return `<div class="form-group"><label class="form-label">麦凯66客户档案</label><div class="mekai66-grid">${Object.entries(groups).map(([cat, fields]) => `<div class="mekai66-group"><div class="mekai66-title">${cat}</div>${fields.map(f => `<label class="mekai66-field"><span>${f.label}</span><input id="${prefix}Mekai_${f.key}" class="form-input" value="${escapeHtml(values?.[f.key] || '')}"></label>`).join('')}</div>`).join('')}</div></div>`;
}
function collectMekai66(prefix) {
    const data = {};
    MEKAI66_FIELDS.forEach(f => {
        const value = val(`${prefix}Mekai_${f.key}`);
        if (value) data[f.key] = value;
    });
    return data;
}

function showMemberDialog() {
    modal('新增客户', `
        <div class="form-row">
            <div class="form-group"><label class="form-label">姓名</label><input id="mName" class="form-input"></div>
            <div class="form-group"><label class="form-label">手机号</label><input id="mPhone" class="form-input"></div>
        </div>
        <div class="form-row">
            <div class="form-group"><label class="form-label">微信号</label><input id="mWechat" class="form-input"></div>
            <div class="form-group"><label class="form-label">客户等级</label><input id="mLevel" class="form-input" placeholder="VIP/老客/新客"></div>
        </div>
        <div class="form-group"><label class="form-label">美容关注点（逗号分隔）</label><input id="mBeauty" class="form-input" placeholder="皮肤干燥,肩颈"></div>
        <div class="form-group"><label class="form-label">身体不适/疾病/禁忌</label><textarea id="mHealth" class="form-input"></textarea></div>
        <div class="form-group"><label class="form-label">过敏信息</label><textarea id="mAllergies" class="form-input"></textarea></div>
        ${mekai66Form('m')}
        <div class="form-group"><label class="form-label">备注</label><textarea id="mNotes" class="form-input"></textarea></div>`,
        () => api.createCrmMember({
            name: val('mName'), phone: val('mPhone'), wechat: val('mWechat'), level: val('mLevel'),
            beautyConcerns: jsonList(val('mBeauty')), healthIssues: jsonList(val('mHealth')),
            allergies: val('mAllergies'), mekaiTags: collectMekai66('m'), notes: val('mNotes')
        })
    );
}
function showEditMemberDialog(m) {
    modal('编辑客户', `
        <div class="form-row">
            <div class="form-group"><label class="form-label">姓名</label><input id="emName" class="form-input" value="${escapeHtml(m.name || '')}"></div>
            <div class="form-group"><label class="form-label">手机号</label><input id="emPhone" class="form-input" value="${escapeHtml(m.phone || '')}"></div>
        </div>
        <div class="form-row">
            <div class="form-group"><label class="form-label">微信号</label><input id="emWechat" class="form-input" value="${escapeHtml(m.wechat || '')}"></div>
            <div class="form-group"><label class="form-label">客户等级</label><input id="emLevel" class="form-input" value="${escapeHtml(m.level || '')}"></div>
        </div>
        <div class="form-group"><label class="form-label">美容关注点</label><input id="emBeauty" class="form-input" value="${escapeHtml((m.beautyConcerns || []).join ? m.beautyConcerns.join(',') : (m.beautyConcerns || ''))}"></div>
        <div class="form-group"><label class="form-label">身体不适/疾病/禁忌</label><textarea id="emHealth" class="form-input">${escapeHtml((m.healthIssues || []).join ? m.healthIssues.join('\n') : (m.healthIssues || ''))}</textarea></div>
        <div class="form-group"><label class="form-label">过敏信息</label><textarea id="emAllergies" class="form-input">${escapeHtml(m.allergies || '')}</textarea></div>
        ${mekai66Form('em', m.mekaiTags || {})}
        <div class="form-group"><label class="form-label">备注</label><textarea id="emNotes" class="form-input">${escapeHtml(m.notes || '')}</textarea></div>`,
        () => api.updateCrmMember(m.id, {
            name: val('emName'), phone: val('emPhone'), wechat: val('emWechat'), level: val('emLevel'),
            beautyConcerns: jsonList(val('emBeauty')), healthIssues: jsonList(val('emHealth')),
            allergies: val('emAllergies'), mekaiTags: collectMekai66('em'), notes: val('emNotes')
        })
    );
}

function showVisitDialog(defaultMemberId = '') {
    modal('新增到店记录', `
        ${memberPicker('v')}
        <div class="form-row"><div class="form-group"><label class="form-label">员工ID</label><input id="vEmp" class="form-input"></div><div class="form-group"><label class="form-label">满意度</label><select id="vSat" class="form-input"><option value="">未填写</option><option value="very_satisfied">非常满意</option><option value="satisfied">满意</option><option value="unsatisfied">不满意</option><option value="very_bad">很差</option></select></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">到店时间</label><input id="vArrive" type="datetime-local" class="form-input"></div><div class="form-group"><label class="form-label">离店时间</label><input id="vLeave" type="datetime-local" class="form-input"></div></div>
        <div class="form-group"><label class="form-label">服务项目</label><input id="vItems" class="form-input"></div>
        <div class="form-group"><label class="form-label">消费金额</label><input id="vAmount" type="number" class="form-input"></div>`,
        () => api.createCrmVisit({ memberId: pickedMember('v'), employeeId: val('vEmp'), arriveAt: val('vArrive'), leaveAt: val('vLeave'), serviceItems: jsonList(val('vItems')), consumptionAmount: val('vAmount'), satisfaction: val('vSat') })
    );
    fillMemberPicker('v');
    if (defaultMemberId) document.getElementById('vMemberManual').value = defaultMemberId;
}
function showAccountDialog(defaultMemberId = '') {
    modal('开卡/建账户', `
        ${memberPicker('a')}
        <div class="form-row"><div class="form-group"><label class="form-label">卡名称</label><input id="aName" class="form-input"></div><div class="form-group"><label class="form-label">类型</label><select id="aType" class="form-input"><option value="balance">储值卡</option><option value="count">次卡</option><option value="course">疗程卡</option></select></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">金额</label><input id="aAmount" type="number" class="form-input"></div><div class="form-group"><label class="form-label">次数</label><input id="aCount" type="number" class="form-input"></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">有效期开始</label><input id="aStart" type="date" class="form-input"></div><div class="form-group"><label class="form-label">有效期结束</label><input id="aEnd" type="date" class="form-input"></div></div>`,
        () => api.createCrmAccount({ memberId: pickedMember('a'), cardName: val('aName'), accountType: val('aType'), totalAmount: val('aAmount'), totalCount: val('aCount'), validStart: val('aStart'), validEnd: val('aEnd') })
    );
    fillMemberPicker('a');
    if (defaultMemberId) document.getElementById('aMemberManual').value = defaultMemberId;
}
function showBodyStatusDialog(defaultMemberId = '') {
    modal('新增身体变化状态', `
        ${memberPicker('bs')}
        <div class="form-row"><div class="form-group"><label class="form-label">体重kg（默认指标）</label><input id="bsWeight" type="number" class="form-input"></div><div class="form-group"><label class="form-label">腰围cm（默认指标）</label><input id="bsWaist" type="number" class="form-input"></div></div>
        <div class="form-group"><label class="form-label">自定义身体标签</label><input id="bsMetricName" class="form-input" placeholder="如：膝盖积液 / 脚踝扭伤 / 肩颈酸痛"></div>
        <div class="form-row"><div class="form-group"><label class="form-label">状态</label><select id="bsMetricStatus" class="form-input"><option value="没啥效果">没啥效果</option><option value="有改善">有改善</option><option value="有好转">有好转</option><option value="明显好转">明显好转</option></select></div><div class="form-group"><label class="form-label">好转数值（可选）</label><input id="bsMetricValue" type="number" class="form-input" placeholder="如疼痛减少3分"></div></div>
        <div class="form-group"><label class="form-label">描述记录</label><textarea id="bsNotes" class="form-input" placeholder="如：膝盖最近温度变高；脚踝变好，开车不疼了"></textarea></div>`,
        () => api.createCrmBodyStatus({ memberId: pickedMember('bs'), weight: val('bsWeight'), waistline: val('bsWaist'), metrics: { name: val('bsMetricName'), status: val('bsMetricStatus'), value: val('bsMetricValue') }, notes: val('bsNotes') })
    );
    fillMemberPicker('bs');
    if (defaultMemberId) document.getElementById('bsMemberManual').value = defaultMemberId;
}
function showProductDialog() {
    modal('新增产品/套餐', `
        <div class="form-row"><div class="form-group"><label class="form-label">产品名称</label><input id="pName" class="form-input" placeholder="养生减肥10次套餐"></div><div class="form-group"><label class="form-label">分类</label><input id="pCategory" class="form-input" placeholder="减肥/养生/美容"></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">类型</label><select id="pType" class="form-input"><option value="package">套餐</option><option value="service">服务项目</option><option value="product">实物产品</option></select></div><div class="form-group"><label class="form-label">默认次数</label><input id="pCount" type="number" class="form-input" value="1"></div></div>
        <div class="form-group"><label class="form-label">价格</label><input id="pPrice" type="number" class="form-input" value="0"></div>
        <div class="form-group"><label class="form-label">说明</label><textarea id="pDesc" class="form-input"></textarea></div>`,
        () => api.createCrmProduct({ productName: val('pName'), category: val('pCategory'), productType: val('pType'), defaultCount: val('pCount'), price: val('pPrice'), description: val('pDesc') })
    );
}
async function showMemberPurchaseDialog(memberId) {
    try {
        const res = await api.getCrmProducts('page=1&page_size=100&status=1');
        const products = res.data?.list || [];
        if (!products.length) { alert('暂无产品，请先到产品管理新增产品/套餐'); return; }
        const today = new Date();
        const nextYear = new Date(today); nextYear.setFullYear(today.getFullYear() + 1);
        modal('客户购买产品/套餐', `
            <input id="buyFixedMember" type="hidden" value="${escapeHtml(memberId)}">
            <div class="form-group"><label class="form-label">选择产品/套餐</label><select id="buyProductSelect" class="form-input">${products.map(p => `<option value="${p.id}" data-count="${p.defaultCount || 1}" data-price="${p.price || 0}">${escapeHtml(p.productName)} · ¥${p.price || 0} · ${p.defaultCount || 1}次</option>`).join('')}</select></div>
            <div class="form-row"><div class="form-group"><label class="form-label">单价</label><input id="buyFixedUnit" type="number" class="form-input" value="${products[0].price || 0}"></div><div class="form-group"><label class="form-label">数量/次数</label><input id="buyFixedCount" type="number" class="form-input" value="${products[0].defaultCount || 1}"></div></div>
            <div class="form-row"><div class="form-group"><label class="form-label">折扣（10=原价，8.5=八五折）</label><input id="buyFixedDiscount" type="number" step="0.1" class="form-input" value="10"></div><div class="form-group"><label class="form-label">购买金额</label><input id="buyFixedAmount" type="number" class="form-input" value="${(Number(products[0].price || 0) * Number(products[0].defaultCount || 1)).toFixed(2)}"></div></div>
            <div class="form-row"><div class="form-group"><label class="form-label">有效期开始</label><input id="buyFixedStart" type="date" class="form-input" value="${dateInput(today)}"></div><div class="form-group"><label class="form-label">有效期结束</label><input id="buyFixedEnd" type="date" class="form-input" value="${dateInput(nextYear)}"></div></div>
            <div class="form-group"><label class="form-label">备注</label><textarea id="buyFixedNotes" class="form-input"></textarea></div>`,
            () => api.purchaseCrmProduct({ productId: val('buyProductSelect'), memberId, unitPrice: val('buyFixedUnit'), purchaseCount: val('buyFixedCount'), discount: Number(val('buyFixedDiscount') || 10) / 10, totalCount: val('buyFixedCount'), totalAmount: val('buyFixedAmount'), validStart: val('buyFixedStart'), validEnd: val('buyFixedEnd'), notes: val('buyFixedNotes') })
        );
        const recalc = () => { document.getElementById('buyFixedAmount').value = (Number(val('buyFixedUnit') || 0) * Number(val('buyFixedCount') || 0) * (Number(val('buyFixedDiscount') || 10) / 10)).toFixed(2); };
        document.getElementById('buyProductSelect').onchange = (e) => {
            const opt = e.target.selectedOptions[0];
            document.getElementById('buyFixedUnit').value = opt.dataset.price || 0;
            document.getElementById('buyFixedCount').value = opt.dataset.count || 1;
            recalc();
        };
        ['buyFixedUnit','buyFixedCount','buyFixedDiscount'].forEach(id => document.getElementById(id).oninput = recalc);
    } catch (e) { alert('加载产品失败：' + e.message); }
}
function showPurchaseDialog(productId, productName, count, price) {
    modal(`客户购买 - ${escapeHtml(productName || '')}`, `
        ${memberPicker('buy')}
        <div class="form-row"><div class="form-group"><label class="form-label">总次数</label><input id="buyCount" type="number" class="form-input" value="${escapeHtml(count || '1')}"></div><div class="form-group"><label class="form-label">购买金额</label><input id="buyAmount" type="number" class="form-input" value="${escapeHtml(price || '0')}"></div></div>
        <div class="form-row"><div class="form-group"><label class="form-label">有效期开始</label><input id="buyStart" type="date" class="form-input"></div><div class="form-group"><label class="form-label">有效期结束</label><input id="buyEnd" type="date" class="form-input"></div></div>
        <div class="form-group"><label class="form-label">备注</label><textarea id="buyNotes" class="form-input"></textarea></div>`,
        () => api.purchaseCrmProduct({ productId, memberId: pickedMember('buy'), totalCount: val('buyCount'), totalAmount: val('buyAmount'), validStart: val('buyStart'), validEnd: val('buyEnd'), notes: val('buyNotes') })
    );
    fillMemberPicker('buy');
}
function showProductConsumeDialog(memberProductId, productName = '') {
    modal(`套餐消费 - ${escapeHtml(productName || '')}`, `
        <div class="form-row"><div class="form-group"><label class="form-label">消费次数</label><input id="pcCount" type="number" class="form-input" value="1"></div><div class="form-group"><label class="form-label">消费金额</label><input id="pcAmount" type="number" class="form-input" value="0"></div></div>
        <div class="form-group"><label class="form-label">关联到店记录ID（可选，不填自动关联最近到店）</label><input id="pcVisit" class="form-input"></div>
        <div class="form-group"><label class="form-label">备注</label><textarea id="pcNotes" class="form-input"></textarea></div>`,
        () => api.consumeCrmProduct(memberProductId, { consumeCount: val('pcCount'), consumeAmount: val('pcAmount'), visitId: val('pcVisit'), notes: val('pcNotes') })
    );
}
function showConsumeDialog(accountId, cardName = '') {
    modal(`账户消费 ${cardName ? ' - ' + escapeHtml(cardName) : ''}`, `
        <div class="form-row"><div class="form-group"><label class="form-label">扣减金额</label><input id="xAmount" type="number" class="form-input" value="0"></div><div class="form-group"><label class="form-label">扣减次数</label><input id="xCount" type="number" class="form-input" value="0"></div></div>
        <div class="form-group"><label class="form-label">关联到店记录ID（可选）</label><input id="xVisit" class="form-input"></div>
        <div class="form-group"><label class="form-label">备注</label><textarea id="xNotes" class="form-input" placeholder="例如：肩颈调理消费1次"></textarea></div>`,
        () => api.consumeCrmAccount(accountId, { amount: val('xAmount'), countChange: val('xCount'), visitId: val('xVisit'), notes: val('xNotes') })
    );
}
function showCloseDialog(accountId) { modal('销卡', `<div class="form-group"><label class="form-label">销卡原因</label><textarea id="cReason" class="form-input"></textarea><div class="muted">如包含“不满意/没效果/投诉/退款”等关键词，系统会自动创建待修复问题。</div></div><div class="form-group"><label class="form-label">退款金额</label><input id="cRefund" type="number" class="form-input"></div><div class="form-group"><label class="form-label">关联反馈ID（可选）</label><input id="cFeedback" class="form-input"></div><div class="form-group"><label class="form-label">负责人（可选）</label><input id="cAssigned" class="form-input"></div>`, () => api.closeCrmCard({ accountId, reason: val('cReason'), refundAmount: val('cRefund'), feedbackRecordId: val('cFeedback'), assignedTo: val('cAssigned') })); }
function showSuggestionDialog() { modal('新增建议', `<div class="form-group"><label class="form-label">建议内容</label><textarea id="sContent" class="form-input"></textarea></div><div class="form-group"><label class="form-label">分类</label><input id="sCategory" class="form-input" placeholder="服务/环境/价格"></div>`, () => api.createCrmSuggestion({ content: val('sContent'), category: val('sCategory') })); }
function showIssueDialog() { modal('新增问题', `<div class="form-group"><label class="form-label">标题</label><input id="iTitle" class="form-input"></div><div class="form-row"><div class="form-group"><label class="form-label">分类</label><input id="iCategory" class="form-input"></div><div class="form-group"><label class="form-label">严重度</label><select id="iSeverity" class="form-input"><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="critical">严重</option></select></div></div><div class="form-group"><label class="form-label">描述</label><textarea id="iDesc" class="form-input"></textarea></div><div class="form-group"><label class="form-label">负责人</label><input id="iAssigned" class="form-input"></div>`, () => api.createCrmIssue({ title: val('iTitle'), category: val('iCategory'), severity: val('iSeverity'), description: val('iDesc'), assignedTo: val('iAssigned') })); }
function showSuggestionStatusDialog(id, status) {
    const titleMap = { adopting: '标记采纳中', adopted: '标记已采纳', ignored: '忽略建议' };
    const title = titleMap[status] || '更新建议';
    const noteLabel = status === 'ignored' ? '忽略原因/处理说明' : '采纳方案/处理说明';
    modal(title, `<div class="form-group"><label class="form-label">${noteLabel}</label><textarea id="sHandleNotes" class="form-input"></textarea></div>`,
        () => api.updateCrmSuggestionStatus(id, {
            status,
            handleNotes: val('sHandleNotes'),
            rejectedReason: status === 'rejected' ? val('sHandleNotes') : ''
        })
    );
}
async function updateIssue(id, data) { await api.updateCrmIssue(id, data); loadTab(); }
function bindDetailButtons(list) {
    document.querySelectorAll('[data-detail]').forEach(btn => {
        btn.onclick = async () => {
            try {
                const res = await api.getCrmMember(btn.dataset.detail);
                showMemberDetail(res.data || {});
            } catch (e) {
                alert(e.message || '加载客户详情失败');
            }
        };
    });
}

function showMemberDetail(m) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card crm-detail-modal">
        <div class="modal-header">
            <h3>${escapeHtml(m.name || '客户详情')} <span class="badge badge-blue">${escapeHtml(m.level || '客户')}</span></h3>
            <button class="modal-close" id="memberDetailClose">&times;</button>
        </div>
        <div class="modal-body">
            <div class="crm-detail-actions">
                <button class="btn btn-primary btn-sm" id="detailAddBody">记录身体变化</button>
                <button class="btn btn-primary btn-sm" id="detailBuyProduct">购买产品/套餐</button>
                <button class="btn btn-primary btn-sm" id="detailAddAppointment">预约服务</button>
                <button class="btn btn-secondary btn-sm" id="detailAddVisit">新增到店</button>
                <button class="btn btn-secondary btn-sm" id="detailAddAccount">开卡/建账户</button>
                <button class="btn btn-secondary btn-sm" id="detailEditMember">编辑客户</button>
            </div>
            <div class="crm-profile-head">
                <div><div class="muted">手机号</div><strong>${escapeHtml(m.phone || '-')}</strong></div>
                <div><div class="muted">微信</div><strong>${escapeHtml(m.wechat || '-')}</strong></div>
                <div><div class="muted">到店次数</div><strong>${m.totalVisits || 0}</strong></div>
                <div><div class="muted">累计消费</div><strong>¥${m.totalSpent || 0}</strong></div>
            </div>
            ${detailSection('美容关注', tags(m.beautyConcerns) || '-')}
            ${detailSection('身体不适/疾病/禁忌', tags(m.healthIssues) || '-')}
            ${detailSection('过敏信息', escapeHtml(m.allergies || '-'))}
            ${detailSection('麦凯66/客户信息', `<pre class="crm-pre">${escapeHtml(JSON.stringify(m.mekaiTags || {}, null, 2))}</pre>`)}
            ${detailSection('备注', escapeHtml(m.notes || '-'))}
            ${bodyTrendSection(m.bodyStatuses || [])}
            ${timelineSection('身体变化', m.bodyStatuses, b => `${formatDate(b.recordDate)} · 体重${b.weight ?? '-'}kg · 腰围${b.waistline ?? '-'}cm · ${escapeHtml(b.metrics?.name || '身体状态')}：${escapeHtml(b.metrics?.status || '-')} ${b.metrics?.value ? `(${escapeHtml(b.metrics.value)})` : ''} · ${escapeHtml(b.notes || '')}`)}
            ${timelineSection('到店记录', m.visits, v => `${formatDate(v.arriveAt)} · ${v.durationMinutes || '-'}分钟 · ${tags(v.serviceItems)} · ¥${v.consumptionAmount || 0}`)}
            ${timelineSection('账户/卡', m.accounts, a => `${escapeHtml(a.cardName || a.accountType)} · 余额 ¥${a.balanceAmount || 0} · 剩余 ${a.balanceCount || 0} 次 · ${accountStatus(a.status)}`)}
            ${timelineSection('账户流水', m.transactions, t => `${formatDate(t.createDate)} · ${txType(t.transactionType)} · 金额 ${t.amount || 0} · 次数 ${t.countChange || 0} · 余额 ¥${t.balanceAfter || 0} · ${escapeHtml(t.notes || '')}`)}
            ${timelineSection('已购产品/套餐', m.products, p => `${escapeHtml(p.productName)} · 剩余 ${p.balanceCount || 0}/${p.totalCount || 0} 次 · ¥${p.balanceAmount || 0}/¥${p.totalAmount || 0} · ${packageStatus(p.status)}`)}
            ${timelineSection('产品消费记录', m.productConsumes, c => `${formatDate(c.createDate)} · 消费${c.consumeCount || 0}次 · ¥${c.consumeAmount || 0} · 剩余${c.balanceCountAfter || 0}次 · ${escapeHtml(c.notes || '')}`)}
            ${timelineSection('客户反馈', m.feedbacks, f => `${formatDate(f.createDate)} · ${satisfactionBadge(f.satisfaction)} · ${escapeHtml(truncate(f.cleanedText || f.rawAsrText || '-', 120))}`)}
            ${timelineSection('建议', m.suggestions, s => `${escapeHtml(s.content)} · ${suggestionStatusBadge(s.status)} · ${priorityBadge(s.priority)} · ${tags(s.tags)} · ${s.frequency || 1}次`)}
        </div>
        <div class="modal-footer"><button class="btn btn-secondary" id="memberDetailCloseBtn">关闭</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const close = () => document.body.removeChild(overlay);
    document.getElementById('memberDetailClose').onclick = close;
    document.getElementById('memberDetailCloseBtn').onclick = close;
    document.getElementById('detailAddBody').onclick = () => { close(); showBodyStatusDialog(m.id); };
    document.getElementById('detailBuyProduct').onclick = () => { close(); showMemberPurchaseDialog(m.id); };
    document.getElementById('detailAddAppointment').onclick = () => { close(); showAppointmentDialog(m.id); };
    document.getElementById('detailAddVisit').onclick = () => { close(); showVisitDialog(m.id); };
    document.getElementById('detailAddAccount').onclick = () => { close(); showAccountDialog(m.id); };
    document.getElementById('detailEditMember').onclick = () => { close(); showEditMemberDialog(m); };
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
}

function bodyTrendSection(list) {
    if (!list || list.length < 2) return '';
    const sorted = [...list].reverse();
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    const delta = (key, unit = '') => {
        if (first[key] == null || last[key] == null) return '-';
        const d = Number(last[key]) - Number(first[key]);
        return `${d > 0 ? '+' : ''}${d}${unit}`;
    };
    const latestMetrics = (list || []).slice(0, 3).map(b => `${escapeHtml(b.metrics?.name || '身体状态')}：${escapeHtml(b.metrics?.status || '-')} ${b.notes ? '· ' + escapeHtml(b.notes) : ''}`).join('<br>') || '-';
    return `<div class="crm-detail-section"><div class="crm-detail-title">身体变化趋势</div><div class="crm-trend-grid"><div>体重变化<br><strong>${delta('weight', 'kg')}</strong></div><div>腰围变化<br><strong>${delta('waistline', 'cm')}</strong></div><div style="grid-column: span 2">最近标签变化<br><strong style="font-size:13px;line-height:1.5">${latestMetrics}</strong></div></div></div>`;
}

function detailSection(title, body) {
    return `<div class="crm-detail-section"><div class="crm-detail-title">${title}</div><div class="crm-detail-body">${body}</div></div>`;
}

function timelineSection(title, list, render) {
    const rows = (list || []).length
        ? list.map(item => `<li>${render(item)}</li>`).join('')
        : '<li class="muted">暂无</li>';
    return `<div class="crm-detail-section"><div class="crm-detail-title">${title}</div><ul class="crm-timeline">${rows}</ul></div>`;
}

window.CrmForms = {
    'crm.member.create': (payload = {}) => {
        showMemberDialog();
        setTimeout(() => {
            FormCopilot.fill({
                mName: payload.name,
                mPhone: payload.phone,
                mBeauty: payload.beautyConcerns,
                mHealth: payload.healthIssues,
                mNotes: payload.notes,
            });
            if (payload.gender) document.getElementById('mMekai_gender') && (document.getElementById('mMekai_gender').value = payload.gender === 1 ? '男' : '女');
            Object.entries(payload.mekaiTags || {}).forEach(([k, v]) => FormCopilot.setValue(`mMekai_${k}`, v));
        }, 80);
    },
    'crm.product.create': (payload = {}) => {
        showProductDialog();
        setTimeout(() => FormCopilot.fill({
            pName: payload.productName,
            pCategory: payload.category,
            pType: payload.productType,
            pCount: payload.defaultCount,
            pPrice: payload.price,
            pDesc: payload.description,
        }), 80);
    },
    'crm.appointment.create': (payload = {}) => {
        showAppointmentDialog('', '', '');
        setTimeout(() => {
            FormCopilot.fill({ aptStart: normalizeStartHint(payload.startHint), aptProductName: payload.serviceKeyword });
            if (payload.employeeName) selectEmployeeByName('aptEmp', payload.employeeName);
        }, 120);
    },
    'crm.body_status.create': (payload = {}) => showBodyStatusDialog(payload.memberId || ''),
    'crm.product.purchase': (payload = {}) => showMemberPurchaseDialog(payload.memberId || ''),
    'crm.suggestion.create': (payload = {}) => showSuggestionDialog(payload.content || ''),
};

function selectEmployeeByName(selectId, name) {
    const sel = document.getElementById(selectId); if (!sel || !name) return;
    const opt = Array.from(sel.options).find(o => o.textContent.includes(name));
    if (opt) sel.value = opt.value;
}
function normalizeStartHint(hint) {
    if (!hint) return '';
    const base = new Date();
    if (hint.includes('明天')) base.setDate(base.getDate() + 1);
    if (hint.includes('后天')) base.setDate(base.getDate() + 2);
    let hour = 10;
    const cn = { '一':1, '二':2, '两':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10 };
    const m = hint.match(/(\d{1,2}|[一二两三四五六七八九十])点/);
    if (m) hour = /^\d+$/.test(m[1]) ? Number(m[1]) : cn[m[1]] || hour;
    if (hint.includes('下午') && hour < 12) hour += 12;
    return `${dateInput(base)}T${String(hour).padStart(2,'0')}:00`;
}
