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
import json
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

    def record(level):
        return lambda *a, **k: records.append((level, " ".join(str(x) for x in a)))

    def bind(**kw):
        return SimpleNamespace(
            info=record("info"),
            warning=record("warning"),
            error=record("error"),
            debug=record("debug"),
        )

    # 顶层也挂上各级方法：core.auth 是模块级 logger.warning(...)，
    # 不走 bind，不挂的话 patch 上去的对象调不到就报 AttributeError
    logger = SimpleNamespace(
        bind=bind,
        info=record("info"),
        warning=record("warning"),
        error=record("error"),
        debug=record("debug"),
    )
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
    """4c. 吊销线配成字符串或负数 → 启动即报错，不静默 401

    未来时间戳不在这一类里：它降级成警告并截到当前，见 test_issued_after_future_timestamp_degrades。
    """
    for bad in ("not-a-number", -5):
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

    with patch.object(loader, "read_config", return_value=custom), patch.object(
        loader, "get_project_dir", return_value="/tmp/"
    ), patch.object(loader, "init_service"), patch.object(
        loader, "get_server_config", fake_get_server_config
    ):
        merged = asyncio.run(loader.get_config_from_api_async())

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


# ------------------------------------------------- 10. round 2：8 条 P1 的接缝


def test_subprotocol_reaches_session_layer():
    """10a. 子协议合并结果必须落到 ConnectionHandler 读的那份 request.headers 上

    之前 _connection_headers 只把合并结果交给 _handle_auth，
    ConnectionHandler 又从头读了一遍 dict(ws.request.headers)，
    结果浏览器连接认证过了但会话里没有 device-id，页面一直提示要绑定。
    """
    import inspect

    from core.connection import ConnectionHandler

    ws_server = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    token = ws_server.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    ws = fake_ws(subprotocol_header(ALLOWED_MAC, CLIENT_ID, token))

    ws_server._connection_headers(ws)

    # ConnectionHandler.handle_connection 就是这么读的（connection.py）
    session_headers = dict(ws.request.headers)
    assert session_headers.get("device-id"), (
        "子协议里的 device-id 没落到 request.headers，会话拿不到设备标识"
    )
    assert session_headers.get("client-id") == CLIENT_ID, session_headers
    assert session_headers.get("authorization", "").startswith("Bearer "), (
        f"子协议里的 token 没落到 request.headers：{session_headers}"
    )

    # 兜住"ConnectionHandler 改成从别处取"——只测合并函数会漏掉这一半
    source = inspect.getsource(ConnectionHandler.handle_connection)
    assert "ws.request.headers" in source, (
        "ConnectionHandler 不再从 ws.request.headers 取，合并结果可能落不到会话层，"
        "请同步改 websocket_server._connection_headers 并更新本用例"
    )
    print("OK: 子协议凭证一路传到会话层")


def test_mqtt_branch_returns_token():
    """10b. MQTT 分支的响应体里必须带 token，且额度消耗与响应一致"""
    config = build_config(
        enabled=True,
        allowed=[ALLOWED_MAC],
        _server={"mqtt_gateway": "1.2.3.4:1883", "mqtt_signature_key": "sig-key"},
    )
    ota = build_ota(config)
    request = FakeRequest({"device-id": ALLOWED_MAC, "client-id": CLIENT_ID})

    resp = asyncio.run(ota.handle_post(request))
    assert resp.status == 200, f"白名单自举应 200，实际 {resp.status}"
    body = json.loads(resp.text)
    assert body.get("mqtt"), f"应下发 MQTT 配置：{body}"
    token = body["mqtt"].get("token")
    assert token, (
        f"MQTT 分支没带 token，激活码与自举名额却已经消耗掉了：{body['mqtt']}"
    )

    # 额度与响应一致：同一台设备不带凭证再来一次，必须被拒
    again = asyncio.run(
        ota.handle_post(FakeRequest({"device-id": ALLOWED_MAC, "client-id": CLIENT_ID}))
    )
    assert again.status == 401, (
        f"第一次给了 token 却消耗了额度，第二次应 401，实际 {again.status}"
    )

    # 拿这个 token 能换到下一次，不至于只能连一次
    renewed = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID, **bearer(token)}
            )
        )
    )
    assert renewed.status == 200, f"MQTT 分支下发的 token 应可续签，实际 {renewed.status}"
    print("OK: MQTT 分支下发 token，额度消耗与响应一致")


def test_activation_code_returns_token_on_mqtt_branch():
    """10c. 激活码绑定的 MQTT 设备也要拿到 token，否则码白烧"""
    config = build_config(
        enabled=True,
        activation_codes=[f"mqtt-code: {ALLOWED_MAC}"],
        _server={"mqtt_gateway": "1.2.3.4:1883", "mqtt_signature_key": "sig-key"},
    )
    ota = build_ota(config)

    resp = asyncio.run(
        ota.handle_post(
            FakeRequest(
                {
                    "device-id": ALLOWED_MAC,
                    "client-id": CLIENT_ID,
                    **bearer("mqtt-code"),
                }
            )
        )
    )
    assert resp.status == 200, f"激活码应 200，实际 {resp.status}"
    body = json.loads(resp.text)
    assert body["mqtt"].get("token"), f"激活码用掉却没下发 token：{body['mqtt']}"
    print("OK: 激活码在 MQTT 分支也能换到 token")


def test_whitelist_normalized_and_bootstrap_for_any_spelling():
    """10d. 白名单按归一值比较：分隔符和大小写不同都该认同一台设备

    websocket 侧认不认白名单只体现在 token 有效期上，
    所以用"短有效期签发 + 白名单放长"来区分：认出来就过，认不出就过期。
    """
    from core.auth import normalize_device_id

    for form in (
        "aa:bb:cc:dd:ee:ff",
        "AA:BB:CC:DD:EE:FF",
        "aa-bb-cc-dd-ee-ff",
        "aabbccddeeff",
        "AA_BB_CC_DD_EE_FF",
    ):
        config = build_config(
            enabled=True,
            allowed=["AA-BB-CC-DD-EE-FF"],
            allowed_devices_expire_seconds=7200,
        )
        ws_server = build_ws_server(config)
        assert ws_server.allowed_devices == {"aabbccddeeff"}, (
            f"加载时没归一：{ws_server.allowed_devices}"
        )

        # 造一个 10 秒前就签发的 token：白名单不认它就只有默认有效期，会过期
        stale_ts = int(time.time()) - 10
        content = f"{CLIENT_ID}|{form}|{stale_ts}"
        signature = ws_server.auth._sign(content)
        token = f"{signature}.{stale_ts}"

        ok = run_ws_auth(
            ws_server,
            {"device-id": form, "client-id": CLIENT_ID, **bearer(token)},
        )
        assert ok, (
            f"白名单写法 {form} 没认出来（归一值 {normalize_device_id(form)}），"
            "会让这台设备的 token 拿到默认有效期"
        )

    # OTA 侧的白名单同样按归一值比较
    ota = build_ota(build_config(enabled=True, allowed=["AA-BB-CC-DD-EE-FF"]))
    assert ota.allowed_devices == {"aabbccddeeff"}, ota.allowed_devices
    print("OK: 白名单认得各种分隔符与大小写写法")


def test_list_config_rejects_scalar_string():
    """10e. allowed_devices / activation_codes 配成字符串必须报错，不能逐字符拆"""
    # allowed_devices 两边都读，activation_codes 只有 OTA 读，按各自加载的那一侧触发
    for key, bad, load in (
        ("allowed_devices", "aa:bb:cc:dd:ee:ff", build_ws_server),
        ("activation_codes", "SecretCode1", build_ota),
    ):
        config = build_config(enabled=True)
        config["server"]["auth"][key] = bad
        try:
            load(config)
            raise AssertionError(f"server.auth.{key} 配成字符串应报错")
        except ValueError:
            pass
    print("OK: 列表型配置配成字符串时报错")


def test_issued_after_future_timestamp_degrades():
    """10f. 填未来的吊销时刻只警告并截到当前，不该让整个进程起不来"""
    from core.auth import normalize_issued_after

    future = int(time.time()) + 60
    logger = recording_logger()
    with patch("core.auth.logger", logger):
        clamped = normalize_issued_after(future)
    assert clamped <= int(time.time()), f"未来时刻应截到当前，实际 {clamped}"
    warned = " ".join(messages(logger, "warning"))
    assert "issued_after" in warned, f"截断了却没提示：{warned}"

    # 能构造出来，WebSocket / OTA / 视觉接口才不会一起没
    with patch("core.auth.logger", logger):
        manager = AuthManager(secret_key=SECRET, issued_after=future)
    assert manager.issued_after <= int(time.time())

    # 非整数与负数仍然是配错，该报错
    for bad in ("abc", -1):
        try:
            normalize_issued_after(bad)
            raise AssertionError(f"issued_after={bad!r} 应报错")
        except ValueError:
            pass
    print("OK: 未来吊销时刻降级为警告，填错仍报错")


def test_reload_order_keeps_config_intact_on_bad_auth():
    """10g. 换配置时先校验认证段：配错不能留下"配置换了一半、模块不再重建"的状态

    走真的 update_config()：只直接调 _load_auth_config 的话，这条用例自己就断言了
    "self.config 没被换"，可被测代码根本没走到赋值那一步，怎么改都能过。
    真正要验的是校验抛错后 self.config 仍指向老对象、且模块没有重建过。
    """
    import config.config_loader as loader
    import core.websocket_server as ws_mod

    ws_server = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    ws_server.config_lock = asyncio.Lock()
    before = ws_server.config

    # 接口真的返回了配错的 auth 段：allowed_devices 是标量字符串，set() 会逐字符拆开
    broken = {
        "selected_module": [],
        "server": {
            "ip": "10.0.0.9",
            "auth": {"enabled": True, "allowed_devices": "aa:bb:cc:dd:ee:ff"},
        },
    }
    # 模块重建是这条用例真正盯的副作用，校验没过就不该被触发
    rebuilt = []
    fake_modules = lambda *a, **k: (rebuilt.append(a[2]) or {})

    async def fake_get_server_config():
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in broken.items()}

    with patch.object(loader, "read_config", return_value={}), patch.object(
        loader, "get_project_dir", return_value="/tmp/"
    ), patch.object(loader, "init_service"), patch.object(
        loader, "get_server_config", fake_get_server_config
    ), patch.object(
        ws_mod, "initialize_modules", fake_modules
    ), patch.object(
        ws_mod, "check_vad_update", return_value=False
    ), patch.object(
        ws_mod, "check_asr_update", return_value=False
    ):
        ok = asyncio.run(ws_server.update_config())

    assert ok is False, "认证段配错时 update_config 应返回失败"
    assert ws_server.config is before, (
        f"校验没过 self.config 就被换掉了：{ws_server.config['server']}"
    )
    assert rebuilt == [], f"校验没过还重建了模块：{rebuilt}"
    print("OK: 认证段校验失败时配置保持原样")


def test_config_loader_merges_local_auth_keys():
    """10h. 全模块部署下本地配的四个认证项必须逐键并进去"""
    import config.config_loader as loader

    api_payload = {"server": {"ip": "10.0.0.5", "auth": {"enabled": True}}}
    local = {
        "manager-api": {"url": "http://console", "secret": "msecret"},
        "server": {
            "auth": {
                "allowed_devices": ["aa:bb:cc:dd:ee:ff"],
                "activation_codes": ["local-code"],
                "issued_after": 1700000000,
                "expire_seconds": 3600,
            }
        },
    }

    async def fake_get_server_config():
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in api_payload.items()}

    with patch.object(loader, "read_config", return_value=local), patch.object(
        loader, "get_project_dir", return_value="/tmp/"
    ), patch.object(loader, "init_service"), patch.object(
        loader, "get_server_config", fake_get_server_config
    ):
        merged = asyncio.run(loader.get_config_from_api_async())

    auth = merged["server"]["auth"]
    assert auth["enabled"] is True, "认证开关应来自智控台"
    for key, want in (
        ("allowed_devices", ["aa:bb:cc:dd:ee:ff"]),
        ("activation_codes", ["local-code"]),
        ("issued_after", 1700000000),
        ("expire_seconds", 3600),
    ):
        assert auth.get(key) == want, f"本地配的 {key} 没生效：{auth}"
    assert merged["server"]["ip"] == "10.0.0.5", "接口返回的字段不该被吞"
    print("OK: 全模块部署下本地四个认证项都并进去了")


def test_update_config_keeps_local_auth_keys():
    """10i. 走完 update_config()，本地四个认证项在 self.config 里仍然是本地配的值

    这条断言覆盖整条链：本地配置 → get_config_from_api_async → 合并 → 赋回 self.config。
    只测 get_config_from_api_async() 挡不住"入参传错"——传 self.config 或只传 server 段
    都不报错，但四个键会悄悄变回空。
    """
    import config.config_loader as loader
    import core.websocket_server as ws_mod

    ws_server = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    ws_server.config_lock = asyncio.Lock()

    local = {
        "manager-api": {"url": "http://console", "secret": "msecret"},
        "server": {
            "auth": {
                "allowed_devices": ["aa:bb:cc:dd:ee:ff"],
                "activation_codes": ["local-code"],
                "issued_after": 1700000000,
                "expire_seconds": 3600,
            }
        },
    }
    api_payload = {
        "selected_module": [],
        "server": {"ip": "10.0.0.9", "auth": {"enabled": True}},
    }
    # 刷新前就签好的 token：auth_key 只在启动时算一次，刷新配置不能把它换掉，
    # 换了等于给所有在线设备换了一把密钥，token 集体作废
    old_token = ws_server.auth.generate_token(CLIENT_ID, ALLOWED_MAC)

    async def fake_get_server_config():
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in api_payload.items()}

    with patch.object(loader, "read_config", return_value=local), patch.object(
        loader, "get_project_dir", return_value="/tmp/"
    ), patch.object(loader, "init_service"), patch.object(
        loader, "get_server_config", fake_get_server_config
    ), patch.object(
        ws_mod, "initialize_modules", return_value={}
    ), patch.object(
        ws_mod, "check_vad_update", return_value=False
    ), patch.object(
        ws_mod, "check_asr_update", return_value=False
    ):
        ok = asyncio.run(ws_server.update_config())
    assert ok, f"update_config 应成功：{messages(ws_server.logger, 'error')}"

    auth = ws_server.config["server"]["auth"]
    for key, want in (
        ("allowed_devices", ["aa:bb:cc:dd:ee:ff"]),
        ("activation_codes", ["local-code"]),
        ("issued_after", 1700000000),
        ("expire_seconds", 3600),
    ):
        assert auth.get(key) == want, (
            f"刷新配置后本地的 {key} 没了，说明入参传的是上次合并结果：{auth}"
        )
    assert ws_server.config["server"]["ip"] == "10.0.0.9", "接口返回的字段应生效"
    assert ws_server.config["server"]["auth_key"] == SECRET, "auth_key 被刷新掉了"
    assert ws_server.auth.verify_token(
        old_token, client_id=CLIENT_ID, username=ALLOWED_MAC
    ), "刷新配置让刷新前签的 token 失效了，等于给在线设备全换了一把密钥"
    print("OK: update_config 刷新后本地认证项与接口字段都在")


def test_cors_empty_warn_reports_blocked_origin():
    """10j. 名单为空时跨域被拦，服务端要留信号，否则只有浏览器那头知道"""
    with captured_warnings() as logger:
        handler = VisionHandler(build_config(enabled=True, cors={"allowed_origins": []}))
        response = _cors_headers_for(handler.config, "http://127.0.0.1:8006")
        assert "Access-Control-Allow-Origin" not in response, "空名单不该放行"

    warned = " ".join(messages(logger, "warning"))
    assert "allowed_origins" in warned, f"被拦下却没留服务端信号：{warned}"
    assert "127.0.0.1:8006" in warned, f"告警里应点名是哪个来源被拦：{warned}"
    print("OK: 名单为空时服务端会点名被拦的来源")


def test_tester_page_covers_both_localhost_spellings():
    """10k. 测试页的两种打开方式都要在文档里写清，两个 origin 不是一回事"""
    import re

    readme = open(
        os.path.join(REPO, "main", "digital-human", "README.md"), encoding="utf-8"
    ).read()
    for origin in ("http://127.0.0.1:8006", "http://localhost:8006"):
        assert origin in readme, f"README 没写 {origin}，按这种地址打开会连不上"
    assert "file://" in readme, "README 应说明用 file:// 打开没意义"

    config_yaml = open(
        os.path.join(SERVER, "config.yaml"), encoding="utf-8"
    ).read()
    # 说明写在 cors: 上方的注释里，正则得连注释一起框进来
    block = re.search(
        r"(?:^[ \t]*#.*\n)+^[ \t]*cors:\s*\n\s*allowed_origins:[^\n]*",
        config_yaml,
        re.M,
    )
    assert block, "config.yaml 里找不到 cors 配置"
    comment = block.group(0)
    assert "127.0.0.1:8006" in comment and "localhost:8006" in comment, (
        "config.yaml 注释要同时写两个来源，只写一个按另一种方式打开照样不通"
    )
    assert '"null"' not in comment, (
        '不该再引导填 "null"：页面检测到 file:// 会自己弹窗挡住，origin 不会是 null'
    )
    print("OK: 文档写清了测试页的两种来源")


TESTER_JS = os.path.join(REPO, "main", "digital-human", "js")
TESTER_JS_FILES = (
    "utils/logger.js",
    "config/manager.js",
    "core/network/ota-connector.js",
)

# 在 node 里真跑一遍测试页的连接流程：填激活码 → 连接 → 刷新 → 再连。
# 只跑 ota-connector 和 manager 这两个模块，其余依赖靠下面的桩顶掉。
TESTER_DRIVER = r"""
function makeStorage() {
    const m = new Map();
    return {
        getItem: k => (m.has(k) ? m.get(k) : null),
        setItem: (k, v) => m.set(k, String(v)),
        removeItem: k => m.delete(k),
        _dump: () => Object.fromEntries(m),
    };
}
globalThis.sessionStorage = makeStorage();
globalThis.localStorage = makeStorage();
globalThis.window = { location: { origin: 'http://127.0.0.1:8006' } };

const inputs = {
    deviceMac: { value: '' },
    deviceName: { value: '' },
    clientId: { value: '' },
    otaUrl: { value: 'http://127.0.0.1:8002/ota/' },
    wakewordWsUrl: { value: '' },
    wakewordEnabled: { value: 'true' },
    wakewordList: { value: '' },
    emojiEnabled: { value: 'true' },
    activationCode: { value: '' },
    serverUrl: { value: '' },
};
globalThis.document = { getElementById: id => inputs[id] || null };

const calls = [];
let issued = process.env.ISSUED_FIRST;
globalThis.fetch = async (url, opts) => {
    calls.push({ url, headers: opts.headers, body: JSON.parse(opts.body) });
    return {
        ok: true, status: 200, statusText: 'OK',
        json: async () => ({ websocket: { url: 'ws://127.0.0.1:8000/', token: issued } }),
    };
};
class FakeWebSocket {
    constructor(url, protocols) {
        this.url = url;
        this.protocols = protocols;
        FakeWebSocket.last = this;
    }
}
globalThis.WebSocket = FakeWebSocket;

const { webSocketConnect } = await import('./js/core/network/ota-connector.js');
const { loadConfig, saveConfig, getConfig } = await import('./js/config/manager.js');

const mac = process.env.TESTER_MAC;
loadConfig();
inputs.deviceMac.value = mac;
inputs.deviceName.value = '测试机';
inputs.clientId.value = 'client-1';
inputs.activationCode.value = process.env.ACTIVATION_CODE;
saveConfig();

// 页面上点连接按钮之前会再 loadConfig 一次，走的是同一条读回路径
loadConfig();
await webSocketConnect('http://127.0.0.1:8002/ota/', getConfig());
const first = {
    call: calls[calls.length - 1],
    session: sessionStorage._dump(),
    local: localStorage._dump(),
};

// 刷新页面：server 端激活码已作废，只有 token 能续签
issued = process.env.ISSUED_SECOND;
loadConfig();
await webSocketConnect('http://127.0.0.1:8002/ota/', getConfig());
const second = {
    call: calls[calls.length - 1],
    session: sessionStorage._dump(),
    local: localStorage._dump(),
    protocols: FakeWebSocket.last.protocols,
};

// logger 会往 stdout 写行，JSON 用标记包起来单独取
process.stdout.write('<<<JSON' + JSON.stringify({ first, second, mac }) + '\n');
"""


def run_tester_page(mac: str, activation_code: str, issued_first: str, issued_second: str) -> dict:
    """在 node 里跑一遍测试页的连接流程，返回实际发出去的请求和落库的凭证"""
    import re
    import shutil
    import subprocess
    import tempfile

    work = tempfile.mkdtemp(prefix="check_auth_3448_js_")
    try:
        # node 按 ESM 加载，import 上的 ?v=0205 是浏览器缓存标记，磁盘上不存在这个文件
        for rel in TESTER_JS_FILES:
            dest = os.path.join(work, "js", rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(os.path.join(TESTER_JS, rel), encoding="utf-8") as fh:
                body = re.sub(r"(\.js)\?v=\d+", r"\1", fh.read())
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(body)

        driver = os.path.join(work, "driver.mjs")
        with open(driver, "w", encoding="utf-8") as fh:
            fh.write(TESTER_DRIVER)

        env = dict(
            os.environ,
            TESTER_MAC=mac,
            ACTIVATION_CODE=activation_code,
            ISSUED_FIRST=issued_first,
            ISSUED_SECOND=issued_second,
        )
        proc = subprocess.run(
            ["node", driver], capture_output=True, text=True, env=env, timeout=120
        )
        assert proc.returncode == 0, f"node 跑测试页失败：{proc.stderr[-2000:]}"
        payload = [
            line for line in proc.stdout.splitlines() if line.startswith("<<<JSON")
        ]
        assert payload, f"node 没吐出结果：{proc.stdout[-2000:]}"
        return json.loads(payload[0][len("<<<JSON") :])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_tester_page_reuses_token():
    """10l. 测试页拿到 token 要存下来复用，激活码用一次就作废

    真在 node 里跑页面那条连接链，看实际发出去的 Authorization 和落库的凭证。
    原来是 grep 子串，只能证明代码里出现过这几个词，证明不了第二次连用的是 token。
    """
    out = run_tester_page(
        mac="AA:BB:CC:DD:EE:FF",
        activation_code="CODE-1",
        issued_first="TOKEN-1",
        issued_second="TOKEN-2",
    )
    first, second = out["first"], out["second"]

    assert first["call"]["headers"].get("Authorization") == "Bearer CODE-1", (
        f"首次应拿激活码换 token：{first['call']['headers']}"
    )
    assert first["session"].get("xz_tester_token") == "TOKEN-1", (
        f"下发的 token 没存进 sessionStorage：{first['session']}"
    )
    assert first["local"].get("xz_tester_token") == "TOKEN-1", (
        f"刷新页面就没了，token 得存进 localStorage：{first['local']}"
    )
    assert second["call"]["headers"].get("Authorization") == "Bearer TOKEN-1", (
        f"刷新后应拿上次的 token 续签，不是作废的激活码：{second['call']['headers']}"
    )
    assert second["session"].get("xz_tester_token") == "TOKEN-2", (
        f"续签换的新 token 应覆盖旧的：{second['session']}"
    )
    assert "t-TOKEN-2" in second["protocols"], (
        f"凭证要靠子协议带给 websocket 连接：{second['protocols']}"
    )
    print("OK: 测试页会复用 token，激活码也读得回来")


def test_tester_page_sends_normalized_device_id():
    """10m. 大写 MAC 要发出小写去分隔符的 Device-Id，且与子协议头一致

    测试页自己生成的随机 MAC 就是大写。这里曾写成 /[:-_]/g，那是 : 到 _ 的字符区间，
    连大写 A-Z 一起吃掉，大写 MAC 算出来是空串。服务端只收 d- 后面非空的值，
    空的话连接直接被判成"端口探测"关掉，测试页连都连不上。
    """
    out = run_tester_page(
        mac="AA:BB:CC:DD:EE:FF",
        activation_code="CODE-1",
        issued_first="TOKEN-1",
        issued_second="TOKEN-2",
    )
    want = "aabbccddeeff"
    for phase in ("first", "second"):
        got = out[phase]["call"]["headers"].get("Device-Id")
        assert got == want, f"{phase} 的 Device-Id 应是 {want}，实际 {got!r}"
    assert f"d-{want}" in out["second"]["protocols"], (
        f"子协议头和请求头得是同一个值，否则 token 签名对不上：{out['second']['protocols']}"
    )
    print("OK: 大写 MAC 归一后才发出去，两处一致")


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
    test_subprotocol_reaches_session_layer()
    test_mqtt_branch_returns_token()
    test_activation_code_returns_token_on_mqtt_branch()
    test_whitelist_normalized_and_bootstrap_for_any_spelling()
    test_list_config_rejects_scalar_string()
    test_issued_after_future_timestamp_degrades()
    test_reload_order_keeps_config_intact_on_bad_auth()
    test_config_loader_merges_local_auth_keys()
    test_update_config_keeps_local_auth_keys()
    test_cors_empty_warn_reports_blocked_origin()
    test_tester_page_covers_both_localhost_spellings()
    test_tester_page_reuses_token()
    test_tester_page_sends_normalized_device_id()
    print("\nALL PASS: 3448 认证旁路已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main())