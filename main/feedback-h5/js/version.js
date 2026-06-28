/**
 * 版本控制 + 缓存清除
 *
 * 作用：每次部署后修改 VERSION 常量，浏览器会把所有 JS/CSS
 *      当成新文件强制重新下载，彻底解决手机端缓存旧版代码的问题。
 *
 * 工作原理：
 * 1. 页面加载时，这个脚本最早执行（在 app.js 之前）
 * 2. 找到所有 <script src="js/xxx.js"> 和 <link href="css/xxx.css">
 * 3. 给 URL 加上 ?v=VERSION 查询参数
 * 4. 浏览器看到不同的 URL 就会重新下载，不读缓存
 *
 * 部署后改这个版本号即可（例如发布日 a→b→c）：
 */
window.APP_VERSION = '20260625-process-fix';

(function () {
    var v = window.APP_VERSION;
    // 给所有 js/ 目录下的 script 加版本号
    document.querySelectorAll('script[src]').forEach(function (el) {
        var src = el.getAttribute('src');
        if (src && (src.indexOf('js/') === 0 || src.indexOf('/js/') !== -1)) {
            el.setAttribute('src', src.split('?')[0] + '?v=' + v);
        }
    });
    // 给 css 加版本号
    document.querySelectorAll('link[href]').forEach(function (el) {
        var href = el.getAttribute('href');
        if (href && (href.indexOf('css/') === 0 || href.indexOf('/css/') !== -1)) {
            el.setAttribute('href', href.split('?')[0] + '?v=' + v);
        }
    });
})();
