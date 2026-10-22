"""issue 3448 设备认证旁路回归测试。

覆盖的旁路与配套改动：
  1. websocket 白名单免 token → 白名单只延长有效期，仍校验 token
  2. OTA 匿名签发 token → 旧 token 续签 / 一次性激活码首次绑定
  3. vision web_test_client 硬编码后门 → 删除
  4. MQTT 分支不受 auth_enable 约束 + topic 注入 → 纳入门禁 + Device-Id 格式校验
  5. OTA 固件下载无鉴权 → 需带凭证
  6. 白名单设备升级后没有换凭证的入口 → 一次性自举 + 缺配置时的启动告警
  7. 激活码不绑设备、消费时机过早 → 绑到 Device-Id，响应组装成功后才作废
  8. 有效期覆盖参数绕过归一化、吊销线配置不合法被静默吞掉 → 统一归一化 + 启动报错
  9. OTA 请求头日志打印新凭证 → 凭证脱敏
  10. Device-Model 未校验却参与 MQTT 密码签名 → 按字符集校验
  11. Device-Id 门禁放在 auth 之外，未开认证的部署被无端拦下 → 只在真下发 MQTT 时校验
  12. 智控台部署下 config_loader 整块覆盖 auth 段 → 改成逐键合并
  13. 浏览器无法自定义 websocket 请求头 → 凭证改走子协议头，URL 查询串不再采信
  14. 陌生来源的响应不带 Vary，共享缓存可能串味 → 带 Origin 就无条件标 Vary

Usage:
    python benchmark/check_auth_3448.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)

from core.auth import (  # noqa: E402
    AuthManager,
    AuthenticationError,
    DEFAULT_EXPIRE_SECONDS,
    MAX_EXPIRE_SECONDS,
)
from core.api.ota_handler import OTAHandler, _parse_activation_codes  # noqa: E402
from core.api.vision_handler import VisionHandler  # noqa: E402

SECRET = "test-auth-key-for-3448"
ALLOWED_MAC = "aa:bb:cc:dd:ee:ff"
OTHER_MAC = "11:22:33:44:55:66"
CLIENT_ID = "7b94d69a-9808-4c59-9c9b-704333b38aff"


def build_config(enabled=True, allowed=None, cors=None, **extra):
    auth = {"enabled": enabled, "allowed_devices": allowed or []}
    auth.update(extra)
    server = {"auth": auth, "auth_key": SECRET}
    if cors is not None:
        server["cors"] = cors
    for key, value in extra.pop("_server", {}).items():
        server[key] = value
    return {"server": server}


def build_ws_server(config):
    """绕开 WebSocketServer.__init__ 的模块初始化，只加载认证属性"""
    from core.websocket_server import WebSocketServer

    ws = WebSocketServer.__new__(WebSocketServer)
    ws.config = config
    ws.logger = recording_logger()
    ws._load_auth_config(config)
    return ws


def build_ota(config):
    return OTAHandler(config)


def recording_logger():
    """收集日志调用，构造期发出的告警也要能拿到"""
    records = []

    def bind(**kw):
        def record(level):
            return lambda *a, **k: records.append((level, " ".join(str(x) for x in a)))

        return SimpleNamespace(
            info=record("info"),
            warning=record("warning"),
            error=record("error"),
            debug=record("debug"),
        )

    logger = SimpleNamespace(bind=bind)
    logger.records = records
    return logger


@contextmanager
def captured_warnings():
    """构造 handler 时把日志换成可读的记录"""
    logger = recording_logger()
    with patch("core.api.base_handler.setup_logging", return_value=logger):
        yield logger


def messages(logger, level=None):
    return [
        text
        for lvl, text in logger.records
        if level is None or lvl == level
    ]


class CIDict(dict):
    """模拟 websockets / aiohttp 的大小写不敏感 header"""

    def __init__(self, data=None):
        super().__init__()
        for k, v in (data or {}).items():
            super().__setitem__(k.lower(), v)

    def get(self, key, default=None):
        return super().get(key.lower(), default)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __contains__(self, key):
        return super().__contains__(key.lower())

    def items(self):
        return {k: v for k, v in super().items()}.items()


class FakeRequest:
    """够 ota_handler.handle_post 用的最小请求对象"""

    def __init__(self, headers=None, body="{}", match_info=None):
        self.headers = CIDict(headers or {})
        self._body = body
        self.match_info = match_info or {}
        self.method = "POST"

    async def text(self):
        return self._body


def fake_ws(headers, path="/xiaozhi/v1/"):
    return SimpleNamespace(
        request=SimpleNamespace(headers=CIDict(headers), path=path)
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def run_ws_auth(ws, headers, path="/xiaozhi/v1/"):
    """调 _handle_auth，通过返回 True，被拒抛 AuthenticationError"""
    try:
        asyncio.run(ws._handle_auth(fake_ws(headers, path)))
        return True
    except AuthenticationError:
        return False


def subprotocol_header(device_id, client_id, token=None):
    values = ["xiaozhi", f"d-{device_id.replace(':', '')}", f"c-{client_id}"]
    if token:
        values.insert(1, f"t-{token}")
    return {"Sec-WebSocket-Protocol": ", ".join(values)}


# ---------------------------------------------------------------- 1. 白名单


def test_allowed_mac_without_token_rejected():
    """1a. 白名单 MAC 且不自举 + 无 token → 拒绝"""
    ws = build_ws_server(
        build_config(enabled=True, allowed=[ALLOWED_MAC], allowed_devices_bootstrap=False)
    )
    ok = run_ws_auth(ws, {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID})
    assert not ok, "白名单设备无 token 也放行，等于认证旁路未关"
    print("OK: 白名单 MAC 无 token 被拒（自举关闭时）")


def test_allowed_mac_forged_client_id_rejected():
    """1b. 白名单 MAC + 伪造 Client-Id 的 token → 拒绝"""
    ws = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    forged = ws.auth.generate_token("attacker-client", ALLOWED_MAC)
    ok = run_ws_auth(
        ws,
        {
            "device-id": ALLOWED_MAC,
            "client-id": CLIENT_ID,
            "Authorization": f"Bearer {forged}",
        },
    )
    assert not ok, "用别的 Client-Id 签的 token 被接受，签名绑定失效"
    print("OK: 白名单 MAC + 伪造 Client-Id 的 token 被拒")


def test_allowed_mac_valid_token_accepted():
    """1c. 白名单 MAC + 合法 token → 通过"""
    ws = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    token = ws.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    ok = run_ws_auth(
        ws,
        {
            "device-id": ALLOWED_MAC,
            "client-id": CLIENT_ID,
            **bearer(token),
        },
    )
    assert ok, "白名单设备带合法 token 应放行"
    print("OK: 白名单 MAC + 合法 token 通过")


def test_non_allowed_mac_without_token_rejected():
    """1d. 白名单外 MAC + 无 token → 拒绝（基线行为不变）"""
    ws = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    ok = run_ws_auth(ws, {"device-id": OTHER_MAC, "client-id": CLIENT_ID})
    assert not ok, "白名单外设备无 token 被放行"
    print("OK: 白名单外 MAC + 无 token 被拒")


# ---------------------------------------------------- 2. 白名单自举与告警


def test_allowed_mac_bootstrap_once():
    """2a. 白名单设备首次免凭证换 token，第二次必须带凭证"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    headers = {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID}

    token, code = ota._issue_ws_token(FakeRequest(headers), CLIENT_ID, ALLOWED_MAC)
    assert token, "白名单设备首次 OTA 应能免凭证换到 token，否则升级即掉线"
    assert ota.auth.verify_token(token, CLIENT_ID, ALLOWED_MAC), "自举 token 应可用"

    again, _ = ota._issue_ws_token(FakeRequest(headers), CLIENT_ID, ALLOWED_MAC)
    assert again == "", "自举只能一次，第二次必须带凭证"

    renewed, _ = ota._issue_ws_token(
        FakeRequest({**headers, **bearer(token)}), CLIENT_ID, ALLOWED_MAC
    )
    assert renewed, "带上自举拿到的 token 应能续签"
    print("OK: 白名单设备免凭证自举一次，之后必须带凭证")


def test_bootstrap_disabled_blocks_whitelist():
    """2b. 关掉自举后白名单设备也没有免凭证入口"""
    ota = build_ota(
        build_config(
            enabled=True,
            allowed=[ALLOWED_MAC],
            allowed_devices_bootstrap=False,
            activation_codes=["boot-code"],
        )
    )
    headers = {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID}
    token, _ = ota._issue_ws_token(FakeRequest(headers), CLIENT_ID, ALLOWED_MAC)
    assert token == "", "自举关掉后白名单设备无凭证不应拿到 token"

    with_code, _ = ota._issue_ws_token(
        FakeRequest({**headers, **bearer("boot-code")}), CLIENT_ID, ALLOWED_MAC
    )
    assert with_code, "自举关掉后仍可用激活码换 token"
    print("OK: 关闭自举后白名单设备只能靠激活码换凭证")


def test_whitelist_without_any_bootstrap_warns():
    """2c. 白名单非空且无自举无激活码 → 启动告警说清后果"""
    with captured_warnings() as logger:
        build_ota(
            build_config(
                enabled=True,
                allowed=[ALLOWED_MAC],
                allowed_devices_bootstrap=False,
            )
        )
    warns = messages(logger, "warning")
    assert any("activation_codes" in w for w in warns), (
        f"缺少换凭证入口时应有告警，实际日志：{warns}"
    )
    print("OK: 白名单设备没有凭证来源时启动告警")


def test_whitelist_with_activation_code_does_not_warn():
    """2d. 有激活码兜底时不误报"""
    with captured_warnings() as logger:
        build_ota(
            build_config(
                enabled=True,
                allowed=[ALLOWED_MAC],
                allowed_devices_bootstrap=False,
                activation_codes=["boot-code"],
            )
        )
    assert not any("activation_codes" in w for w in messages(logger, "warning")), (
        "有激活码兜底时不该再报没有凭证来源"
    )
    print("OK: 有激活码兜底时不告警")


# ------------------------------------------------------------ 3. 激活码


def test_activation_code_bound_to_device():
    """3a. 绑定了设备的激活码不能给别的 MAC 用"""
    ota = build_ota(
        build_config(enabled=True, activation_codes=[f"bound-code: {ALLOWED_MAC}"])
    )
    wrong = ota._issue_ws_token(
        FakeRequest(
            {
                "device-id": "de:ad:be:ef:00:99",
                "client-id": CLIENT_ID,
                **bearer("bound-code"),
            }
        ),
        CLIENT_ID,
        "de:ad:be:ef:00:99",
    )
    assert wrong[0] == "", "绑定了 Device-Id 的码被无关设备换走了"

    right = ota._issue_ws_token(
        FakeRequest(
            {
                "device-id": ALLOWED_MAC,
                "client-id": CLIENT_ID,
                **bearer("bound-code"),
            }
        ),
        CLIENT_ID,
        ALLOWED_MAC,
    )
    assert right[0], "绑定的码应能给对应设备签发"
    print("OK: 激活码绑定 Device-Id 后不给无关设备用")


def test_bare_activation_code_still_works():
    """3b. 裸字符串激活码保持兼容"""
    ota = build_ota(build_config(enabled=True, activation_codes=["plain-code"]))
    token, code = ota._issue_ws_token(
        FakeRequest(
            {
                "device-id": OTHER_MAC,
                "client-id": CLIENT_ID,
                **bearer("plain-code"),
            }
        ),
        CLIENT_ID,
        OTHER_MAC,
    )
    assert token, "裸字符串激活码应继续可用"
    assert code == "plain-code", "应把待作废的码交回调用方"
    print("OK: 裸字符串激活码保持兼容")


def test_activation_code_parse():
    """3c. 解析规则"""
    codes = _parse_activation_codes(["a", "b: aa:bb:cc:dd:ee:ff", "  ", "c:  "])
    assert codes == {"a": None, "b": "aa:bb:cc:dd:ee:ff", "c": None}, codes
    print("OK: 激活码解析规则正确")


def test_activation_code_consumed_after_response():
    """3d. 端到端：响应组装成功后才作废激活码"""
    ota = build_ota(build_config(enabled=True, activation_codes=["e2e-code"]))
    headers = {
        "device-id": OTHER_MAC,
        "client-id": CLIENT_ID,
        **bearer("e2e-code"),
    }
    resp = asyncio.run(ota.handle_post(FakeRequest(headers)))
    assert resp.status == 200, f"激活码换 token 后应正常下发，实际 {resp.status}"
    assert "e2e-code" not in ota.activation_codes, "响应成功后激活码应已作废"

    resp2 = asyncio.run(ota.handle_post(FakeRequest(headers)))
    assert resp2.status == 401, "同一个码不能换第二次 token"
    print("OK: 激活码在响应组装成功后作废，且不可重复使用")


# ------------------------------------------------- 4. 有效期与吊销线归一化


def test_expire_seconds_normalized():
    """4a. 白名单有效期覆盖参数绕不过归一化"""
    ws = build_ws_server(
        build_config(
            enabled=True,
            allowed=[ALLOWED_MAC],
            allowed_devices_expire_seconds=0,
        )
    )
    assert ws.allowed_expire_seconds == 0, "配置原样保留，交给归一化"
    token = ws.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    # 配成 0 会被归一化回默认值，token 不会 1 秒就失效
    assert ws.auth.verify_token(
        token, CLIENT_ID, ALLOWED_MAC, expire_seconds=ws.allowed_expire_seconds
    ), "配成 0 的白名单有效期被当成了立即失效"
    print("OK: 白名单有效期配成 0 回落到默认值而非立即失效")


def test_expire_seconds_bad_type_falls_back():
    """4b. 有效期配成字符串不再被静默吞成验签失败"""
    auth = AuthManager(secret_key=SECRET, expire_seconds="3600")
    assert auth.expire_seconds == 3600, auth.expire_seconds
    token = auth.generate_token(CLIENT_ID, OTHER_MAC)
    assert auth.verify_token(token, CLIENT_ID, OTHER_MAC), (
        "数字字符串有效期应被正确采用，而不是让 token 全部验不过"
    )

    for junk in ("abc", None, -1, 0):
        fallback = AuthManager(secret_key=SECRET, expire_seconds=junk)
        assert fallback.expire_seconds == DEFAULT_EXPIRE_SECONDS, (
            f"{junk!r} 应回落到默认值，实际 {fallback.expire_seconds}"
        )
        assert fallback.verify_token(
            fallback.generate_token(CLIENT_ID, OTHER_MAC), CLIENT_ID, OTHER_MAC
        ), f"{junk!r} 回落后 token 仍应可用"

    capped = AuthManager(secret_key=SECRET, expire_seconds=999999999)
    assert capped.expire_seconds == MAX_EXPIRE_SECONDS, capped.expire_seconds
    print("OK: 有效期字符串正确采用，非法值回落默认，超大值截断到 90 天上限")


def test_issued_after_invalid_fails_fast():
    """4c. 吊销线配成未来时间或字符串 → 启动即报错，不静默 401"""
    for bad in (int(time.time()) + 3600, "not-a-number", -5):
        try:
            AuthManager(secret_key=SECRET, issued_after=bad)
        except ValueError:
            continue
        raise AssertionError(f"issued_after={bad!r} 应该启动报错，实际没报错")

    auth = AuthManager(secret_key=SECRET, issued_after=0)
    assert auth.verify_token(auth.generate_token(CLIENT_ID, OTHER_MAC), CLIENT_ID, OTHER_MAC)
    print("OK: issued_after 不合法时启动报错，合法时行为不变")


def test_issued_after_blocks_old_token():
    """4d. 吊销线之前的 token 一律拒"""
    line = int(time.time()) - 5
    auth = AuthManager(secret_key=SECRET, issued_after=line)
    old_ts = line - 5
    stale = f"{auth._sign(f'{CLIENT_ID}|{OTHER_MAC}|{old_ts}')}.{old_ts}"
    assert not auth.verify_token(stale, CLIENT_ID, OTHER_MAC), (
        "签发时刻早于吊销线的 token 应被拒"
    )
    fresh = auth.generate_token(CLIENT_ID, OTHER_MAC)
    assert auth.verify_token(fresh, CLIENT_ID, OTHER_MAC), "吊销线之后签发的应通过"
    print("OK: 吊销线之前的 token 被拒，之后的照常通过")


# ------------------------------------------------------- 5. Device-Id 门禁


def test_device_id_checked_only_for_mqtt():
    """5a. 不下发 MQTT 时不校验 Device-Id，未开认证的部署不被误伤"""
    ota = build_ota(build_config(enabled=False))
    resp = asyncio.run(
        ota.handle_post(
            FakeRequest({"device-id": "not-a-mac", "client-id": CLIENT_ID})
        )
    )
    assert resp.status == 200, f"不开 MQTT 时不该拦 Device-Id，实际 {resp.status}"
    print("OK: 不下发 MQTT 时不拦 Device-Id")


def test_invalid_device_id_rejected_for_mqtt():
    """5b. 下发 MQTT 时非法 Device-Id → 400"""
    ota = build_ota(build_config(enabled=False, _server={"mqtt_gateway": "1.2.3.4:1883"}))
    for evil in ("x/#", "aabbccddeeff/#", "x:y:z:1:2:3"):
        resp = asyncio.run(
            ota.handle_post(
                FakeRequest({"device-id": evil, "client-id": CLIENT_ID})
            )
        )
        assert resp.status == 400, f"{evil} 应被拒，实际 {resp.status}"
    print("OK: 下发 MQTT 时非法 Device-Id 被 400 拦下")


def test_device_id_newline_rejected():
    """5c. 两端接受范围一致：结尾带换行的 Device-Id 也要拒"""
    ota = build_ota(build_config(enabled=False))
    assert not ota._is_valid_device_id(ALLOWED_MAC + "\n"), (
        "$ 会放过结尾换行，与智控台的 String.matches 不一致"
    )
    assert ota._is_valid_device_id(ALLOWED_MAC)
    print("OK: Device-Id 结尾带换行被拒，与智控台一致")


def test_invalid_device_model_rejected():
    """5d. Device-Model 参与 MQTT 密码签名，必须限制字符集"""
    ota = build_ota(build_config(enabled=False, _server={"mqtt_gateway": "1.2.3.4:1883"}))
    resp = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID},
                body='{"board": {"type": "a@@@b"}}',
            )
        )
    )
    assert resp.status == 400, f"含分隔符的型号应被拒，实际 {resp.status}"

    ok = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID},
                body='{"board": {"type": "xiaozhi-esp32-s3"}}',
            )
        )
    )
    assert ok.status == 200, f"常规型号应放行，实际 {ok.status}"
    print("OK: Device-Model 按字符集校验")


# --------------------------------------------------------- 6. OTA 端到端


def test_handle_post_401_without_credential():
    """6a. 端到端：OTA 无凭证 → 401（非白名单设备）"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    resp = asyncio.run(
        ota.handle_post(
            FakeRequest({"device-id": OTHER_MAC, "client-id": CLIENT_ID})
        )
    )
    assert resp.status == 401, f"无凭证应 401，实际 {resp.status}"
    print("OK: OTA 无凭证 401")


def test_handle_post_400_invalid_device_id():
    """6b. 端到端：凭证有效但 Device-Id 非法且要下发 MQTT → 400"""
    ota = build_ota(
        build_config(enabled=True, _server={"mqtt_gateway": "1.2.3.4:1883"})
    )
    token = ota.auth.generate_token(CLIENT_ID, "not-a-mac")
    resp = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {
                    "device-id": "not-a-mac",
                    "client-id": CLIENT_ID,
                    **bearer(token),
                }
            )
        )
    )
    assert resp.status == 400, f"非法 Device-Id 应 400，实际 {resp.status}"
    print("OK: OTA 非法 Device-Id 返回 400")


def test_handle_post_renew_issues_token():
    """6c. 端到端：带旧 token 续签，下发非空 token"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    old = ota.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    resp = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {
                    "device-id": ALLOWED_MAC,
                    "client-id": CLIENT_ID,
                    **bearer(old),
                }
            )
        )
    )
    assert resp.status == 200, f"带合法 token 应 200，实际 {resp.status}"
    print("OK: OTA 持旧 token 续签正常")


def test_auth_disabled_unchanged():
    """6d. auth.enabled=false → 行为完全不变（直接放行、不签发）"""
    ws = build_ws_server(build_config(enabled=False, allowed=[ALLOWED_MAC]))
    ok = run_ws_auth(ws, {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID})
    assert ok, "认证关闭时应完全放行，与改动前一致"

    ota = build_ota(build_config(enabled=False))
    token, code = ota._issue_ws_token(
        FakeRequest({"device-id": ALLOWED_MAC, "client-id": CLIENT_ID}),
        CLIENT_ID,
        ALLOWED_MAC,
    )
    assert token == "", "认证关闭时 OTA 不应签发 token，与改动前一致"
    print("OK: auth.enabled=false 行为不变")


def test_empty_whitelist_unchanged():
    """6e. allowed_devices 为空 → 走 token 验证，用默认有效期"""
    ws = build_ws_server(build_config(enabled=True, allowed=[]))
    token = ws.auth.generate_token(CLIENT_ID, OTHER_MAC)
    ok = run_ws_auth(
        ws,
        {"device-id": OTHER_MAC, "client-id": CLIENT_ID, **bearer(token)},
    )
    assert ok, "白名单为空时合法 token 应通过"

    old_ts = int(time.time()) - 10
    stale = f"{ws.auth._sign(f'{CLIENT_ID}|{OTHER_MAC}|{old_ts}')}.{old_ts}"
    ws.auth.expire_seconds = 1
    assert not ws.auth.verify_token(stale, CLIENT_ID, OTHER_MAC), (
        "白名单为空时应按默认有效期校验过期"
    )
    print("OK: allowed_devices 为空走默认 token 校验")


def test_web_test_client_backdoor_removed():
    """6f. client_id == web_test_client → 拒绝"""
    handler = VisionHandler(build_config(enabled=True))
    ok, device_id = handler._verify_auth_token(
        FakeRequest({"Client-Id": "web_test_client", "Device-Id": "whatever"})
    )
    assert not ok, "web_test_client 仍能跳过认证"
    assert device_id is None, "被拒时不应回传 device_id"
    print("OK: web_test_client 后门已移除")


def test_download_requires_credential():
    """6g. 固件下载无凭证 → 401"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    resp = asyncio.run(
        ota.handle_post(FakeRequest({"device-id": OTHER_MAC, "client-id": CLIENT_ID}))
    )
    assert resp.status == 401

    token = ota.auth.generate_token(CLIENT_ID, OTHER_MAC)
    download = asyncio.run(
        ota.handle_download(
            FakeRequest(
                {
                    "device-id": OTHER_MAC,
                    "client-id": CLIENT_ID,
                    **bearer(token),
                },
                {"filename": "nonexistent.bin"},
            )
        )
    )
    assert download.status != 401, "带合法凭证不应被鉴权拦下"
    print("OK: 固件下载无凭证 401，带凭证放行到后续校验")


def test_handler_state_initialized():
    """6h. OTAHandler 构造后固件缓存相关属性必须就位"""
    ota = build_ota(build_config(enabled=True))
    for attr in ("bin_dir", "_bin_cache", "auth", "auth_enable"):
        assert hasattr(ota, attr), f"OTAHandler 缺少属性 {attr}"
    assert "files_by_model" in ota._bin_cache, "固件缓存结构不完整"
    print("OK: OTAHandler 状态初始化完整")


def test_ota_header_log_masks_token():
    """6i. OTA 请求头日志不打印凭证"""
    ota = build_ota(build_config(enabled=True, activation_codes=["secret-code"]))
    with captured_warnings() as logger:
        with patch.object(ota.logger, "bind") as bind:
            bind.side_effect = logger.bind
            asyncio.run(
                ota.handle_post(
                    FakeRequest(
                        {
                            "device-id": OTHER_MAC,
                            "client-id": CLIENT_ID,
                            **bearer("secret-code"),
                        }
                    )
                )
            )
    assert logger.records, "应有调试日志输出"
    for _level, text in logger.records:
        assert "secret-code" not in text, f"日志泄露了凭证：{text}"
        assert "Bearer secret-code" not in text, f"日志泄露了凭证：{text}"
    print("OK: OTA 请求头日志已脱敏")


# ------------------------------------------------------------ 7. 子协议


def test_subprotocol_carries_credential():
    """7a. 浏览器走子协议头也能认证通过

    子协议值不能带冒号，所以客户端要在发 OTA 时就用去分隔符的形态，
    两处保持同一个字符串，签名才对得上
    """
    device_hex = ALLOWED_MAC.replace(":", "")
    ws = build_ws_server(build_config(enabled=True, allowed=[device_hex]))
    token = ws.auth.generate_token(CLIENT_ID, device_hex)
    ok = run_ws_auth(ws, subprotocol_header(device_hex, CLIENT_ID, token))
    assert ok, "子协议头里的 token 应能通过认证"

    # 签名与上报的 Device-Id 不一致时仍要拒绝
    mismatched = ws.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    assert not run_ws_auth(
        ws, subprotocol_header(device_hex, CLIENT_ID, mismatched)
    ), "签名用的 Device-Id 与连接时上报的不一致却被接受"
    print("OK: 子协议头携带 token 可完成认证，身份绑定仍生效")


def test_query_string_not_trusted():
    """7b. URL 查询串里的凭证与身份不再被采信"""
    ws = build_ws_server(build_config(enabled=True))
    token = ws.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    ok = run_ws_auth(
        ws,
        {},
        path=(
            "/xiaozhi/v1/?authorization=Bearer%20"
            f"{token}&device-id={ALLOWED_MAC}&client-id={CLIENT_ID}"
        ),
    )
    assert not ok, "查询串里的凭证与设备标识不该再被采信"

    headers = ws._connection_headers(
        fake_ws({}, path=f"/xiaozhi/v1/?device-id={ALLOWED_MAC}")
    )
    assert "device-id" not in headers, "查询串里的 device-id 不该进入请求头"
    print("OK: 查询串里的凭证与设备标识不再被采信")


def test_subprotocol_parsing():
    """7c. 子协议头解析"""
    from core.websocket_server import _parse_subprotocol_headers, WS_SUBPROTOCOL

    parsed = _parse_subprotocol_headers(
        {"sec-websocket-protocol": "xiaozhi, t-tok3n, d-aabbccddeeff, c-abc-123"}
    )
    assert parsed == {
        "authorization": "Bearer tok3n",
        "device-id": "aabbccddeeff",
        "client-id": "abc-123",
    }, parsed

    ws = build_ws_server(build_config(enabled=True))
    assert ws._select_subprotocol(None, ["xiaozhi", "t-x"]) == WS_SUBPROTOCOL
    assert ws._select_subprotocol(None, ["other"]) is None
    print("OK: 子协议头解析与回显正确")


# ------------------------------------------------------------- 8. CORS


def _cors_headers_for(config, origin):
    ota = build_ota(config)
    from aiohttp import web

    resp = web.Response(text="x")
    ota._add_cors_headers(resp, FakeRequest({"Origin": origin}))
    return resp.headers


def test_cors_blocks_unknown_origin():
    """8a. 默认配置下任意来源都拿不到跨域头"""
    headers = _cors_headers_for(build_config(enabled=True), "https://evil.example")
    assert "Access-Control-Allow-Origin" not in headers, dict(headers)
    assert "Access-Control-Allow-Credentials" not in headers
    print("OK: 默认配置下陌生来源无跨域头")


def test_cors_wildcard_not_allowed():
    """8b. allowed_origins 配 * 也不回显"""
    headers = _cors_headers_for(
        build_config(enabled=True, cors={"allowed_origins": ["*"]}),
        "https://evil.example",
    )
    assert "Access-Control-Allow-Origin" not in headers, dict(headers)
    assert "Access-Control-Allow-Credentials" not in headers
    print("OK: allowed_origins 配 * 不放行任意来源")


def test_cors_allows_listed_origin():
    """8c. 名单内的来源正常放行"""
    allowed = "https://console.example"
    headers = _cors_headers_for(
        build_config(enabled=True, cors={"allowed_origins": [allowed]}), allowed
    )
    assert headers.get("Access-Control-Allow-Origin") == allowed, dict(headers)
    assert headers.get("Access-Control-Allow-Credentials") == "true"
    other = _cors_headers_for(
        build_config(enabled=True, cors={"allowed_origins": [allowed]}),
        "https://evil.example",
    )
    assert "Access-Control-Allow-Origin" not in other
    print("OK: 名单内来源放行、名单外拦截")


def test_cors_vary_always_written():
    """8d. 请求带了 Origin 就标 Vary，哪怕这次没放行"""
    blocked = _cors_headers_for(build_config(enabled=True), "https://evil.example")
    assert blocked.get("Vary") == "Origin", (
        f"陌生来源的响应也必须带 Vary，否则共享缓存会串味：{dict(blocked)}"
    )

    ota = build_ota(build_config(enabled=True))
    from aiohttp import web

    resp = web.Response(text="x")
    ota._add_cors_headers(resp, FakeRequest({}))
    assert "Vary" not in resp.headers, "请求没带 Origin 时不必写 Vary"
    print("OK: 带 Origin 的响应一律标 Vary")


def test_all_cors_call_sites_pass_request():
    """8e. 所有跨域头调用点都要传 request"""
    import re

    pattern = re.compile(r"_add_cors_headers\(\s*\w+\s*\)")
    offenders = []
    for rel in (
        "core/api/base_handler.py",
        "core/api/ota_handler.py",
        "core/api/vision_handler.py",
    ):
        with open(os.path.join(SERVER, rel), encoding="utf-8") as fh:
            for line in fh:
                if pattern.search(line):
                    offenders.append(f"{rel}: {line.strip()}")
    assert not offenders, f"这些调用点没传 request：{offenders}"
    print("OK: 所有跨域头调用点都传了 request")


# ------------------------------------------------- 9. 智控台配置合并


def test_config_loader_keeps_api_and_local_keys():
    """9. 智控台部署下 config_loader 逐键合并，不吞掉接口与本地字段"""
    import config.config_loader as loader

    api_payload = {
        "server": {
            "ip": "10.0.0.5",
            "secret": "server-secret",
            "auth": {"enabled": True, "allowed_devices": ["aa:bb:cc:dd:ee:ff"]},
        },
        "prompt_template": "{}",
    }
    custom = {
        "manager-api": {"url": "http://console", "secret": "msecret"},
        "server": {"cors": {"allowed_origins": ["null"]}},
    }

    async def fake_get_server_config():
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in api_payload.items()}

    with patch.object(loader, "init_service"), patch.object(
        loader, "get_server_config", fake_get_server_config
    ):
        merged = asyncio.run(loader.get_config_from_api_async(custom))

    server = merged["server"]
    assert server["auth"]["enabled"] is True, "认证开关应来自智控台"
    assert server["auth"]["allowed_devices"] == ["aa:bb:cc:dd:ee:ff"], (
        f"接口返回的 allowed_devices 被吞了：{server['auth']}"
    )
    assert server["cors"] == {"allowed_origins": ["null"]}, (
        f"本地配的 cors 被吞了：{server}"
    )
    assert server["ip"] == "10.0.0.5", f"接口返回的字段不该被默认值覆盖：{server}"
    assert server["secret"] == "server-secret", server
    assert merged["read_config_from_api"] is True
    print("OK: 智控台部署下 server 字段逐键合并不丢失")


def main() -> int:
    test_allowed_mac_without_token_rejected()
    test_allowed_mac_forged_client_id_rejected()
    test_allowed_mac_valid_token_accepted()
    test_non_allowed_mac_without_token_rejected()
    test_allowed_mac_bootstrap_once()
    test_bootstrap_disabled_blocks_whitelist()
    test_whitelist_without_any_bootstrap_warns()
    test_whitelist_with_activation_code_does_not_warn()
    test_activation_code_bound_to_device()
    test_bare_activation_code_still_works()
    test_activation_code_parse()
    test_activation_code_consumed_after_response()
    test_expire_seconds_normalized()
    test_expire_seconds_bad_type_falls_back()
    test_issued_after_invalid_fails_fast()
    test_issued_after_blocks_old_token()
    test_device_id_checked_only_for_mqtt()
    test_invalid_device_id_rejected_for_mqtt()
    test_device_id_newline_rejected()
    test_invalid_device_model_rejected()
    test_handle_post_401_without_credential()
    test_handle_post_400_invalid_device_id()
    test_handle_post_renew_issues_token()
    test_auth_disabled_unchanged()
    test_empty_whitelist_unchanged()
    test_web_test_client_backdoor_removed()
    test_download_requires_credential()
    test_handler_state_initialized()
    test_ota_header_log_masks_token()
    test_subprotocol_carries_credential()
    test_query_string_not_trusted()
    test_subprotocol_parsing()
    test_cors_blocks_unknown_origin()
    test_cors_wildcard_not_allowed()
    test_cors_allows_listed_origin()
    test_cors_vary_always_written()
    test_all_cors_call_sites_pass_request()
    test_config_loader_keeps_api_and_local_keys()
    print("\nALL PASS: 3448 认证旁路已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main())