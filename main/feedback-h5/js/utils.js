// 工具函数模块

// 生成随机MAC地址
export function generateRandomMac() {
    const hexDigits = '0123456789ABCDEF';
    let mac = 'FB';
    for (let i = 0; i < 5; i++) {
        mac += ':';
        for (let j = 0; j < 2; j++) {
            mac += hexDigits.charAt(Math.floor(Math.random() * 16));
        }
    }
    return mac;
}

// 复制文本到剪贴板（兼容手机浏览器/微信内置浏览器）
export async function copyToClipboard(text) {
    const value = String(text || '');
    if (!value) return false;

    // 1. 标准 Clipboard API：必须在用户点击事件中调用，HTTPS 下成功率最高
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(value);
            return true;
        }
    } catch (e) {
        // 继续走降级方案
    }

    // 2. 移动端/旧浏览器降级：textarea + select + execCommand
    const textArea = document.createElement('textarea');
    textArea.value = value;
    textArea.setAttribute('readonly', 'readonly');
    textArea.style.position = 'fixed';
    textArea.style.top = '50%';
    textArea.style.left = '50%';
    textArea.style.width = '1px';
    textArea.style.height = '1px';
    textArea.style.opacity = '0.01';
    textArea.style.zIndex = '-1';
    document.body.appendChild(textArea);

    try {
        textArea.focus({ preventScroll: true });
        textArea.select();
        textArea.setSelectionRange(0, value.length);
        const ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(textArea);
        return !!ok;
    } catch (e) {
        try { document.body.removeChild(textArea); } catch (_) {}
        return false;
    }
}

export function showManualCopySheet(text) {
    const old = document.getElementById('manualCopySheet');
    if (old) old.remove();
    const overlay = document.createElement('div');
    overlay.id = 'manualCopySheet';
    overlay.className = 'manual-copy-overlay';
    overlay.innerHTML = `
        <div class="manual-copy-card">
            <h3>长按复制点评文字</h3>
            <p>当前浏览器限制了自动复制，请长按下方文本，使用手机系统菜单复制。</p>
            <textarea id="manualCopyText" readonly>${String(text || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
            <button id="manualCopyClose" class="btn-primary btn-large">我已复制</button>
        </div>`;
    document.body.appendChild(overlay);
    const ta = document.getElementById('manualCopyText');
    setTimeout(() => {
        try {
            ta.focus();
            ta.select();
            ta.setSelectionRange(0, ta.value.length);
        } catch (e) {}
    }, 50);
    document.getElementById('manualCopyClose').onclick = () => overlay.remove();
}

// TTS语音播报
export function speak(text) {
    try {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
            return true;
        }
    } catch (e) {
        // 忽略TTS错误
    }
    return false;
}

// 检测是否是移动端
export function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// 检测是否在微信内
function isWechat() {
    return /MicroMessenger/i.test(navigator.userAgent);
}

// 智能跳转 - 先尝试唤起APP，失败则跳网页版
function smartOpen(appUrl, webUrl, appName) {
    // 微信浏览器拦截 deep link，直接跳网页提示
    if (isWechat()) {
        alert(`微信内无法直接打开${appName}，请点击右上角菜单 → "在浏览器中打开"`);
        window.location.href = webUrl;
        return;
    }

    // PC 浏览器或非移动端 - 直接打开网页
    if (!isMobile()) {
        window.open(webUrl, '_blank');
        return;
    }

    // 移动端 - 用 iframe 唤起 APP，避免错误页面
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = appUrl;
    document.body.appendChild(iframe);

    // 监听页面是否真的离开了（说明 APP 唤起成功）
    let appOpened = false;
    const visibilityHandler = () => {
        if (document.hidden) {
            appOpened = true;
        }
    };
    document.addEventListener('visibilitychange', visibilityHandler);

    // 2.5秒后判断：如果页面没有变成 hidden，说明 APP 没打开，跳网页
    setTimeout(() => {
        document.removeEventListener('visibilitychange', visibilityHandler);
        if (iframe.parentNode) iframe.parentNode.removeChild(iframe);

        if (!appOpened && !document.hidden) {
            // APP 没打开 - 跳网页
            window.location.href = webUrl;
        }
    }, 2500);
}

// 打开大众点评 - 直接搜索门店
export function openDianping(storeName) {
    // 大众点评 URL Scheme（搜索关键词）
    // 注意：iOS需要在白名单 LSApplicationQueriesSchemes
    const appUrl = `dianping://search?keyword=${encodeURIComponent(storeName)}`;
    const webUrl = `https://www.dianping.com/search/keyword/0/0_${encodeURIComponent(storeName)}`;
    smartOpen(appUrl, webUrl, '大众点评');
}

// 打开美团 - 直接搜索门店
export function openMeituan(storeName) {
    // 美团 URL Scheme（搜索关键词）
    const appUrl = `imeituan://www.meituan.com/search?q=${encodeURIComponent(storeName)}`;
    const webUrl = `https://i.meituan.com/index/search?q=${encodeURIComponent(storeName)}`;
    smartOpen(appUrl, webUrl, '美团');
}

// 员工类型标签
export const EMPLOYEE_TYPE_MAP = {
    'manager': '店长',
    'excellent': '优秀',
    'intern': '实习',
    'normal': ''
};

// 获取员工类型标签
export function getEmployeeTypeLabel(type) {
    return EMPLOYEE_TYPE_MAP[type] || '';
}
