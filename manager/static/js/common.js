function post(api, bodyData, fn) {
    let basePath = '';
    let token = localStorage.getItem('token');
    fetch(basePath + api, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token,
        },
        body: bodyData==null ? null : JSON.stringify(bodyData)
    })
        .then(response => response.json())
        .then(data => {
            if(data.code === 401){
                window.location = 'login.html';
                return
            }
            fn(data);
        });
}

function get(api, fn) {
    let basePath = 'http://localhost:8001';
    let token = localStorage.getItem('token');
    fetch(basePath + api, {
        method: "GET",
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token,
        },
    })
        .then(response => response.json())
        .then(data => {
            if(data.code === 401){
                window.location = 'login.html';
                return
            }
            fn(data);
        });
}

// 注册全局组件
const AppHeader = {
    template: `
        <header class="app-header">
            <div class="header-logo">AI</div>
            <slot>xiaozhi-esp32-server</slot>
        </header>
    `
};

const AppFooter = {
    template: `
        <footer class="app-footer">
            <slot>© 2025 xiaozhi-esp32-server</slot>
        </footer>
    `
};

// 初始化Vue应用的通用配置
function createVueApp(options) {
    const app = Vue.createApp({
        ...options,
        components: { AppHeader, AppFooter }
    });
    app.use(ElementPlus);
    return app;
}