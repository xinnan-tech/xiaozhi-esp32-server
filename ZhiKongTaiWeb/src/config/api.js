// 获取当前运行环境的基础 URL
const getBaseUrl = () => {
    // 如果是开发环境，使用环境变量中的地址
    if (import.meta.env.DEV) {
        return import.meta.env.VITE_API_BASE_URL;
    }
    
    // 生产环境使用当前域名和端口
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    return `${protocol}//${hostname}${port ? `:${port}` : ''}`;
};

export const API_BASE_URL = getBaseUrl(); 