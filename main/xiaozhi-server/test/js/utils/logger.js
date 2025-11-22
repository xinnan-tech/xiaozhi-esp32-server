import { getLogContainer } from '../ui/dom-helper.js'

const logContainer = getLogContainer();
// 日志记录函数
export function log(message, type = 'info') {
    // 将消息按换行符分割成多行
    const lines = message.split('\n');
    const now = new Date();
    // const timestamp = `[${now.toLocaleTimeString()}] `;
    const timestamp = `[${now.toLocaleTimeString()}.${now.getMilliseconds().toString().padStart(3, '0')}] `;
    // 为每一行创建日志条目
    lines.forEach((line, index) => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        // 如果是第一条日志，显示时间戳
        const prefix = index === 0 ? timestamp : ' '.repeat(timestamp.length);
        logEntry.textContent = `${prefix}${line}`;
        // logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        // logEntry.style 保留起始的空格
        logEntry.style.whiteSpace = 'pre';
        if (type === 'error') {
            logEntry.style.color = 'red';
        } else if (type === 'debug') {
            logEntry.style.color = 'gray';
            return;
        } else if (type === 'warning') {
            logEntry.style.color = 'orange';
        } else if (type === 'success') {
            logEntry.style.color = 'green';
        } else {
            logEntry.style.color = 'black';
        }
        logContainer.appendChild(logEntry);
    });

    logContainer.scrollTop = logContainer.scrollHeight;
}