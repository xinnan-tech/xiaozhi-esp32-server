"""issue 3448 设备认证旁路回归测试。

覆盖 6 条旁路：
  1. websocket 白名单免 token → 白名单只延长有效期，仍校验 token
  2. OTA 匿名签发 token → 改为旧 token 续签 / 一次性激活码首次绑定
  3. vision web_test_client 硬编码后门 → 删除
  4. MQTT 分支不受 auth_enable 约束 + topic 注入 → 纳入门禁 + Device-Id 格式校验
  5. OTA 固件下载无鉴权 → 需带凭证

Usage:
    python benchmark/check_auth_3448.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)

from core.auth import AuthenticationError  # noqa: E402
from core.api.ota_handler import OTAHandler  # noqa: E402
from core.api.vision_handler import VisionHandler  # noqa: E402

SECRET = "test-auth-key-for-3448"
ALLOWED_MAC = "aa:bb:cc:dd:ee:ff"
OTHER_MAC = "11:22:33:44:55:66"
CLIENT_ID = "7b94d69a-9808-4c59-9c9b-704333b38aff"


def build_config(enabled=True, allowed=None, **extra):
    auth = {"enabled": enabled, "allowed_devices": allowed or []}
    auth.update(extra)
    return {"server": {"auth": auth, "auth_key": SECRET}}


def build_ws_server(config):
    """绕开 WebSocketServer.__init__ 的模块初始化，只加载认证属性"""
    from core.websocket_server import WebSocketServer

    ws = WebSocketServer.__new__(WebSocketServer)
    ws.config = config
    ws.logger = SimpleNamespace(bind=lambda **kw: SimpleNamespace(
        info=lambda *a, **k: None, warning=lambda *a, **k: None,
        error=lambda *a, **k: None, debug=lambda *a, **k: None,
    ))
    ws._load_auth_config(config)
    return ws


def build_ota(config):
    return OTAHandler(config)


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


def fake_ws(headers):
    return SimpleNamespace(request=SimpleNamespace(headers=CIDict(headers)))


def fake_request(headers, match_info=None):
    return SimpleNamespace(headers=CIDict(headers), match_info=match_info or {})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def run_ws_auth(ws, headers):
    """调 _handle_auth，通过返回 True，被拒抛 AuthenticationError"""
    try:
        asyncio.run(ws._handle_auth(fake_ws(headers)))
        return True
    except AuthenticationError:
        return False


def test_allowed_mac_without_token_rejected():
    """1. 白名单 MAC + 无 token → 拒绝"""
    ws = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    ok = run_ws_auth(
        ws,
        {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID},
    )
    assert not ok, "白名单设备无 token 也放行，等于认证旁路未关"
    print("OK: 白名单 MAC 无 token 被拒")


def test_allowed_mac_forged_client_id_rejected():
    """2. 白名单 MAC + 伪造 Client-Id → 拒绝"""
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
    """3. 白名单 MAC + 合法 token → 通过"""
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
    """4. 白名单外 MAC + 无 token → 拒绝（基线行为不变）"""
    ws = build_ws_server(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    ok = run_ws_auth(ws, {"device-id": OTHER_MAC, "client-id": CLIENT_ID})
    assert not ok, "白名单外设备无 token 被放行"
    print("OK: 白名单外 MAC 无 token 被拒")


def test_ota_allowed_mac_gets_token_on_renew():
    """5. OTA 白名单 MAC 续签 → 下发非空 token"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    old = ota.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    new = ota._issue_ws_token(
        fake_request(
            {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID, **bearer(old)}
        ),
        CLIENT_ID,
        ALLOWED_MAC,
    )
    assert new, "白名单设备持旧 token 续签应拿到新 token"
    assert ota.auth.verify_token(new, CLIENT_ID, ALLOWED_MAC), "下发的 token 应可用"
    print("OK: OTA 白名单 MAC 续签拿到非空 token")


def test_ota_without_credential_rejected():
    """6. OTA 无任何凭证 → 拒绝签发"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    for headers in (
        {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID},
        {
            "device-id": ALLOWED_MAC,
            "client-id": CLIENT_ID,
            **bearer("totally-made-up-token"),
        },
    ):
        got = ota._issue_ws_token(fake_request(headers), CLIENT_ID, ALLOWED_MAC)
        assert got == "", f"无有效凭证不应签发 token，实际 {got!r}"
    print("OK: OTA 无凭证 / 无效 token 均不签发")


def test_ota_activation_code_first_binding():
    """7. OTA 一次性激活码 → 首次绑定签发，用后即失效"""
    ota = build_ota(
        build_config(enabled=True, activation_codes=["one-shot-code"])
    )
    headers = {
        "device-id": ALLOWED_MAC,
        "client-id": CLIENT_ID,
        **bearer("one-shot-code"),
    }
    got = ota._issue_ws_token(fake_request(headers), CLIENT_ID, ALLOWED_MAC)
    assert got, "激活码应能换取 token"
    again = ota._issue_ws_token(fake_request(headers), CLIENT_ID, ALLOWED_MAC)
    assert again == "", "激活码用过一次后不应再用"
    print("OK: OTA 激活码首次绑定签发且用后失效")


def test_auth_disabled_unchanged():
    """8. auth.enabled=false → 行为完全不变（直接放行、不签发）"""
    ws = build_ws_server(build_config(enabled=False, allowed=[ALLOWED_MAC]))
    ok = run_ws_auth(ws, {"device-id": ALLOWED_MAC, "client-id": CLIENT_ID})
    assert ok, "认证关闭时应完全放行，与改动前一致"

    ota = build_ota(build_config(enabled=False))
    got = ota._issue_ws_token(
        fake_request({"device-id": ALLOWED_MAC, "client-id": CLIENT_ID}),
        CLIENT_ID,
        ALLOWED_MAC,
    )
    assert got == "", "认证关闭时 OTA 不应签发 token，与改动前一致"
    print("OK: auth.enabled=false 行为不变")


def test_empty_whitelist_unchanged():
    """9. allowed_devices 为空 → 走 token 验证，用默认有效期"""
    ws = build_ws_server(build_config(enabled=True, allowed=[]))
    token = ws.auth.generate_token(CLIENT_ID, OTHER_MAC)
    ok = run_ws_auth(
        ws,
        {"device-id": OTHER_MAC, "client-id": CLIENT_ID, **bearer(token)},
    )
    assert ok, "白名单为空时合法 token 应通过"
    # 白名单为空时按默认有效期校验过期：造一个 10 秒前签发的 token
    old_ts = int(time.time()) - 10
    stale = f"{ws.auth._sign(f'{CLIENT_ID}|{OTHER_MAC}|{old_ts}')}.{old_ts}"
    ws.auth.expire_seconds = 1
    assert not ws.auth.verify_token(stale, CLIENT_ID, OTHER_MAC), (
        "白名单为空时应按默认有效期校验过期"
    )
    print("OK: allowed_devices 为空走默认 token 校验")


def test_web_test_client_backdoor_removed():
    """10. client_id == web_test_client → 拒绝"""
    handler = VisionHandler(build_config(enabled=True))
    ok, device_id = handler._verify_auth_token(
        fake_request({"Client-Id": "web_test_client", "Device-Id": "whatever"})
    )
    assert not ok, "web_test_client 仍能跳过认证"
    assert device_id is None, "被拒时不应回传 device_id"
    print("OK: web_test_client 后门已移除")


def test_mqtt_topic_injection_blocked():
    """11. MQTT topic 注入 Device-Id: x/# → 被格式校验拦下"""
    ota = build_ota(build_config(enabled=True))
    for evil in ("x/#", "aabbccddeeff/#", "../../etc", "x:y:z:1:2:3"):
        assert not ota._is_valid_device_id(evil), f"{evil} 不该通过 Device-Id 校验"
    for ok_mac in (
        ALLOWED_MAC,
        "11-22-33-44-55-66",
        "11_22_33_44_55_66",
        "aabbccddeeff",
        "AA:BB:CC:DD:EE:FF",
    ):
        assert ota._is_valid_device_id(ok_mac), f"{ok_mac} 应通过 Device-Id 校验"
    print("OK: MQTT topic 注入被 Device-Id 校验拦下")


def test_download_requires_credential():
    """12. OTA 固件下载无 token → 拒绝"""
    ota = build_ota(build_config(enabled=True, allowed=[ALLOWED_MAC]))
    resp = asyncio.run(
        ota.handle_download(
            fake_request({"device-id": ALLOWED_MAC, "client-id": CLIENT_ID})
        )
    )
    assert resp.status == 401, f"无凭证下载应 401，实际 {resp.status}"

    token = ota.auth.generate_token(CLIENT_ID, ALLOWED_MAC)
    resp_ok = asyncio.run(
        ota.handle_download(
            fake_request(
                {
                    "device-id": ALLOWED_MAC,
                    "client-id": CLIENT_ID,
                    **bearer(token),
                },
                {"filename": "nonexistent.bin"},
            )
        )
    )
    assert resp_ok.status != 401, "带合法凭证不应被鉴权拦下"
    print("OK: 固件下载无凭证 401，带凭证放行到后续校验")


def test_handler_state_initialized():
    """OTAHandler 构造后固件缓存相关属性必须就位"""
    ota = build_ota(build_config(enabled=True))
    for attr in ("bin_dir", "_bin_cache", "auth", "auth_enable"):
        assert hasattr(ota, attr), f"OTAHandler 缺少属性 {attr}"
    assert "files_by_model" in ota._bin_cache, "固件缓存结构不完整"
    print("OK: OTAHandler 状态初始化完整")


def main() -> int:
    test_allowed_mac_without_token_rejected()
    test_allowed_mac_forged_client_id_rejected()
    test_allowed_mac_valid_token_accepted()
    test_non_allowed_mac_without_token_rejected()
    test_ota_allowed_mac_gets_token_on_renew()
    test_ota_without_credential_rejected()
    test_ota_activation_code_first_binding()
    test_auth_disabled_unchanged()
    test_empty_whitelist_unchanged()
    test_web_test_client_backdoor_removed()
    test_mqtt_topic_injection_blocked()
    test_download_requires_credential()
    test_handler_state_initialized()
    print("\nALL PASS: 3448 认证旁路已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main())