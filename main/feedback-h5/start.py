#!/usr/bin/env python3
"""客户反馈 H5 服务器 + 全协议反向代理 - 端口 8007

一站式服务（FRP 单端口模式）:
  外网 https://feedback.new123.vip
    → FRP 隧道 → 本地 8007 (本服务)
      ├─ /              → H5 静态文件
      ├─ /api/v1/*      → 反代到 127.0.0.1:8009 (feedback-backend HTTP)
      ├─ /health        → 反代到 127.0.0.1:8009
      ├─ /xiaozhi/ota/* → 反代到 127.0.0.1:8002 (Java HTTP)
      └─ /ws/*          → 反代到 127.0.0.1:18000 (xiaozhi-server WebSocket)

依赖: aiohttp (pip install aiohttp)
"""

import asyncio
import os
import sys
import mimetypes
from pathlib import Path

from aiohttp import web, ClientSession, ClientTimeout, WSMsgType, ClientConnectionError

PORT = int(os.environ.get('H5_PORT', '8007'))
DIRECTORY = Path(__file__).resolve().parent
ADMIN_DIRECTORY = Path(
    os.environ.get('ADMIN_UI_DIR', DIRECTORY.parent / 'feedback-backend' / 'admin-ui')
).resolve()

# 反向代理目标地址：优先读环境变量（容器内用 docker 服务名，本地裸跑用 127.0.0.1）
# 本地裸跑: FEEDBACK_BACKEND_HOST=127.0.0.1  (默认)
# Docker:   FEEDBACK_BACKEND_HOST=feedback-backend  (compose 服务名)
FEEDBACK_BACKEND_HOST = os.environ.get('FEEDBACK_BACKEND_HOST', '127.0.0.1')
FEEDBACK_BACKEND_PORT = int(os.environ.get('FEEDBACK_BACKEND_PORT', '8009'))
JAVA_HOST = os.environ.get('JAVA_HOST', '127.0.0.1')
JAVA_PORT = int(os.environ.get('JAVA_PORT', '8002'))

# 反向代理路由表
# (路径前缀, 目标 host, 目标 port, 协议)
HTTP_PROXY_RULES = [
    ('/api/v1/', FEEDBACK_BACKEND_HOST, FEEDBACK_BACKEND_PORT),  # feedback-backend
    ('/health',   FEEDBACK_BACKEND_HOST, FEEDBACK_BACKEND_PORT),
    ('/xiaozhi/ota/', JAVA_HOST, JAVA_PORT),                      # Java OTA
]

# WebSocket 代理目标：
# - /api/v1/agent/chat/ws → ws://<FEEDBACK_BACKEND_HOST>:<FEEDBACK_BACKEND_PORT>/api/v1/agent/chat/ws
# - /ws/ → ws://<XIAOZHI_WS_HOST>:<XIAOZHI_WS_PORT>/xiaozhi/v1/
# 本地裸跑: XIAOZHI_WS_HOST=127.0.0.1, XIAOZHI_WS_PORT=18000 (宿主机映射端口)
# Docker:   XIAOZHI_WS_HOST=xiaozhi-esp32-server, XIAOZHI_WS_PORT=8000 (容器内端口)
WS_PROXY_TARGET_HOST = os.environ.get('XIAOZHI_WS_HOST', '127.0.0.1')
WS_PROXY_TARGET_PORT = int(os.environ.get('XIAOZHI_WS_PORT', '18000'))
WS_PROXY_TARGET_PATH = os.environ.get('XIAOZHI_WS_PATH', '/xiaozhi/v1/')

# 不允许透传的 hop-by-hop 请求头
HOP_BY_HOP_HEADERS = frozenset({
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade', 'host', 'content-length',
})


# ============================================================
# HTTP 反向代理
# ============================================================
async def http_proxy_handler(request: web.Request) -> web.StreamResponse:
    """HTTP 反向代理：将请求转发到匹配的后端服务"""
    path = request.path

    # 找到匹配的代理规则
    target = None
    for prefix, host, port in HTTP_PROXY_RULES:
        if path.startswith(prefix) or path == prefix.rstrip('/'):
            target = (host, port)
            break

    if not target:
        return web.Response(status=404, text='No proxy rule matched')

    host, port = target
    target_url = f'http://{host}:{port}{path}'
    if request.query_string:
        target_url += '?' + request.query_string

    # 准备请求头（移除 hop-by-hop）
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in HOP_BY_HOP_HEADERS}

    # 读取请求体
    body = await request.read() if request.body_exists else None

    # 转发请求
    timeout = ClientTimeout(total=60)
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                allow_redirects=False,
            ) as upstream_resp:
                # 透传响应头
                resp_headers = {k: v for k, v in upstream_resp.headers.items()
                                if k.lower() not in HOP_BY_HOP_HEADERS}
                # 添加 CORS（防止后端没加）
                resp_headers.setdefault('Access-Control-Allow-Origin', '*')

                response = web.StreamResponse(
                    status=upstream_resp.status,
                    headers=resp_headers,
                )
                await response.prepare(request)

                # 流式转发响应体
                async for chunk in upstream_resp.content.iter_chunked(8192):
                    await response.write(chunk)
                await response.write_eof()
                return response

    except ClientConnectionError as e:
        return web.Response(status=502, text=f'Bad Gateway: backend unreachable ({e})')
    except asyncio.TimeoutError:
        return web.Response(status=504, text='Gateway Timeout')
    except Exception as e:
        return web.Response(status=502, text=f'Proxy error: {e}')



async def agent_chat_ws_proxy_handler(request: web.Request) -> web.WebSocketResponse:
    """WebSocket 反向代理：后台管理 AI 数字人长连接。"""
    return await websocket_proxy_handler(
        request,
        target_host=FEEDBACK_BACKEND_HOST,
        target_port=FEEDBACK_BACKEND_PORT,
        target_path=request.path,
        label='AGENT-WS-PROXY',
    )


async def websocket_proxy_handler(
    request: web.Request,
    target_host: str,
    target_port: int,
    target_path: str,
    label: str = 'WS-PROXY',
) -> web.WebSocketResponse:
    """通用 WebSocket 透明代理。"""
    print('=' * 70, file=sys.stderr)
    print(f'[{label}] 收到 WebSocket 升级请求', file=sys.stderr)
    print(f'  客户端: {request.remote}', file=sys.stderr)
    print(f'  路径: {request.path}', file=sys.stderr)
    print(f'  查询参数: {request.query_string[:120]}', file=sys.stderr)
    print(f'  请求头:', file=sys.stderr)
    for k, v in request.headers.items():
        v_show = v if len(v) < 60 else v[:50] + '...'
        print(f'    {k}: {v_show}', file=sys.stderr)

    upgrade = request.headers.get('Upgrade', '').lower()
    connection = request.headers.get('Connection', '').lower()
    ws_key = request.headers.get('Sec-WebSocket-Key', '')
    ws_version = request.headers.get('Sec-WebSocket-Version', '')
    print(f'  WS 升级检查: Upgrade={upgrade!r}, Connection={connection!r}, '
          f'Key={"有" if ws_key else "❌缺失"}, Version={ws_version!r}', file=sys.stderr)
    if 'websocket' not in upgrade or 'upgrade' not in connection:
        print(f'  ❌ 升级头缺失！aiohttp 会返回 400', file=sys.stderr)
        print(f'  → 通常是 Nginx/反代没有正确转发 Upgrade 和 Connection 头', file=sys.stderr)
    print('=' * 70, file=sys.stderr)

    target_ws_url = f'ws://{target_host}:{target_port}{target_path}'
    if request.query_string:
        target_ws_url += '?' + request.query_string
    print(f'[{label}] 转发到上游: {target_ws_url[:120]}...', file=sys.stderr)

    client_ws = web.WebSocketResponse(max_msg_size=0, autoping=True, heartbeat=30)
    if not client_ws.can_prepare(request).ok:
        reason = client_ws.can_prepare(request).protocol or '请求头不符合 WebSocket 协议'
        print(f'[{label}] ❌ 无法升级为 WebSocket: {reason}', file=sys.stderr)
        return web.Response(
            status=400,
            text=f'WebSocket upgrade rejected: {reason}\n'
                 f'Hint: 检查反向代理是否转发了 Upgrade 和 Connection 头\n'
                 f'Got headers: Upgrade={upgrade!r}, Connection={connection!r}\n'
        )

    await client_ws.prepare(request)
    print(f'[{label}] 客户端 WebSocket 升级成功', file=sys.stderr)

    timeout = ClientTimeout(total=None, connect=10, sock_read=None)
    msg_counter = {'c2u_text': 0, 'c2u_bin': 0, 'u2c_text': 0, 'u2c_bin': 0}
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.ws_connect(
                target_ws_url,
                max_msg_size=0,
                autoping=True,
                heartbeat=30,
            ) as upstream_ws:
                print(f'[{label}] ✅ 已连接上游', file=sys.stderr)

                async def client_to_upstream():
                    async for msg in client_ws:
                        if msg.type == WSMsgType.TEXT:
                            msg_counter['c2u_text'] += 1
                            if msg_counter['c2u_text'] <= 3:
                                print(f'[{label}] C→U TEXT #{msg_counter["c2u_text"]}: {msg.data[:120]}', file=sys.stderr)
                            await upstream_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            msg_counter['c2u_bin'] += 1
                            if msg_counter['c2u_bin'] <= 3:
                                print(f'[{label}] C→U BIN #{msg_counter["c2u_bin"]}: {len(msg.data)} bytes', file=sys.stderr)
                            await upstream_ws.send_bytes(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            print(f'[{label}] 客户端 WS 错误: {client_ws.exception()}', file=sys.stderr)
                            break
                    if not upstream_ws.closed:
                        await upstream_ws.close()

                async def upstream_to_client():
                    async for msg in upstream_ws:
                        if msg.type == WSMsgType.TEXT:
                            msg_counter['u2c_text'] += 1
                            if msg_counter['u2c_text'] <= 3:
                                print(f'[{label}] U→C TEXT #{msg_counter["u2c_text"]}: {msg.data[:120]}', file=sys.stderr)
                            await client_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            msg_counter['u2c_bin'] += 1
                            if msg_counter['u2c_bin'] <= 3:
                                print(f'[{label}] U→C BIN #{msg_counter["u2c_bin"]}: {len(msg.data)} bytes', file=sys.stderr)
                            await client_ws.send_bytes(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            print(f'[{label}] 上游 WS 错误: {upstream_ws.exception()}', file=sys.stderr)
                            break
                    if not client_ws.closed:
                        await client_ws.close()

                await asyncio.gather(client_to_upstream(), upstream_to_client())
                print(f'[{label}] 连接结束，消息统计: {msg_counter}', file=sys.stderr)

    except ClientConnectionError as e:
        print(f'[{label}] ❌ 连接上游失败: {e}', file=sys.stderr)
        if not client_ws.closed:
            await client_ws.close(code=1011, message=b'upstream connect failed')
    except Exception as e:
        print(f'[{label}] ❌ 代理异常: {type(e).__name__}: {e}', file=sys.stderr)
        if not client_ws.closed:
            await client_ws.close(code=1011, message=str(e).encode()[:120])
    finally:
        print(f'[{label}] 关闭', file=sys.stderr)

    return client_ws


# ============================================================
# WebSocket 反向代理
# ============================================================
async def ws_proxy_handler(request: web.Request) -> web.WebSocketResponse:
    """WebSocket 反向代理：客户端 ↔ 本服务 ↔ xiaozhi-server

    路径映射: /ws/* → ws://127.0.0.1:18000/xiaozhi/v1/*
    所有 query string 一并转发（device-id, client-id, authorization 等）
    """
    sub_path = request.path[len('/ws'):] or '/'
    if not sub_path.startswith('/'):
        sub_path = '/' + sub_path
    target_path = WS_PROXY_TARGET_PATH.rstrip('/') + sub_path
    return await websocket_proxy_handler(
        request,
        target_host=WS_PROXY_TARGET_HOST,
        target_port=WS_PROXY_TARGET_PORT,
        target_path=target_path,
        label='WS-PROXY',
    )


# ============================================================
# 静态文件服务
# ============================================================
async def admin_static_handler(request: web.Request) -> web.StreamResponse:
    """反馈后台静态文件服务。"""
    if not ADMIN_DIRECTORY.exists():
        return web.Response(status=404, text=f'Admin UI not found: {ADMIN_DIRECTORY}')

    sub_path = request.match_info.get('path', '')
    if request.path in ('/admin', '/admin/') or not sub_path:
        sub_path = 'index.html'

    file_path = (ADMIN_DIRECTORY / sub_path).resolve()
    try:
        file_path.relative_to(ADMIN_DIRECTORY)
    except ValueError:
        return web.Response(status=403, text='Forbidden')

    if not file_path.exists() or not file_path.is_file():
        index_file = ADMIN_DIRECTORY / 'index.html'
        if index_file.exists():
            file_path = index_file
        else:
            return web.Response(status=404, text='Not Found')

    mime, _ = mimetypes.guess_type(str(file_path))
    if file_path.suffix == '.js' or file_path.suffix == '.mjs':
        mime = 'application/javascript'
    elif file_path.suffix == '.wasm':
        mime = 'application/wasm'
    if not mime:
        mime = 'application/octet-stream'

    headers = {
        'Content-Type': mime,
        'Access-Control-Allow-Origin': '*',
    }
    if file_path.suffix in ('.js', '.css', '.html'):
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    else:
        headers['Cache-Control'] = 'public, max-age=86400'

    return web.FileResponse(file_path, headers=headers)


async def static_handler(request: web.Request) -> web.StreamResponse:
    """客户反馈 H5 静态文件服务。"""
    path = request.path
    if path == '/' or path == '':
        path = '/index.html'

    # 防止路径穿越攻击
    file_path = (DIRECTORY / path.lstrip('/')).resolve()
    try:
        file_path.relative_to(DIRECTORY)
    except ValueError:
        return web.Response(status=403, text='Forbidden')

    # SPA 兜底：未找到的路径返回 index.html（让前端路由处理）
    if not file_path.exists() or not file_path.is_file():
        index_file = DIRECTORY / 'index.html'
        if index_file.exists():
            file_path = index_file
        else:
            return web.Response(status=404, text='Not Found')

    # 推断 MIME 类型
    mime, _ = mimetypes.guess_type(str(file_path))
    if file_path.suffix == '.js' or file_path.suffix == '.mjs':
        mime = 'application/javascript'
    elif file_path.suffix == '.wasm':
        mime = 'application/wasm'
    if not mime:
        mime = 'application/octet-stream'

    headers = {
        'Content-Type': mime,
        'Access-Control-Allow-Origin': '*',
    }
    # JS/CSS 不缓存（H5 单页应用，确保更新及时生效）
    if file_path.suffix in ('.js', '.css', '.html'):
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    else:
        headers['Cache-Control'] = 'public, max-age=86400'

    return web.FileResponse(file_path, headers=headers)


async def options_handler(request: web.Request) -> web.Response:
    """OPTIONS 预检请求"""
    return web.Response(
        status=204,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Device-Id, Client-Id, Authorization',
            'Access-Control-Max-Age': '86400',
        }
    )


# ============================================================
# 应用启动
# ============================================================
def create_app() -> web.Application:
    app = web.Application(client_max_size=10 * 1024 * 1024)  # 10MB 上限

    # 路由优先级：从具体到通用

    # 1a. 后台 AI 数字人长连接（必须在 /ws/ 通用代理前）
    app.router.add_route('GET', '/api/v1/agent/chat/ws', agent_chat_ws_proxy_handler)

    # 1b. WebSocket 代理（必须在通用规则前）
    app.router.add_route('GET', '/ws', ws_proxy_handler)
    app.router.add_route('GET', '/ws/', ws_proxy_handler)
    app.router.add_route('GET', '/ws/{path:.*}', ws_proxy_handler)

    # 2. OPTIONS 预检（所有路径）
    app.router.add_route('OPTIONS', '/{path:.*}', options_handler)

    # 3. HTTP 反向代理（按前缀匹配）
    for prefix, _, _ in HTTP_PROXY_RULES:
        # 处理前缀路径本身和子路径
        clean_prefix = prefix.rstrip('/')
        app.router.add_route('*', clean_prefix, http_proxy_handler)
        app.router.add_route('*', clean_prefix + '/', http_proxy_handler)
        app.router.add_route('*', clean_prefix + '/{path:.*}', http_proxy_handler)

    # 4. 后台管理静态文件（公网 feedback-admin.new123.vip 通过 Tailscale 反代到这里）
    app.router.add_route('GET', '/admin', admin_static_handler)
    app.router.add_route('GET', '/admin/', admin_static_handler)
    app.router.add_route('GET', '/admin/{path:.*}', admin_static_handler)

    # 5. H5 静态文件兜底
    app.router.add_route('GET', '/', static_handler)
    app.router.add_route('GET', '/{path:.*}', static_handler)

    return app


def main():
    app = create_app()

    print(f'客户反馈 H5 服务已启动')
    print(f'页面地址: http://127.0.0.1:{PORT}/')
    print(f'')
    print(f'反向代理规则:')
    print(f'  /                → 静态文件 ({DIRECTORY})')
    for prefix, host, port in HTTP_PROXY_RULES:
        print(f'  {prefix:18s} → http://{host}:{port}{prefix} (HTTP)')
    print(f'  /ws/             → ws://{WS_PROXY_TARGET_HOST}:{WS_PROXY_TARGET_PORT}{WS_PROXY_TARGET_PATH} (WebSocket)')
    print(f'')
    print(f'按 Ctrl+C 停止')
    print('=' * 70)

    web.run_app(app, host='0.0.0.0', port=PORT, print=None, access_log=None)


if __name__ == '__main__':
    main()
