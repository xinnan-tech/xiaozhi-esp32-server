// 主应用模块 - SPA路由 + 状态管理 + 页面视图

import { FeedbackAPI, WS_BASE } from './api.js';
import { copyToClipboard, showManualCopySheet, isMobile, speak, openDianping, openMeituan, getEmployeeTypeLabel } from './utils.js';
import { getAudioPlayer } from './audio-player.js';
import { getAudioRecorder, checkMicrophoneAvailability } from './audio-recorder.js';
import { checkOpusLoaded } from './opus-codec.js';

// 等待 Opus 库异步初始化完成
async function waitForOpusReady(maxWait = 5000) {
    const start = Date.now();
    while (Date.now() - start < maxWait) {
        if (typeof Module !== 'undefined') {
            // Module.instance 是工厂函数返回的实例
            const inst = (typeof Module.instance !== 'undefined') ? Module.instance : Module;
            if (typeof inst._opus_decoder_get_size === 'function' &&
                typeof inst._opus_encoder_get_size === 'function') {
                window.ModuleInstance = inst;
                console.log('[Opus] 库初始化完成');
                return true;
            }
        }
        await new Promise(r => setTimeout(r, 100));
    }
    console.warn('[Opus] 库初始化超时');
    return false;
}

// 启动时初始化 Opus
waitForOpusReady().then(() => checkOpusLoaded());

// 应用状态
const appState = {
    currentPage: 'home',
    storeCode: '',
    storeInfo: null,
    employees: [],
    selectedEmployee: null,
    deviceMac: '',
    sessionId: '',
    chatMessages: [],
    customerName: '',
    phoneTail: '',
    customerIdentity: null,
    feedbackResult: null,
    ws: null,
    otaResult: null,
    live2dManager: null,
    audioPlayer: null,
    audioRecorder: null,
    isRemoteSpeaking: false,
    appointment: null,
};

// 暴露给 Live2D 使用
window.chatApp = appState;

// 从URL参数读取store code
function getUrlParams() {
    const hash = window.location.hash || '#/home';
    const [path, query] = hash.substring(2).split('?');
    const params = {};
    if (query) {
        query.split('&').forEach(p => {
            const [k, v] = p.split('=');
            params[k] = decodeURIComponent(v);
        });
    }
    return { path, params };
}

function navigate(page) {
    window.location.hash = `#/${page}`;
}

// 页面渲染入口
function render() {
    const { path, params } = getUrlParams();
    const app = document.getElementById('app');

    switch (path) {
        case 'home':
            appState.storeCode = params.code || '';
            renderHome(app);
            break;
        case 'appointment':
            appState.storeCode = params.storeCode || params.code || '';
            renderAppointment(app);
            break;
        case 'voice':
            renderVoice(app);
            break;
        case 'result':
            renderResult(app);
            break;
        case 'publish':
            renderPublish(app);
            break;
        case 'complete':
            renderComplete(app);
            break;
        default:
            renderHome(app);
    }
}

// ==================== 客户预约页 ====================
function todayISO() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function appointmentSpeak(text) {
    try {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'zh-CN';
            u.rate = 1;
            window.speechSynthesis.speak(u);
        }
    } catch (e) {}
}

function showVoiceUnlockHint(message = '手机浏览器需要点一下才能开启麦克风和语音播报') {
    const btn = document.getElementById('aptStartVoiceBtn');
    const status = document.getElementById('aptListenStatus');
    if (btn) btn.style.display = 'block';
    if (status) status.textContent = message;
}

function hideVoiceUnlockHint() {
    const btn = document.getElementById('aptStartVoiceBtn');
    if (btn) btn.style.display = 'none';
}

function unlockAppointmentVoice() {
    const state = appState.appointment;
    if (!state || state.completed) return;
    state.voiceUnlocked = true;
    hideVoiceUnlockHint();
    try {
        // 用一次空播报解锁移动端 TTS；部分浏览器需要用户手势触发。
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance('');
            u.lang = 'zh-CN';
            window.speechSynthesis.speak(u);
        }
    } catch (e) {}
    startAppointmentAutoListen();
}

function renderAppointment(container) {
    container.innerHTML = `
    <div class="page appointment-page">
        <div class="appointment-hero">
            <div class="appointment-kicker">智能预约</div>
            <h1 id="aptStoreName">正在加载门店...</h1>
            <p id="aptSubtitle">我会先读取今天所有技师排期，为您快速预约</p>
        </div>
        <div id="aptError" class="error-message" style="display:none"></div>
        <div id="aptMain" style="display:none">
            <div class="apt-card">
                <div class="apt-card-title">请选择服务技师</div>
                <div id="aptEmployees" class="apt-employee-list"></div>
            </div>
            <div class="apt-card">
                <div class="apt-card-title">可预约时间</div>
                <div id="aptSlots" class="apt-slot-list"><div class="apt-muted">请先选择技师</div></div>
            </div>
            <div class="apt-card">
                <div class="apt-card-title">预约信息</div>
                <div class="apt-form-grid">
                    <input id="aptPhone" class="apt-input" placeholder="请直接说或输入手机号" inputmode="tel">
                    <button id="aptLookupBtn" class="btn-secondary">查询我的项目</button>
                </div>
                <div id="aptMemberInfo" class="apt-member-info" style="display:none"></div>
                <div id="aptProducts" class="apt-product-list"><div class="apt-muted">输入手机号后自动查询可预约项目</div></div>
                <div id="aptExistingAppointments" class="apt-product-list" style="display:none"></div>
                <div id="aptConfirmText" class="apt-confirm-text">请选择技师、时间和项目</div>
                <button id="aptSubmitBtn" class="btn-primary btn-large" disabled>确认预约</button>
            </div>
            <div class="apt-voice-panel" id="aptVoicePanel">
                <div id="aptAiText" class="apt-ai-text">我会自动听您说话。您可以直接说：我要约2号技师下午3点，或直接说手机号。</div>
                <button id="aptStartVoiceBtn" class="apt-start-voice-btn" style="display:none">点一下开启语音助手</button>
                <div id="aptListenStatus" class="apt-listen-status">正在启动语音监听...</div>
            </div>
        </div>
    </div>`;
    initAppointmentPage();
}

async function initAppointmentPage() {
    const err = document.getElementById('aptError');
    if (!appState.storeCode) {
        err.textContent = '缺少门店编码，请确认预约链接是否正确';
        err.style.display = 'block';
        return;
    }
    const result = await FeedbackAPI.appointmentBootstrap(appState.storeCode, todayISO(), 60);
    if (!result.success) {
        err.textContent = result.message || '预约初始化失败';
        err.style.display = 'block';
        return;
    }
    const data = result.data;
    appState.appointment = {
        store: data.store,
        date: data.date,
        durationMinutes: data.durationMinutes || 60,
        employees: data.employees || [],
        availability: data.availability || { slots: [] },
        selectedEmployee: null,
        selectedSlot: null,
        member: null,
        products: [],
        selectedProduct: null,
        recognition: null,
        listening: false,
        completed: false,
        voiceUnlocked: false,
        intent: 'book',
        myAppointments: [],
        selectedExistingAppointment: null,
    };
    document.getElementById('aptStoreName').textContent = data.store.storeName;
    document.getElementById('aptSubtitle').textContent = `今天可预约技师 ${appState.appointment.employees.length} 位，已为您提前加载空闲时间`;
    document.getElementById('aptMain').style.display = 'block';
    renderAppointmentEmployees();
    const names = appState.appointment.employees.map(e => `${e.number}号技师${e.name}`).join('、');
    setAppointmentAiText(`您好，今天可以预约的技师有：${names}。请问您想预约哪位技师？`, true);
    setTimeout(startAppointmentAutoListen, 800);
    document.getElementById('aptSubmitBtn').addEventListener('click', submitAppointment);
    document.getElementById('aptVoicePanel').addEventListener('click', unlockAppointmentVoice);
    document.getElementById('aptStartVoiceBtn').addEventListener('click', unlockAppointmentVoice);
    document.addEventListener('click', unlockAppointmentVoice, { once: true });
    document.getElementById('aptLookupBtn').addEventListener('click', lookupAppointmentProductsFromInput);
    document.getElementById('aptPhone').addEventListener('input', (e) => {
        const phone = (e.target.value || '').replace(/\D/g, '');
        if (phone.length >= 11) lookupAppointmentProducts(phone);
    });
}

function renderAppointmentEmployees() {
    const list = document.getElementById('aptEmployees');
    const state = appState.appointment;
    list.innerHTML = state.employees.map(e => `
        <button class="apt-employee ${state.selectedEmployee?.id === e.id ? 'selected' : ''}" data-id="${e.id}">
            <span>${e.number}号</span><strong>${escapeHtml(e.name)}</strong>
        </button>`).join('');
    list.querySelectorAll('.apt-employee').forEach(btn => {
        btn.addEventListener('click', () => selectAppointmentEmployee(btn.dataset.id));
    });
}

function selectAppointmentEmployee(employeeId) {
    const state = appState.appointment;
    state.selectedEmployee = state.employees.find(e => e.id === employeeId);
    state.selectedSlot = null;
    renderAppointmentEmployees();
    renderAppointmentSlots();
    const slots = getAvailableSlotsForEmployee(employeeId).slice(0, 5);
    const text = slots.length
        ? `${state.selectedEmployee.name}今天可以预约：${slots.map(s => formatSlotText(s.start)).join('、')}。您想约哪个时间？`
        : `${state.selectedEmployee.name}今天暂时没有可预约时间，请选择其他技师。`;
    setAppointmentAiText(text, true);
    updateAppointmentConfirm();
}

function getAvailableSlotsForEmployee(employeeId) {
    return (appState.appointment?.availability?.slots || [])
        .filter(s => s.employeeId === employeeId && s.available);
}

function renderAppointmentSlots() {
    const state = appState.appointment;
    const box = document.getElementById('aptSlots');
    if (!state.selectedEmployee) {
        box.innerHTML = '<div class="apt-muted">请先选择技师</div>';
        return;
    }
    const slots = getAvailableSlotsForEmployee(state.selectedEmployee.id);
    if (slots.length === 0) {
        box.innerHTML = '<div class="apt-muted">该技师今天暂无空闲，请选择其他技师</div>';
        return;
    }
    box.innerHTML = slots.map(s => `
        <button class="apt-slot ${state.selectedSlot?.start === s.start ? 'selected' : ''}" data-start="${s.start}" data-end="${s.end}">
            ${formatSlotText(s.start)}<small>${s.start}-${s.end}</small>
        </button>`).join('');
    box.querySelectorAll('.apt-slot').forEach(btn => {
        btn.addEventListener('click', () => {
            state.selectedSlot = { start: btn.dataset.start, end: btn.dataset.end };
            renderAppointmentSlots();
            updateAppointmentConfirm();
            setAppointmentAiText(`好的，我帮您确认一下：${state.selectedEmployee.name}，${formatDateZh(state.date)}${formatSlotText(state.selectedSlot.start)}。请直接说或输入手机号，我帮您查询项目后确认预约。`, true);
        });
    });
}

async function lookupAppointmentProductsFromInput() {
    const phone = (document.getElementById('aptPhone')?.value || '').replace(/\D/g, '');
    if (!phone || phone.length < 7) {
        alert('请先输入手机号');
        return;
    }
    await lookupAppointmentProducts(phone);
}

async function lookupAppointmentProducts(phone) {
    const state = appState.appointment;
    if (!state || state._lastLookupPhone === phone) return;
    state._lastLookupPhone = phone;
    const box = document.getElementById('aptProducts');
    const memberInfo = document.getElementById('aptMemberInfo');
    box.innerHTML = '<div class="apt-muted">正在查询您的项目...</div>';
    const result = await FeedbackAPI.getAppointmentMemberProducts(state.store.storeCode, phone);
    if (!result.success) {
        state.member = null;
        state.products = [];
        state.selectedProduct = null;
        memberInfo.style.display = 'none';
        box.innerHTML = `<div class="apt-muted">${result.message || '未查询到项目'}</div>`;
        setAppointmentAiText(result.message || '未查询到您的项目，请联系门店确认。', true);
        updateAppointmentConfirm();
        return;
    }
    state.member = result.data.member;
    state.products = result.data.products || [];
    state.selectedProduct = null;
    memberInfo.style.display = 'block';
    memberInfo.textContent = `已识别客户：${state.member?.name || '顾客'}（${phone}）`;
    renderAppointmentProducts();
    const productNames = state.products.map(p => p.productName).join('、');
    setAppointmentAiText(state.products.length ? `查到了您的项目：${productNames}。请选择本次要预约的项目。` : '已找到客户档案，但暂无可预约项目，请联系门店确认。', true);
    updateAppointmentConfirm();
}

function renderAppointmentProducts() {
    const state = appState.appointment;
    const box = document.getElementById('aptProducts');
    if (!state.products.length) {
        box.innerHTML = '<div class="apt-muted">暂无可预约项目</div>';
        return;
    }
    box.innerHTML = state.products.map(p => `
        <button class="apt-product ${state.selectedProduct?.id === p.id ? 'selected' : ''}" data-id="${p.id}">
            <strong>${escapeHtml(p.productName || '项目')}</strong>
            <span>剩余 ${p.balanceCount ?? 0} 次 · ${p.durationMinutes || 60} 分钟</span>
            ${p.validEnd ? `<small>有效期至 ${p.validEnd}</small>` : ''}
        </button>`).join('');
    box.querySelectorAll('.apt-product').forEach(btn => {
        btn.addEventListener('click', () => {
            state.selectedProduct = state.products.find(p => p.id === btn.dataset.id);
            state.durationMinutes = state.selectedProduct?.durationMinutes || state.durationMinutes || 60;
            renderAppointmentProducts();
            updateAppointmentConfirm();
            setAppointmentAiText(`已选择${state.selectedProduct.productName}。请确认技师、时间和项目无误后提交预约。`, true);
        });
    });
}

async function lookupMyAppointments(phone) {
    const state = appState.appointment;
    if (!state) return;
    const box = document.getElementById('aptExistingAppointments');
    box.style.display = 'grid';
    box.innerHTML = '<div class="apt-muted">正在查询您的预约...</div>';
    const result = await FeedbackAPI.getMyAppointments(state.store.storeCode, phone);
    if (!result.success) {
        state.myAppointments = [];
        state.selectedExistingAppointment = null;
        box.innerHTML = `<div class="apt-muted">${result.message || '未查询到预约'}</div>`;
        setAppointmentAiText(result.message || '未查询到可操作的预约。', true);
        updateAppointmentConfirm();
        return;
    }
    state.member = result.data.member;
    state.myAppointments = result.data.appointments || [];
    state.selectedExistingAppointment = null;
    renderMyAppointments();
    setAppointmentAiText(state.myAppointments.length ? '已查到您的预约，请选择要操作的预约。' : '没有查到未完成的预约。', true);
    updateAppointmentConfirm();
}

function renderMyAppointments() {
    const state = appState.appointment;
    const box = document.getElementById('aptExistingAppointments');
    box.style.display = 'grid';
    if (!state.myAppointments.length) {
        box.innerHTML = '<div class="apt-muted">暂无未完成预约</div>';
        return;
    }
    box.innerHTML = state.myAppointments.map(a => `
        <button class="apt-product ${state.selectedExistingAppointment?.id === a.id ? 'selected' : ''}" data-id="${a.id}">
            <strong>${escapeHtml(a.productName || '预约服务')}</strong>
            <span>${formatAppointmentDateTime(a.startAt)} · ${escapeHtml(employeeNameById(a.employeeId) || '技师')}</span>
            <small>状态：${a.status || 'pending'}</small>
        </button>`).join('');
    box.querySelectorAll('.apt-product').forEach(btn => {
        btn.addEventListener('click', () => {
            state.selectedExistingAppointment = state.myAppointments.find(a => a.id === btn.dataset.id);
            if (state.intent === 'reschedule' && state.selectedExistingAppointment?.employeeId) {
                state.selectedEmployee = state.employees.find(e => e.id === state.selectedExistingAppointment.employeeId) || state.selectedEmployee;
                renderAppointmentEmployees();
                renderAppointmentSlots();
            }
            renderMyAppointments();
            if (state.intent === 'cancel') {
                setAppointmentAiText('已选中预约。您说确认或点击确认按钮，我就帮您取消。', true);
            } else if (state.intent === 'reschedule') {
                setAppointmentAiText('已选中原预约。请重新选择技师和时间，然后确认改约。', true);
            }
            updateAppointmentConfirm();
        });
    });
}

function employeeNameById(id) {
    return appState.appointment?.employees?.find(e => e.id === id)?.name || '';
}

function updateAppointmentConfirm() {
    const state = appState.appointment;
    const text = document.getElementById('aptConfirmText');
    const btn = document.getElementById('aptSubmitBtn');
    if (state.intent === 'cancel') {
        if (!state.selectedExistingAppointment) {
            text.textContent = '请选择要取消的预约';
            btn.disabled = true;
            return;
        }
        text.textContent = `将取消：${formatAppointmentDateTime(state.selectedExistingAppointment.startAt)} · ${state.selectedExistingAppointment.productName || '预约服务'}`;
        btn.textContent = '确认取消预约';
        btn.disabled = false;
        return;
    }
    if (state.intent === 'reschedule') {
        if (!state.selectedExistingAppointment || !state.selectedEmployee || !state.selectedSlot) {
            text.textContent = '请选择原预约和新的技师/时间';
            btn.textContent = '确认改约';
            btn.disabled = true;
            return;
        }
        text.textContent = `将改约到：${state.selectedEmployee.name} · ${formatDateZh(state.date)} ${state.selectedSlot.start}`;
        btn.textContent = '确认改约';
        btn.disabled = false;
        return;
    }
    if (!state?.selectedEmployee || !state?.selectedSlot || !state?.selectedProduct) {
        text.textContent = '请选择技师、时间和项目';
        btn.textContent = '确认预约';
        btn.disabled = true;
        return;
    }
    text.textContent = `已选择：${state.selectedEmployee.name} · ${formatDateZh(state.date)} ${state.selectedSlot.start} · ${state.selectedProduct.productName}`;
    btn.textContent = '确认预约';
    btn.disabled = false;
}

async function submitAppointment() {
    const state = appState.appointment;
    const phone = (document.getElementById('aptPhone').value || '').replace(/\D/g, '');
    if (!state?.selectedEmployee || !state?.selectedSlot || !state?.selectedProduct) return;
    if (!phone || phone.length < 7) { alert('请填写有效手机号'); return; }

    const btn = document.getElementById('aptSubmitBtn');
    btn.disabled = true;

    if (state.intent === 'cancel') {
        btn.textContent = '正在取消...';
        const result = await FeedbackAPI.cancelAppointmentPublic({
            storeCode: state.store.storeCode,
            customerPhone: phone,
            appointmentId: state.selectedExistingAppointment?.id,
            reason: '客户H5取消',
        });
        if (result.success) {
            state.completed = true;
            stopAppointmentListening();
            btn.textContent = '已取消';
            setAppointmentAiText('好的，您的预约已取消。', true);
        } else {
            btn.disabled = false;
            btn.textContent = '确认取消预约';
            setAppointmentAiText(result.message || '取消失败，请稍后再试。', true);
        }
        return;
    }

    if (state.intent === 'reschedule') {
        btn.textContent = '正在实时确认新档期...';
        const startAt = `${state.date}T${state.selectedSlot.start}:00`;
        const result = await FeedbackAPI.rescheduleAppointmentPublic({
            storeCode: state.store.storeCode,
            customerPhone: phone,
            appointmentId: state.selectedExistingAppointment?.id,
            employeeId: state.selectedEmployee.id,
            startAt,
            durationMinutes: state.selectedExistingAppointment?.durationMinutes || state.durationMinutes,
            reason: '客户H5改约',
        });
        if (result.success) {
            state.completed = true;
            stopAppointmentListening();
            btn.textContent = '改约成功';
            setAppointmentAiText(`改约成功，新的时间是${formatDateZh(state.date)}${formatSlotText(state.selectedSlot.start)}。`, true);
        } else if (result.code === 409) {
            btn.disabled = false;
            btn.textContent = '确认改约';
            await refreshAppointmentAvailability();
            setAppointmentAiText('不好意思，新时间刚刚被预约了，请重新选择其他时间。', true);
        } else {
            btn.disabled = false;
            btn.textContent = '确认改约';
            setAppointmentAiText(result.message || '改约失败，请稍后再试。', true);
        }
        return;
    }

    btn.textContent = '正在实时确认档期...';
    setAppointmentAiText('好的，正在为您预约，请稍后。我会实时确认这个时间是否还没有被别人预定。', true);

    const startAt = `${state.date}T${state.selectedSlot.start}:00`;
    const result = await FeedbackAPI.bookAppointment({
        storeCode: state.store.storeCode,
        employeeId: state.selectedEmployee.id,
        startAt,
        durationMinutes: state.selectedProduct.durationMinutes || state.durationMinutes,
        customerName: state.member?.name || '',
        customerPhone: phone,
        memberProductId: state.selectedProduct.memberProductId,
        productId: state.selectedProduct.productId,
        serviceName: state.selectedProduct.productName || '预约服务',
        notes: '客户H5预约',
    });
    if (result.success) {
        state.completed = true;
        stopAppointmentListening();
        btn.textContent = '预约成功';
        setAppointmentAiText(`预约成功，已为您安排${state.selectedEmployee.name}，时间是${formatDateZh(state.date)}${formatSlotText(state.selectedSlot.start)}。请您按时到店。`, true);
        btn.disabled = true;
    } else if (result.code === 409) {
        btn.textContent = '确认预约';
        btn.disabled = false;
        await refreshAppointmentAvailability();
        setAppointmentAiText(`不好意思，刚刚这个时间已经被其他顾客预约了。请您重新选择其他时间。`, true);
    } else {
        btn.textContent = '确认预约';
        btn.disabled = false;
        setAppointmentAiText(result.message || '预约失败，请稍后再试', true);
    }
}

async function refreshAppointmentAvailability() {
    const state = appState.appointment;
    const result = await FeedbackAPI.getAppointmentAvailability(state.store.storeCode, state.date, null, state.durationMinutes);
    if (result.success) {
        state.availability = result.data;
        state.selectedSlot = null;
        renderAppointmentSlots();
        updateAppointmentConfirm();
    }
}

function stopAppointmentListening() {
    const state = appState.appointment;
    if (!state) return;
    try {
        if (state.recognition) state.recognition.stop();
    } catch (e) {}
    state.recognition = null;
    state.listening = false;
    const status = document.getElementById('aptListenStatus');
    if (status) status.textContent = '预约已完成，语音监听已关闭';
}

function startAppointmentAutoListen() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const status = document.getElementById('aptListenStatus');
    if (!SpeechRecognition) {
        if (status) status.textContent = '当前浏览器不支持自动语音识别，请手动输入手机号和选择项目';
        return;
    }
    const state = appState.appointment;
    if (!state || state.completed || state.listening) return;
    try {
        const rec = new SpeechRecognition();
        rec.lang = 'zh-CN';
        rec.interimResults = false;
        rec.continuous = false;
        state.recognition = rec;
        state.listening = true;
        if (status) status.textContent = '正在聆听... 可直接说手机号、技师或时间';
        rec.onresult = e => {
            const text = Array.from(e.results).map(r => r[0]?.transcript || '').join('');
            handleAppointmentUtterance(text);
        };
        rec.onerror = e => {
            if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                showVoiceUnlockHint('请点一下按钮并允许麦克风权限');
            } else {
                if (status) status.textContent = '环境较嘈杂，我会继续听有效信息';
            }
        };
        rec.onend = () => {
            state.listening = false;
            if (state.completed) {
                if (status) status.textContent = '预约已完成，语音监听已关闭';
                return;
            }
            if (status) status.textContent = '继续聆听中...';
            if (window.location.hash.includes('/appointment')) {
                setTimeout(startAppointmentAutoListen, 500);
            }
        };
        rec.start();
    } catch (e) {
        state.listening = false;
        showVoiceUnlockHint('请点一下按钮开始语音预约');
    }
}

function enterAppointmentAction(intent) {
    const state = appState.appointment;
    if (!state) return;
    state.intent = intent;
    state.selectedExistingAppointment = null;
    document.getElementById('aptProducts').innerHTML = '<div class="apt-muted">取消/改约无需选择项目，请先说手机号查询预约</div>';
    document.getElementById('aptExistingAppointments').style.display = 'grid';
    document.getElementById('aptExistingAppointments').innerHTML = '<div class="apt-muted">请直接说或输入手机号，我帮您查询未完成预约</div>';
    setAppointmentAiText(intent === 'cancel' ? '好的，我来帮您取消预约。请直接说您的手机号。' : '好的，我来帮您改约时间。请直接说您的手机号。', true);
    updateAppointmentConfirm();
}

function handleAppointmentUtterance(text) {
    const state = appState.appointment;
    if (!state) return;
    text = normalizeSpeechText(text);
    if (!text) return;
    const wantsCancel = /不能参加|不参加|不去了|取消|取消预约|来不了|不能去了/.test(text);
    const wantsReschedule = /改约|改时间|换时间|改到|换到|重新约/.test(text);
    if (wantsCancel) enterAppointmentAction('cancel');
    if (wantsReschedule) enterAppointmentAction('reschedule');
    const phone = matchPhone(text);
    const emp = matchAppointmentEmployee(text);
    const product = matchAppointmentProduct(text);
    const slot = matchAppointmentSlot(text);
    const confirmed = /确认|对的|可以|就这个|没问题|好的|好/.test(text);
    if (!phone && !emp && !product && !slot && !confirmed && !wantsCancel && !wantsReschedule) {
        const status = document.getElementById('aptListenStatus');
        if (status) status.textContent = '环境较嘈杂，已忽略无关声音，继续聆听...';
        return;
    }
    setAppointmentAiText(`您说：${text}`, false);
    if (phone) {
        const input = document.getElementById('aptPhone');
        if (input) input.value = phone;
        if (state.intent === 'cancel' || state.intent === 'reschedule') {
            lookupMyAppointments(phone);
        } else {
            lookupAppointmentProducts(phone);
        }
    }
    if (emp) {
        selectAppointmentEmployee(emp.id);
    }
    if (product) {
        appState.appointment.selectedProduct = product;
        appState.appointment.durationMinutes = product.durationMinutes || appState.appointment.durationMinutes || 60;
        renderAppointmentProducts();
        updateAppointmentConfirm();
        setAppointmentAiText(`已选择${product.productName}。`, true);
    }
    if (slot && state.selectedEmployee) {
        state.selectedSlot = slot;
        renderAppointmentSlots();
        updateAppointmentConfirm();
        setAppointmentAiText(`好的，我帮您确认：${state.selectedEmployee.name}，${formatDateZh(state.date)}${formatSlotText(slot.start)}。请直接说您的手机号，我帮您查询可预约项目。`, true);
        return;
    }
    if (confirmed && state.selectedEmployee && state.selectedSlot && state.selectedProduct) {
        submitAppointment();
        return;
    }
    if (!state.selectedEmployee) {
        setAppointmentAiText('请告诉我想预约哪位技师，比如说：我要约2号技师。', true);
    } else if (!state.selectedSlot) {
        setAppointmentAiText('请告诉我想约几点，比如说：下午3点。', true);
    } else if (!state.member) {
        setAppointmentAiText('请直接说您的手机号，我帮您查询可预约项目。', true);
    } else if (!state.selectedProduct) {
        setAppointmentAiText('请从卡片中选择本次要预约的项目，或直接说项目名称。', true);
    }
}

function normalizeSpeechText(text) {
    return String(text || '')
        .replace(/幺/g, '一')
        .replace(/零/g, '0')
        .replace(/〇/g, '0')
        .replace(/一/g, '1')
        .replace(/二/g, '2')
        .replace(/两/g, '2')
        .replace(/三/g, '3')
        .replace(/四/g, '4')
        .replace(/五/g, '5')
        .replace(/六/g, '6')
        .replace(/七/g, '7')
        .replace(/八/g, '8')
        .replace(/九/g, '9')
        .replace(/十1/g, '11')
        .replace(/十2/g, '12')
        .replace(/十/g, '10')
        .trim();
}

function matchPhone(text) {
    const normalized = normalizeSpeechText(text).replace(/[，,。\s\-]/g, '');
    const full = normalized.match(/1\d{10}/);
    if (full) return full[0];
    const digits = normalized.replace(/\D/g, '');
    return digits.length >= 7 ? digits : '';
}

function matchAppointmentProduct(text) {
    const state = appState.appointment;
    if (!state?.products?.length) return null;
    return state.products.find(p => text.includes(p.productName)) || null;
}

function matchAppointmentEmployee(text) {
    const state = appState.appointment;
    if (!state) return null;
    for (const e of state.employees) {
        if (text.includes(e.name) || text.includes(`${e.number}号`) || text.includes(`${e.number} 号`)) return e;
    }
    return null;
}

function matchAppointmentSlot(text) {
    const state = appState.appointment;
    if (!state?.selectedEmployee) return null;
    const slots = getAvailableSlotsForEmployee(state.selectedEmployee.id);
    const hourMatch = text.match(/(\d{1,2}|一|二|两|三|四|五|六|七|八|九|十|十一|十二)点/);
    if (!hourMatch) return null;
    const hour = chineseHourToNumber(hourMatch[1]);
    const isPm = /下午|晚上/.test(text) || (hour >= 1 && hour <= 8 && !/上午|早上/.test(text));
    const h24 = isPm && hour < 12 ? hour + 12 : hour;
    const minute = /半/.test(text) ? '30' : '00';
    const target = `${String(h24).padStart(2, '0')}:${minute}`;
    return slots.find(s => s.start === target) || slots.find(s => s.start.startsWith(String(h24).padStart(2, '0')));
}

function chineseHourToNumber(v) {
    const map = { '一':1, '二':2, '两':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10, '十一':11, '十二':12 };
    return map[v] || parseInt(v, 10);
}

function setAppointmentAiText(text, shouldSpeak = false) {
    const el = document.getElementById('aptAiText');
    if (el) el.textContent = text;
    if (shouldSpeak) appointmentSpeak(text);
}

function formatAppointmentDateTime(value) {
    if (!value) return '-';
    const s = String(value).replace('T', ' ');
    return `${s.slice(0, 10)} ${s.slice(11, 16)}`;
}

function formatSlotText(time) {
    const [h, m] = time.split(':').map(Number);
    const prefix = h < 12 ? '上午' : h < 18 ? '下午' : '晚上';
    const hour = h > 12 ? h - 12 : h;
    return `${prefix}${hour}点${m === 30 ? '半' : ''}`;
}

function formatDateZh(date) {
    const today = todayISO();
    return date === today ? '今天' : date;
}

// ==================== 首页 ====================
async function renderHome(container) {
    // 返回首页时清理 WebSocket 和音频资源
    if (appState.ws) {
        try { appState.ws.close(); } catch (e) {}
        appState.ws = null;
    }
    if (appState.audioRecorder?.isRecording) {
        try { appState.audioRecorder.stop(); } catch (e) {}
    }
    appState.chatMessages = [];
    appState.customerName = '';
    appState.phoneTail = '';
    appState.customerIdentity = null;
    appState.sessionId = '';
    appState._otaResult = null;

    container.innerHTML = `
    <div class="page home-page">
        <div class="page-header">
            <h1>🎯 服务反馈</h1>
            <p class="subtitle">您的声音，我们用心倾听</p>
        </div>
        <div class="store-input-section" id="storeInputSection">
            <label>请输入服务码</label>
            <div class="code-input-group">
                <input type="text" id="storeCodeInput" placeholder="6位服务码" maxlength="6" value="${appState.storeCode}" inputmode="numeric">
                <button id="queryStoreBtn" class="btn-primary">查询</button>
            </div>
        </div>
        <div id="storeInfoSection" class="store-info-section" style="display:none">
            <div class="store-card">
                <h2 id="storeNameDisplay"></h2>
                <span class="store-code" id="storeCodeDisplay"></span>
            </div>
            <div class="employee-section">
                <h3>请选择服务人员</h3>
                <div id="employeeList" class="employee-list"></div>
            </div>
            <button id="startFeedbackBtn" class="btn-start" disabled>开始语音反馈</button>
        </div>
        <div id="errorMessage" class="error-message" style="display:none"></div>
    </div>`;

    document.getElementById('queryStoreBtn').addEventListener('click', queryStore);
    document.getElementById('storeCodeInput').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') queryStore();
    });
    document.getElementById('startFeedbackBtn').addEventListener('click', startFeedback);

    // 如果 URL 带了 code 参数，自动查询并隐藏输入框（用户体验：扫码进入即直奔员工选择）
    if (appState.storeCode) {
        document.getElementById('storeCodeInput').value = appState.storeCode;
        appState._codeFromUrl = true;
        queryStore();
    } else {
        appState._codeFromUrl = false;
    }
}

async function queryStore() {
    const codeInput = document.getElementById('storeCodeInput');
    const code = codeInput.value.trim();
    if (!code) return;

    const errEl = document.getElementById('errorMessage');
    errEl.style.display = 'none';

    const result = await FeedbackAPI.getStoreByCode(code);
    if (!result.success) {
        errEl.textContent = result.message;
        errEl.style.display = 'block';
        document.getElementById('storeInfoSection').style.display = 'none';
        return;
    }

    appState.storeInfo = result.data;
    appState.storeCode = code;

    if (!result.data.agentId) {
        errEl.textContent = '门店配置中，请稍后再试';
        errEl.style.display = 'block';
        document.getElementById('storeInfoSection').style.display = 'none';
        return;
    }

    document.getElementById('storeNameDisplay').textContent = result.data.storeName;
    document.getElementById('storeCodeDisplay').textContent = `服务码: ${result.data.storeCode}`;
    document.getElementById('storeInfoSection').style.display = 'block';

    // 如果服务码是从 URL 参数带进来的，查询成功后直接隐藏输入框（扫码场景免输入）
    if (appState._codeFromUrl) {
        const inputSection = document.getElementById('storeInputSection');
        if (inputSection) inputSection.style.display = 'none';
    }

    // 【预加载】门店查询成功后立即后台预热 Live2D 资源（不等用户选员工）
    // 这样用户在选员工的几秒内，4MB 的模型文件已经下载完了
    preloadVoicePageResources();

    const empResult = await FeedbackAPI.getEmployees(result.data.id);
    if (empResult.success) {
        appState.employees = empResult.data || [];
        renderEmployeeList();
    }
}

function renderEmployeeList() {
    const list = document.getElementById('employeeList');
    list.innerHTML = appState.employees.map(emp => {
        const typeLabel = getEmployeeTypeLabel(emp.employeeType);
        return `
        <div class="employee-card" data-emp-id="${emp.id}">
            <span class="emp-number">${emp.number}号</span>
            <span class="emp-name">${emp.name}</span>
            ${typeLabel ? `<span class="emp-type type-${emp.employeeType}">${typeLabel}</span>` : ''}
        </div>`;
    }).join('');

    list.querySelectorAll('.employee-card').forEach(card => {
        card.addEventListener('click', () => {
            list.querySelectorAll('.employee-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            const empId = card.dataset.empId;
            appState.selectedEmployee = appState.employees.find(e => e.id === empId);
            document.getElementById('startFeedbackBtn').disabled = false;

            // 【预加载】用户选完员工后，后台静默预热 Live2D 资源 + 音频上下文
            // 等用户点击"开始语音反馈"时，文件已经在浏览器缓存里了
            preloadVoicePageResources();
        });
    });
}

// 预加载语音页所需资源（在 home 页静默执行）
let _preloadStarted = false;
async function preloadVoicePageResources() {
    if (_preloadStarted) return;
    _preloadStarted = true;
    console.log('[preload] 开始预加载语音页资源...');

    const modelName = localStorage.getItem('live2dModel') || 'hiyori_pro_zh';
    const modelFileMap = {
        'hiyori_pro_zh': 'hiyori_pro_t11',
        'natori_pro_zh': 'natori_pro_t06',
    };
    const fileBase = modelFileMap[modelName] || 'hiyori_pro_t11';
    const basePath = `resources/${modelName}/runtime/${fileBase}`;

    // 预加载模型相关文件（让浏览器缓存住）
    const filesToPreload = [
        `${basePath}.model3.json`,
        `${basePath}.moc3`,
        `${basePath}.physics3.json`,
        `${basePath}.cdi3.json`,
        `${basePath}.2048/texture_00.png`,
        `${basePath}.2048/texture_01.png`,
    ];

    // 用 fetch 预加载（结果会进 HTTP 缓存，PIXI.Live2D 后续加载会命中缓存）
    const t0 = performance.now();
    await Promise.all(filesToPreload.map(url =>
        fetch(url, { cache: 'force-cache' })
            .then(r => r.blob())
            .catch(e => console.warn(`[preload] ${url} 失败:`, e.message))
    ));
    console.log(`[preload] Live2D 资源预加载完成，耗时 ${Math.round(performance.now() - t0)}ms`);

    // 预初始化音频上下文（消除浏览器策略导致的首次启动延迟）
    try {
        const { getAudioPlayer } = await import('./audio-player.js');
        const player = getAudioPlayer();
        player.start();
        console.log('[preload] 音频播放器已预热');
    } catch (e) {
        console.warn('[preload] 音频预热失败:', e.message);
    }
}

async function startFeedback() {
    if (!appState.storeInfo || !appState.selectedEmployee) return;

    const btn = document.getElementById('startFeedbackBtn');
    btn.textContent = '准备中...';
    btn.disabled = true;

    // 检查麦克风
    const micOk = await checkMicrophoneAvailability();
    if (!micOk) {
        btn.textContent = '开始语音反馈';
        btn.disabled = false;
        alert('无法访问麦克风，请允许麦克风权限后重试');
        return;
    }

    const initResult = await FeedbackAPI.deviceInit(
        appState.storeInfo.id,
        appState.selectedEmployee.id
    );

    if (!initResult.success) {
        btn.textContent = '开始语音反馈';
        btn.disabled = false;
        alert(initResult.message || '设备初始化失败');
        return;
    }

    appState.deviceMac = initResult.data.deviceMac;
    appState._deviceInitResult = initResult.data;

    // 检查 device_init 返回的 OTA 结果
    const otaResult = initResult.data.otaResult;
    console.log('[startFeedback] deviceInit 返回 otaResult:', otaResult ? '有' : '无',
        otaResult ? `activation=${!!otaResult.activation} websocket=${!!otaResult.websocket?.url}` : '');

    if (otaResult && otaResult.activation && otaResult.activation.code) {
        // 设备未绑定 → 显示激活码，等待管理员绑定
        appState._otaResult = otaResult;
        showActivationCode(otaResult.activation.code, otaResult.websocket, btn, initResult.data.agentId);
        return;
    }

    if (otaResult && otaResult.websocket && otaResult.websocket.url) {
        // 设备已绑定 → 直接连接
        appState._otaResult = otaResult;
        navigate('voice');
        return;
    }

    // OTA 未返回有效结果（Java 可能未运行），需要在语音页重新获取
    appState._otaResult = null;
    console.warn('[startFeedback] device-init 未获取到 OTA 结果，将在语音页重试');
    navigate('voice');
}

// 显示激活码弹窗
function showActivationCode(code, wsInfo, startBtn, agentId) {
    // 生成带 agentId 的管理后台链接，方便管理员直接跳转
    const adminUrl = agentId
        ? `http://localhost:8002/#/device-management?agentId=${agentId}`
        : 'http://localhost:8002';

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card activation-modal">
        <h2>🔑 设备激活</h2>
        <p class="modal-subtitle">请管理员在智控台输入以下验证码完成绑定</p>
        <div class="activation-code-display">${code}</div>
        <div class="activation-hint">
            <p>📋 操作步骤：</p>
            <ol>
                <li>点击打开 <a href="${adminUrl}" target="_blank">管理后台</a></li>
                <li>在「设备管理」页面输入验证码 <strong>${code}</strong></li>
                <li>绑定完成后点击下方按钮</li>
            </ol>
        </div>
        <button class="btn-primary btn-large" id="retryConnectBtn">✅ 已绑定，开始对话</button>
        <button class="modal-cancel-btn" id="activationCancelBtn">取消</button>
    </div>`;
    document.body.appendChild(overlay);

    document.getElementById('retryConnectBtn').addEventListener('click', async () => {
        document.body.removeChild(overlay);
        const btn2 = document.getElementById('startFeedbackBtn');
        if (btn2) {
            btn2.textContent = '连接中...';
            btn2.disabled = true;
        }

        // 重新调用 OTA 检查绑定状态
        const otaResult = await FeedbackAPI.connectOTA(appState.deviceMac, 'feedback_client');
        if (otaResult && otaResult.websocket && otaResult.websocket.url) {
            // 绑定成功！
            appState._otaResult = otaResult;
            navigate('voice');
        } else if (otaResult && otaResult.activation && otaResult.activation.code) {
            // 仍然未绑定，重新显示激活码
            showActivationCode(otaResult.activation.code, otaResult.websocket, btn2, agentId);
        } else {
            alert('连接失败，请检查管理后台是否正常运行');
            if (btn2) {
                btn2.textContent = '开始语音反馈';
                btn2.disabled = false;
            }
        }
    });

    document.getElementById('activationCancelBtn').addEventListener('click', () => {
        document.body.removeChild(overlay);
        startBtn.textContent = '开始语音反馈';
        startBtn.disabled = false;
    });
}

// ==================== 语音对话页 ====================
function renderVoice(container) {
    // 安全检查：必须先有门店信息和设备MAC（防止直接访问 #/voice URL）
    if (!appState.storeInfo || !appState.deviceMac) {
        console.warn('[renderVoice] 缺少必要状态，返回首页');
        navigate('home');
        return;
    }

    // 清理之前的 Live2D 实例，防止 WebGL 上下文累积
    if (appState.live2dManager) {
        try {
            appState.live2dManager.destroy();
        } catch (e) { /* 忽略清理异常 */ }
        appState.live2dManager = null;
    }

    container.innerHTML = `
    <div class="voice-fullscreen">
        <!-- 准备页（覆盖在最上层，AI 准备就绪后淡出） -->
        <div id="prepareOverlay" class="prepare-overlay">
            <div class="prepare-card">
                <div class="prepare-emoji">✨</div>
                <h2 class="prepare-title">智能助手准备中</h2>
                <p class="prepare-subtitle">请稍候，马上为您开启对话</p>

                <div class="prepare-progress">
                    <div class="prepare-progress-bar" id="prepareProgressBar"></div>
                </div>
                <div class="prepare-percent" id="preparePercent">0%</div>

                <div class="prepare-steps">
                    <div class="prepare-step" id="step-live2d">
                        <span class="step-icon">⏳</span>
                        <span class="step-text">加载数字人形象</span>
                    </div>
                    <div class="prepare-step" id="step-ws">
                        <span class="step-icon">⏳</span>
                        <span class="step-text">建立语音通道</span>
                    </div>
                    <div class="prepare-step" id="step-ai">
                        <span class="step-icon">⏳</span>
                        <span class="step-text">AI 准备开口</span>
                    </div>
                </div>

                <p class="prepare-tip">💡 即将开始与您的服务体验对话</p>
            </div>
        </div>

        <!-- Live2D 全屏背景 -->
        <canvas id="live2d-stage" class="live2d-fullscreen"></canvas>

        <!-- 顶部状态栏（叠加在数字人上方） -->
        <div class="voice-status-overlay">
            <span id="voiceStatus" class="voice-status-text">连接中...</span>
        </div>

        <!-- 中下部：聊天弹幕（叠加在数字人上） -->
        <div id="chatStream" class="chat-stream-overlay"></div>

        <!-- 底部控制（叠加在数字人上） -->
        <div class="voice-controls-overlay">
            <button id="muteBtn" class="ctrl-btn-round mute-btn" disabled title="静音">
                <span class="ctrl-icon">🎤</span>
            </button>
            <button id="endCallBtn" class="ctrl-btn-main primary-end" disabled>
                <span>✅ 结束反馈</span>
            </button>
        </div>
    </div>`;

    // 重置准备状态
    appState._prepareState = {
        live2dReady: false,
        wsReady: false,
        aiReady: false,
        dismissed: false,
    };

    // 兜底：30 秒后无论如何强制淡出准备页（防止 AI 长时间不响应卡住）
    // 注意：如果 WS 连接失败，showPrepareError 会先把准备页变成错误诊断页
    setTimeout(() => {
        if (appState._prepareState && !appState._prepareState.dismissed) {
            // 如果 WS 都没通，已经被错误诊断接管，不淡出
            if (!appState._prepareState.wsReady) {
                console.warn('[prepareOverlay] 30秒超时但 WS 未就绪，保留页面让用户看错误');
                return;
            }
            console.warn('[prepareOverlay] 30秒兜底超时，强制淡出准备页');
            dismissPrepareOverlay();
        }
    }, 30000);

    initLive2D();
    connectVoice();
}

// 更新准备进度
function updatePrepareProgress() {
    const state = appState._prepareState;
    if (!state || state.dismissed) return;

    const steps = [
        { key: 'live2dReady', id: 'step-live2d' },
        { key: 'wsReady', id: 'step-ws' },
        { key: 'aiReady', id: 'step-ai' },
    ];
    let completed = 0;
    steps.forEach(s => {
        const el = document.getElementById(s.id);
        if (!el) return;
        const icon = el.querySelector('.step-icon');
        if (state[s.key]) {
            completed++;
            el.classList.add('done');
            if (icon) icon.textContent = '✅';
        }
    });

    const percent = Math.round((completed / steps.length) * 100);
    const bar = document.getElementById('prepareProgressBar');
    const pct = document.getElementById('preparePercent');
    if (bar) bar.style.width = percent + '%';
    if (pct) pct.textContent = percent + '%';

    // 全部就绪 → 淡出准备页
    if (state.live2dReady && state.wsReady && state.aiReady) {
        dismissPrepareOverlay();
    }
}

// 淡出准备页
function dismissPrepareOverlay() {
    const state = appState._prepareState;
    if (!state || state.dismissed) return;
    state.dismissed = true;

    const overlay = document.getElementById('prepareOverlay');
    if (overlay) {
        overlay.classList.add('fading-out');
        setTimeout(() => {
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        }, 500);
    }
}

// 在准备页上显示连接错误诊断（不淡出）
function showPrepareError(code, reason) {
    const state = appState._prepareState;
    if (!state || state.dismissed) return;

    const overlay = document.getElementById('prepareOverlay');
    if (!overlay) return;

    // 1006: TLS/连接异常关闭（多半是 Nginx WS 没配 Upgrade 头）
    // 1011: 服务端内部错误
    // 1015: TLS 失败
    let errorTitle = '连接失败';
    let errorReason = '';
    let errorTip = '';

    if (code === 1006) {
        errorTitle = '语音通道无法建立';
        errorReason = '后端 WebSocket 连接被中断（code 1006）';
        errorTip = '可能原因：\n• 反向代理（Nginx/FRP）未配置 WebSocket 升级头\n• xiaozhi-server 未运行或不可达\n• 域名 SSL 证书问题\n请联系管理员检查 Nginx 配置';
    } else if (code === 1011) {
        errorTitle = '服务端错误';
        errorReason = `服务端拒绝连接 (code ${code}): ${reason || '未知原因'}`;
        errorTip = '请稍后重试，或联系管理员';
    } else if (code === 1015) {
        errorTitle = 'TLS 握手失败';
        errorReason = `加密连接建立失败 (code ${code})`;
        errorTip = '请检查域名 SSL 证书是否有效';
    } else {
        errorReason = `连接关闭 (code ${code})${reason ? ': ' + reason : ''}`;
        errorTip = '请检查网络连接后重试';
    }

    overlay.innerHTML = `
    <div class="prepare-card prepare-error">
        <div class="prepare-emoji">⚠️</div>
        <h2 class="prepare-title">${errorTitle}</h2>
        <p class="prepare-error-reason">${errorReason}</p>
        <div class="prepare-error-tip">${errorTip.replace(/\n/g, '<br>')}</div>
        <div class="prepare-error-actions">
            <button class="btn-primary btn-large" onclick="location.reload()">🔄 重新尝试</button>
            <button class="modal-cancel-btn" onclick="location.hash='#/home'">返回首页</button>
        </div>
    </div>`;
}

async function initLive2D() {
    try {
        if (typeof Live2DManager === 'undefined') {
            console.warn('Live2DManager未加载');
            return;
        }
        const manager = new Live2DManager();
        await manager.initializeLive2D();
        appState.live2dManager = manager;
        // 让Live2D可以访问到
        if (window.chatApp) {
            window.chatApp.live2dManager = manager;
        }
        // 标记 Live2D 加载完成，更新准备进度
        if (appState._prepareState) {
            appState._prepareState.live2dReady = true;
            updatePrepareProgress();
        }
    } catch (e) {
        console.error('Live2D初始化失败:', e);
        // 即使 Live2D 加载失败，也标记完成（不要卡住进度条）
        if (appState._prepareState) {
            appState._prepareState.live2dReady = true;
            updatePrepareProgress();
        }
    }
}

async function connectVoice() {
    const statusEl = document.getElementById('voiceStatus');
    const muteBtn = document.getElementById('muteBtn');
    const endCallBtn = document.getElementById('endCallBtn');
    appState.chatMessages = [];
    appState._autoEndTriggered = false;

    statusEl.textContent = '正在连接...';

    // 启动音频播放系统
    appState.audioPlayer = getAudioPlayer();
    appState.audioPlayer.start();

    // 初始化录音器
    appState.audioRecorder = getAudioRecorder();

    // 优先使用 device_init 返回的 OTA 结果，避免重复请求
    let otaResult = appState._otaResult;
    console.log('[connectVoice] 使用缓存的 OTA 结果:', otaResult ? '有' : '无');
    if (!otaResult || !otaResult.websocket || !otaResult.websocket.url) {
        // 通过 feedback-backend 代理调用 OTA（避免 CORS）
        console.log('[connectVoice] 重新调用 OTA 代理...');
        otaResult = await FeedbackAPI.connectOTA(appState.deviceMac, 'feedback_client');
        console.log('[connectVoice] OTA 代理返回:', otaResult ? JSON.stringify(otaResult).substring(0, 200) : 'null');
    }

    if (!otaResult || !otaResult.websocket || !otaResult.websocket.url) {
        statusEl.textContent = '连接失败，请重试';
        console.error('[connectVoice] 无法获取 WebSocket URL');
        return;
    }

    // 未绑定，显示验证码（兜底：正常流程已在 startFeedback 中处理）
    if (otaResult.activation && otaResult.activation.code) {
        statusEl.innerHTML = `<div style="text-align:center">
            <div style="font-size:14px;color:#666">请管理员在智控台输入以下验证码绑定智能体：</div>
            <div style="font-size:36px;color:#4CAF50;font-weight:bold;margin:10px 0">${otaResult.activation.code}</div>
            <button onclick="location.reload()" style="padding:8px 16px;background:#4CAF50;color:#fff;border:none;border-radius:6px;cursor:pointer">绑定后点这里重试</button>
        </div>`;
        return;
    }

    appState.otaResult = otaResult;
    statusEl.textContent = '正在连接语音服务...';

    // 构建 WebSocket URL
    // OTA 返回的 URL 通常是 ws://127.0.0.1:18000/...（内部地址）
    // 如果当前页面是通过外网域名访问的，需要替换为 wss://域名/ws/（走 FRP 隧道）
    let wsUrlStr = otaResult.websocket.url;
    const isExternalAccess = !['127.0.0.1', 'localhost', '0.0.0.0'].includes(window.location.hostname);
    const isLocalWsUrl = wsUrlStr.includes('127.0.0.1') || wsUrlStr.includes('localhost');

    if (isExternalAccess && isLocalWsUrl) {
        // 外网访问 + OTA 返回内部地址 → 改用同源 WebSocket（需要 FRP/Nginx 配置 /ws/ 路径）
        wsUrlStr = WS_BASE + '/';
        console.log('[connectVoice] 外网模式，使用同源 WS:', wsUrlStr);
    }

    let wsUrl = new URL(wsUrlStr);
    if (otaResult.websocket.token) {
        wsUrl.searchParams.append('authorization', 'Bearer ' + otaResult.websocket.token);
    }
    // 同时通过 URL 参数传递 device-id 和 client-id（WebSocket 协议要求）
    wsUrl.searchParams.append('device-id', appState.deviceMac);
    wsUrl.searchParams.append('client-id', 'feedback_client');

    const finalWsUrl = wsUrl.toString();
    console.log('[connectVoice] WebSocket URL:', finalWsUrl);

    try {
        const ws = new WebSocket(finalWsUrl);
        ws.binaryType = 'arraybuffer';
        appState.ws = ws;
        appState.audioRecorder.setWebSocket(ws);

        ws.onopen = () => {
            console.log('[connectVoice] WebSocket 已连接');
            statusEl.textContent = '已连接';
            ws.send(JSON.stringify({
                type: 'hello',
                device_id: appState.deviceMac,
                device_name: appState.storeInfo?.storeName || '反馈H5',
                device_mac: appState.deviceMac,
                token: otaResult.websocket?.token,
                features: { mcp: false, emoji: false }
            }));
        };

        ws.onmessage = async (event) => {
            if (typeof event.data === 'string') {
                try {
                    const msg = JSON.parse(event.data);
                    console.log('[connectVoice] WS 收到文本消息:', msg.type, msg.text || '');
                    handleWSTextMessage(msg);
                } catch (e) {
                    console.warn('非JSON消息:', event.data);
                }
            } else {
                const opusData = new Uint8Array(event.data);
                appState.audioPlayer.enqueueAudioData(opusData);
            }
        };

        ws.onclose = (event) => {
            console.log('[connectVoice] WebSocket 关闭: code=', event.code, 'reason=', event.reason);
            // 如果还没建立过对话（没有 session_id），说明连接提前断了
            if (!appState.sessionId) {
                statusEl.textContent = `连接断开 (${event.code})，请重试`;
                console.error('[connectVoice] WebSocket 在建立对话前就关闭了');
                // 在准备页上显示明确的错误诊断
                showPrepareError(event.code, event.reason);
                return; // 不触发 processAfterConversation
            }
            statusEl.textContent = '对话已结束，正在生成结果...';
            muteBtn.disabled = true;
            endCallBtn.disabled = true;
            // 停止录音
            if (appState.audioRecorder?.isRecording) {
                appState.audioRecorder.stop();
            }
            // 触发AI处理（如果用户选了满意度，传过去；否则不传）
            const sat = appState._pendingSatisfaction || '';
            appState._pendingSatisfaction = '';
            setTimeout(() => processAfterConversation(sat), 500);
        };

        ws.onerror = (event) => {
            console.error('[connectVoice] WebSocket 错误:', event);
            statusEl.textContent = '连接错误，请检查网络';
        };

        // 静音按钮 - 切换是否发送音频
        let isMuted = false;
        muteBtn.addEventListener('click', () => {
            isMuted = !isMuted;
            if (isMuted) {
                // 暂停录音
                if (appState.audioRecorder?.isRecording) {
                    appState.audioRecorder.stop();
                }
                muteBtn.classList.add('muted');
                muteBtn.querySelector('.mute-icon').textContent = '🔇';
                muteBtn.querySelector('.mute-text').textContent = '已静音';
            } else {
                // 恢复录音
                startContinuousRecording();
                muteBtn.classList.remove('muted');
                muteBtn.querySelector('.mute-icon').textContent = '🎤';
                muteBtn.querySelector('.mute-text').textContent = '监听中';
            }
        });

        // 结束反馈按钮 - 弹出满意度选择
        endCallBtn.addEventListener('click', () => {
            showSatisfactionDialog();
        });

    } catch (e) {
        statusEl.textContent = '连接失败: ' + e.message;
    }
}

// 开始持续录音（自动模式 - 由服务端VAD自动判断说话边界）
async function startContinuousRecording() {
    if (!appState.ws || appState.ws.readyState !== WebSocket.OPEN) return;
    if (appState.audioRecorder?.isRecording) return;

    // 发送 listen start (auto模式 - 服务端VAD自动判断)
    appState.ws.send(JSON.stringify({
        session_id: appState.sessionId,
        type: 'listen',
        state: 'start',
        mode: 'auto'
    }));
    // 开始录音（持续发送音频流）
    await appState.audioRecorder.start();
}

function handleWSTextMessage(msg) {
    const statusEl = document.getElementById('voiceStatus');
    const chatStream = document.getElementById('chatStream');
    const muteBtn = document.getElementById('muteBtn');
    const endCallBtn = document.getElementById('endCallBtn');

    if (msg.type === 'hello' && msg.session_id) {
        appState.sessionId = msg.session_id;
        statusEl.textContent = '对话中（请直接说话）';
        if (muteBtn) muteBtn.disabled = false;
        if (endCallBtn) endCallBtn.disabled = false;

        // 标记 WebSocket 通道就绪（hello 握手完成）
        if (appState._prepareState) {
            appState._prepareState.wsReady = true;
            updatePrepareProgress();
        }

        // 触发AI开始第一个问题
        if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
            appState.ws.send(JSON.stringify({
                session_id: msg.session_id,
                type: 'listen',
                state: 'detect',
                text: '你好'
            }));
        }
        // 自动启动持续录音（auto模式 - 服务端VAD）
        setTimeout(() => startContinuousRecording(), 300);
    } else if (msg.type === 'stt' && msg.text) {
        addChatBubble(chatStream, msg.text, true);
        appState.chatMessages.push({ role: 'user', text: msg.text });
        updateCustomerIdentityFromText(msg.text);
    } else if (msg.type === 'llm' && msg.text) {
        const textWithoutEmoji = msg.text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim();
        if (textWithoutEmoji) {
            addChatBubble(chatStream, msg.text, false);
            appState.chatMessages.push({ role: 'ai', text: msg.text });
        }
    } else if (msg.type === 'tts') {
        if (msg.state === 'start') {
            statusEl.textContent = 'AI说话中...';
            appState.isRemoteSpeaking = true;
            // 【关键】AI 开始说第一句话 → 标记准备完成，淡出加载页
            if (appState._prepareState && !appState._prepareState.aiReady) {
                appState._prepareState.aiReady = true;
                updatePrepareProgress();
            }
            if (appState.live2dManager) {
                appState.live2dManager.startTalking?.();
            }
        } else if (msg.state === 'sentence_start' && msg.text) {
            const last = appState.chatMessages[appState.chatMessages.length - 1];
            if (!last || last.role !== 'ai' || last.text !== msg.text) {
                addChatBubble(chatStream, msg.text, false);
                appState.chatMessages.push({ role: 'ai', text: msg.text });
            }
            // 【优化1】检测 AI 说再见 → 自动弹出满意度选择
            checkAutoEndConversation(msg.text);
        } else if (msg.state === 'stop') {
            statusEl.textContent = '请直接说话...';
            appState.isRemoteSpeaking = false;
            if (appState.live2dManager) {
                setTimeout(() => {
                    appState.live2dManager.stopTalking?.();
                }, 500);
            }
        }
    }
}

// 【优化1】检测 AI 说再见 → 自动弹出满意度选择（无需用户手动点击结束按钮）
function checkAutoEndConversation(text) {
    if (appState._autoEndTriggered) return; // 防止重复触发

    const goodbyeKeywords = ['再见', '拜拜', '祝您', '祝您生活愉快', '感谢您的反馈',
        '感谢您的配合', '期待您下次', '谢谢您的反馈', '感谢您的参与',
        '我们的服务到此结束', '本次反馈已结束', '那就先到这里'];

    const isGoodbye = goodbyeKeywords.some(kw => text.includes(kw));
    if (isGoodbye) {
        console.log('[autoEnd] 检测到告别语，自动弹出满意度选择');
        appState._autoEndTriggered = true;
        // 等 TTS 播完后再弹窗（延迟一点让用户听完）
        setTimeout(() => {
            if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
                showSatisfactionDialog();
            }
        }, 1500);
    }
}

function addChatBubble(container, text, isUser) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${isUser ? 'user' : 'ai'}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function normalizePhoneTail(value) {
    const digits = String(value || '').replace(/\D/g, '');
    return digits.length >= 4 ? digits.slice(-4) : '';
}

function formLine(label, controlHtml) {
    return `<div style="margin-bottom:12px;text-align:left"><label style="display:block;font-size:13px;color:#666;margin-bottom:6px">${label}</label>${controlHtml}</div>`;
}

function updateCustomerIdentityFromText(text) {
    const raw = String(text || '');
    const phoneTail = normalizePhoneTail(raw);
    if (phoneTail) appState.phoneTail = phoneTail;

    const namePatterns = [
        /(?:我叫|我是|叫我)([一-龥A-Za-z]{1,12})/,
        /(?:称呼|叫)(?:我)?[：:，,\s]*([一-龥A-Za-z]{1,12})/,
    ];
    for (const pattern of namePatterns) {
        const match = raw.match(pattern);
        if (match && match[1] && !/^\d+$/.test(match[1])) {
            appState.customerName = match[1].slice(0, 12);
            break;
        }
    }
}

async function ensureCustomerIdentity() {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
        <div class="modal-card satisfaction-modal identity-modal">
            <h2>最后一步：确认客户信息</h2>
            <p class="modal-subtitle">请用表单留下称呼和手机号后四位，方便门店把本次反馈关联到您的客户档案。</p>
            ${formLine('怎么称呼您', `<input id="identityName" class="form-input" placeholder="例如：张姐 / 李女士" value="${escapeHtml(appState.customerName || '')}" autocomplete="name">`)}
            ${formLine('手机号后四位', `<input id="identityPhoneTail" class="form-input" placeholder="例如：9833" maxlength="4" inputmode="numeric" pattern="\\d{4}" value="${escapeHtml(appState.phoneTail || '')}">`)}
            <div class="identity-hint">这些信息不再由 AI 语音追问，请在这里确认后提交。</div>
            <div class="login-error" id="identityError"></div>
            <button class="btn-primary btn-large" id="identityConfirmBtn">确认提交</button>
        </div>`;
        document.body.appendChild(overlay);
        const nameInput = document.getElementById('identityName');
        const phoneInput = document.getElementById('identityPhoneTail');
        phoneInput?.addEventListener('input', (e) => {
            e.target.value = String(e.target.value || '').replace(/\D/g, '').slice(0, 4);
        });
        setTimeout(() => (nameInput || phoneInput)?.focus(), 50);
        document.getElementById('identityConfirmBtn').addEventListener('click', () => {
            const name = nameInput?.value.trim() || '';
            const tail = normalizePhoneTail(phoneInput?.value || '');
            if (!name) {
                document.getElementById('identityError').textContent = '请填写称呼';
                nameInput?.focus();
                return;
            }
            if (tail.length !== 4) {
                document.getElementById('identityError').textContent = '请填写手机号后四位';
                phoneInput?.focus();
                return;
            }
            appState.customerName = name;
            appState.phoneTail = tail;
            document.body.removeChild(overlay);
            resolve(true);
        });
    });
}

async function processAfterConversation(satisfaction) {
    if (appState.chatMessages.length === 0) {
        // 对话没产生任何消息，显示重试按钮而非静默跳回
        const statusEl = document.getElementById('voiceStatus');
        if (statusEl) {
            statusEl.innerHTML = `<div style="text-align:center">
                <div style="font-size:14px;color:#666;margin-bottom:10px">对话未能建立，请重试</div>
                <button onclick="location.hash='#/home';location.reload()" style="padding:8px 16px;background:#4CAF50;color:#fff;border:none;border-radius:6px;cursor:pointer">返回首页</button>
            </div>`;
        }
        return;
    }

    const allText = appState.chatMessages.map(m => `${m.role === 'user' ? '客户' : 'AI'}: ${m.text}`).join('\n');

    // 保存满意度供后续使用
    appState.satisfaction = satisfaction;

    // 【重要】无论 AI 处理是否成功，先保存原始对话记录（防丢失）
    FeedbackAPI.saveRecord({
        storeId: appState.storeInfo?.id,
        employeeId: appState.selectedEmployee?.id,
        sessionId: appState.sessionId,
        deviceMac: appState.deviceMac,
        rawAsrText: allText,
        customerName: appState.customerName,
        phoneTail: appState.phoneTail,
        satisfaction: satisfaction,
    });

    navigate('result');

    const result = await FeedbackAPI.processFeedback({
        sessionId: appState.sessionId,
        deviceMac: appState.deviceMac,
        clientId: 'feedback_client',
        storeName: appState.storeInfo?.storeName || '',
        employeeNumber: String(appState.selectedEmployee?.number || ''),
        asrText: allText,
        customerName: appState.customerName,
        phoneTail: appState.phoneTail,
        satisfaction: satisfaction
    });

    if (result.success) {
        appState.feedbackResult = result.data;
        renderFeedbackResult();
        // AI 处理成功后，更新记录（补全清洗文本/QA/点评）
        FeedbackAPI.saveRecord({
            storeId: appState.storeInfo?.id,
            employeeId: appState.selectedEmployee?.id,
            sessionId: appState.sessionId,
            deviceMac: appState.deviceMac,
            rawAsrText: allText,
            cleanedText: result.data.cleaned_text,
            qaJson: result.data.qa_result,
            reviewLong: result.data.review_long,
            reviewShort: result.data.review_short,
            customerName: appState.customerName,
            phoneTail: appState.phoneTail,
            satisfaction: result.data.satisfaction,
        });
    } else {
        const statusEl = document.getElementById('processStatus');
        if (statusEl) statusEl.textContent = '处理失败: ' + (result.message || '');
        // 即使 AI 处理失败，也渲染不满意的结果页（原始记录已保存）
        appState.feedbackResult = {
            should_publish: false,
            satisfaction: satisfaction,
        };
        renderFeedbackResult();
    }
}

// 显示满意度选择弹窗
function showSatisfactionDialog() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
    <div class="modal-card satisfaction-modal">
        <h2>请评价本次服务</h2>
        <p class="modal-subtitle">选择满意度后，再用表单确认称呼和手机号后四位</p>
        <div class="satisfaction-options">
            <button class="sat-option sat-very-satisfied" data-value="very_satisfied">
                <span class="sat-emoji">🤩</span>
                <span class="sat-label">非常满意</span>
            </button>
            <button class="sat-option sat-satisfied" data-value="satisfied">
                <span class="sat-emoji">😊</span>
                <span class="sat-label">满意</span>
            </button>
            <button class="sat-option sat-unsatisfied" data-value="unsatisfied">
                <span class="sat-emoji">😕</span>
                <span class="sat-label">不满意</span>
            </button>
            <button class="sat-option sat-very-bad" data-value="very_bad">
                <span class="sat-emoji">😡</span>
                <span class="sat-label">非常糟糕</span>
            </button>
        </div>
        <button class="modal-cancel-btn" id="satCancelBtn">取消</button>
    </div>`;
    document.body.appendChild(overlay);

    overlay.querySelectorAll('.sat-option').forEach(btn => {
        btn.addEventListener('click', async () => {
            const satisfaction = btn.dataset.value;
            const ok = await ensureCustomerIdentity();
            if (!ok) return;
            document.body.removeChild(overlay);
            // 关闭WebSocket，进入处理流程
            if (appState.audioRecorder?.isRecording) {
                appState.audioRecorder.stop();
            }
            if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
                // 把 satisfaction 暂存，等 onclose 触发时使用
                appState._pendingSatisfaction = satisfaction;
                appState.ws.close();
            } else {
                processAfterConversation(satisfaction);
            }
        });
    });

    document.getElementById('satCancelBtn').addEventListener('click', () => {
        document.body.removeChild(overlay);
    });
}

// ==================== 结果页 ====================
function renderResult(container) {
    const sat = appState.satisfaction;
    const willPublish = sat === 'very_satisfied' || sat === 'satisfied';

    container.innerHTML = `
    <div class="page result-page">
        <div id="processingView" class="processing-view">
            <div class="processing-icon">✨</div>
            <h2 class="processing-title">${willPublish ? '正在为您生成大众点评好评' : '正在记录您的反馈'}</h2>
            <p class="processing-subtitle">${willPublish ? '请您稍等片刻...' : '感谢您的真实反馈'}</p>
            <div class="processing-loader">
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
            </div>
            <div class="processing-status" id="processStatus">AI正在分析对话内容...</div>
        </div>

        <div id="resultContent" class="result-content-clean" style="display:none">
            <!-- 结果内容动态填充 -->
        </div>
    </div>`;
}

function renderFeedbackResult() {
    const data = appState.feedbackResult;
    const sat = appState.satisfaction;
    const processingView = document.getElementById('processingView');
    const contentEl = document.getElementById('resultContent');

    if (processingView) processingView.style.display = 'none';
    if (!contentEl) return;

    contentEl.style.display = 'block';

    // 情况1: 满意/非常满意 - 展示好评话术 + 一键复制 + 平台跳转
    if (data.should_publish && data.review_long) {
        const storeName = appState.storeInfo?.storeName || '';
        contentEl.innerHTML = `
        <div class="result-header satisfied-header">
            <div class="result-emoji">${sat === 'very_satisfied' ? '🤩' : '😊'}</div>
            <h2>感谢您的好评</h2>
            <p>已为您生成大众点评好评话术</p>
        </div>
        <div class="review-card">
            <div class="review-tabs">
                <button class="tab-btn active" data-tab="long">📝 标准版</button>
                <button class="tab-btn" data-tab="short">⚡ 精简版</button>
            </div>
            <div id="reviewLong" class="review-text-box active">${escapeHtml(data.review_long)}</div>
            <div id="reviewShort" class="review-text-box">${escapeHtml(data.review_short || '')}</div>
        </div>
        <div class="review-actions">
            <button id="copyLongBtn" class="btn-copy-review">📋 复制标准版好评</button>
            <button id="copyShortBtn" class="btn-copy-review btn-copy-short" style="display:none">📋 复制精简版好评</button>
        </div>
        <div class="platform-section">
            <h3>一键发布到平台</h3>
            <p class="platform-hint">点击下方按钮打开APP，粘贴刚才复制的点评即可</p>
            <div class="platform-buttons-inline">
                <button id="openDianpingBtn" class="btn-platform btn-dianping">📍 大众点评</button>
                <button id="openMeituanBtn" class="btn-platform btn-meituan">🎯 美团</button>
            </div>
        </div>
        <button id="completeBtn2" class="btn-secondary btn-large" style="margin-top:16px">完成</button>`;

        // Tab 切换逻辑
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.review-text-box').forEach(t => t.classList.remove('active'));
                btn.classList.add('active');
                const tab = btn.dataset.tab;
                const isLong = tab === 'long';
                document.getElementById(isLong ? 'reviewLong' : 'reviewShort').classList.add('active');
                // 切换复制按钮
                document.getElementById('copyLongBtn').style.display = isLong ? '' : 'none';
                document.getElementById('copyShortBtn').style.display = isLong ? 'none' : '';
            });
        });

        // 一键复制（标准版）
        document.getElementById('copyLongBtn').addEventListener('click', async () => {
            const ok = await copyToClipboard(data.review_long || '');
            const btn = document.getElementById('copyLongBtn');
            if (ok) {
                btn.textContent = '✅ 已复制到剪贴板';
                btn.classList.add('copied');
                speak('好评已复制，请打开大众点评粘贴发布');
                if (isMobile()) showManualCopySheet(data.review_long || '');
            } else {
                btn.textContent = '请长按文字手动复制';
                showManualCopySheet(data.review_long || '');
            }
            setTimeout(() => { btn.textContent = '📋 复制标准版好评'; btn.classList.remove('copied'); }, 3000);
        });

        // 一键复制（精简版）
        document.getElementById('copyShortBtn').addEventListener('click', async () => {
            const ok = await copyToClipboard(data.review_short || '');
            const btn = document.getElementById('copyShortBtn');
            if (ok) {
                btn.textContent = '✅ 已复制到剪贴板';
                btn.classList.add('copied');
                speak('好评已复制，请打开美团粘贴发布');
                if (isMobile()) showManualCopySheet(data.review_short || '');
            } else {
                btn.textContent = '请长按文字手动复制';
                showManualCopySheet(data.review_short || '');
            }
            setTimeout(() => { btn.textContent = '📋 复制精简版好评'; btn.classList.remove('copied'); }, 3000);
        });

        // 平台跳转
        document.getElementById('openDianpingBtn').addEventListener('click', () => openDianping(storeName));
        document.getElementById('openMeituanBtn').addEventListener('click', () => openMeituan(storeName));
        document.getElementById('completeBtn2').addEventListener('click', () => navigate('complete'));
    } else {
        // 情况2: 不满意/非常糟糕 - 致歉 + 引导
        const isVeryBad = sat === 'very_bad';
        contentEl.innerHTML = `
        <div class="result-header unsatisfied-header">
            <div class="result-emoji">${isVeryBad ? '🙏' : '😔'}</div>
            <h2>${isVeryBad ? '非常抱歉给您带来不好的体验' : '感谢您的真实反馈'}</h2>
            <p>${isVeryBad ? '门店管理团队会尽快与您联系处理' : '您的意见我们已记录，会持续改进'}</p>
        </div>
        <div class="feedback-saved-card">
            <div class="saved-icon">✓</div>
            <div class="saved-text">
                <div class="saved-title">反馈已记录</div>
                <div class="saved-subtitle">门店管理人员将查阅您的反馈</div>
            </div>
        </div>
        <button id="completeBtn" class="btn-primary btn-large">完成</button>`;

        document.getElementById('completeBtn').addEventListener('click', () => navigate('complete'));
    }
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==================== 发布好评页 ====================
function renderPublish(container) {
    const data = appState.feedbackResult || {};
    container.innerHTML = `
    <div class="page publish-page">
        <div class="page-header">
            <h1>⭐ 发布好评</h1>
        </div>
        <div class="review-box">
            <h3>好评话术</h3>
            <div class="review-content" id="reviewContent">${data.review_long || ''}</div>
            <button id="copyReviewBtn" class="btn-primary">📋 复制好评</button>
        </div>
        <div class="platform-buttons">
            <h3>跳转评价平台</h3>
            <button id="openDianpingBtn" class="btn-platform btn-dianping">📍 打开大众点评</button>
            <button id="openMeituanBtn" class="btn-platform btn-meituan">🎯 打开美团</button>
        </div>
        <button id="completeBtn" class="btn-complete">完成</button>
    </div>`;

    document.getElementById('copyReviewBtn').addEventListener('click', async () => {
        const text = data.review_long || '';
        const ok = await copyToClipboard(text);
        if (ok) {
            document.getElementById('copyReviewBtn').textContent = '✅ 已复制';
            speak('好评话术已复制成功，请直接粘贴发布，感谢您的支持！');
            if (isMobile()) showManualCopySheet(text);
        } else {
            showManualCopySheet(text);
        }
    });

    const storeName = appState.storeInfo?.storeName || '';
    document.getElementById('openDianpingBtn').addEventListener('click', () => openDianping(storeName));
    document.getElementById('openMeituanBtn').addEventListener('click', () => openMeituan(storeName));
    document.getElementById('completeBtn').addEventListener('click', () => navigate('complete'));
}

// ==================== 完成页 ====================
function renderComplete(container) {
    container.innerHTML = `
    <div class="page complete-page">
        <div class="complete-content">
            <div class="complete-icon">🎉</div>
            <h1>感谢您的反馈！</h1>
            <p>您的意见对我们非常重要</p>
            <p>祝您生活愉快！</p>
        </div>
        <button id="retryBtn" class="btn-primary btn-large">再来一次</button>
    </div>`;

    document.getElementById('retryBtn').addEventListener('click', () => {
        appState.selectedEmployee = null;
        appState.chatMessages = [];
        appState.feedbackResult = null;
        appState.sessionId = '';
        appState._otaResult = null;
        if (appState.ws) {
            try { appState.ws.close(); } catch (e) {}
            appState.ws = null;
        }
        // 清理 Live2D 实例
        if (appState.live2dManager) {
            try { appState.live2dManager.destroy(); } catch (e) {}
            appState.live2dManager = null;
        }
        navigate('home');
    });
}

// ==================== 初始化 ====================
window.addEventListener('hashchange', render);
window.addEventListener('load', render);
