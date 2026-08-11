import sys
import types
import unittest

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class _TestLogger:
    def bind(self, **_kwargs):
        return self

    def warning(self, *_args, **_kwargs):
        return None


logger_module = types.ModuleType("config.logger")
logger_module.setup_logging = lambda: _TestLogger()
sys.modules.setdefault("config.logger", logger_module)

register_module = types.ModuleType("plugins_func.register")
register_module.Action = types.SimpleNamespace(REQLLM="reqllm")
register_module.ActionResponse = lambda *args: args
register_module.ToolType = types.SimpleNamespace(SYSTEM_CTL="system")
register_module.register_function = lambda *_args, **_kwargs: (lambda function: function)
sys.modules.setdefault("plugins_func.register", register_module)

from plugins_func.functions.get_weather import (
    WeatherConfigError,
    build_auth_headers,
    fetch_weather_data,
    format_weather_report,
)


class WeatherAuthenticationTests(unittest.TestCase):
    def test_api_key_uses_header_without_bearer(self):
        headers = build_auth_headers({"auth_type": "api_key", "api_key": "api-key"})

        self.assertEqual("api-key", headers["X-QW-Api-Key"])
        self.assertNotIn("Authorization", headers)

    def test_jwt_contains_only_qweather_claims_and_eddsa_key_id(self):
        private_key = Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        headers = build_auth_headers(
            {
                "auth_type": "jwt",
                "project_id": "project-id",
                "credential_id": "credential-id",
                "private_key": pem,
            },
            now=1_700_000_000,
        )

        token = headers["Authorization"].removeprefix("Bearer ")
        decoded = jwt.decode(
            token,
            private_key.public_key(),
            algorithms=["EdDSA"],
            options={"verify_exp": False, "verify_iat": False},
        )
        jwt_headers = jwt.get_unverified_header(token)
        self.assertEqual(
            {"sub": "project-id", "iat": 1_699_999_970, "exp": 1_700_000_900},
            decoded,
        )
        self.assertEqual("EdDSA", jwt_headers["alg"])
        self.assertEqual("credential-id", jwt_headers["kid"])
        self.assertNotIn("X-QW-Api-Key", headers)

    def test_incomplete_jwt_configuration_is_rejected(self):
        with self.assertRaises(WeatherConfigError):
            build_auth_headers({"auth_type": "jwt", "project_id": "project-id"})


class WeatherApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_city_current_and_daily_json_endpoints(self):
        requests = []

        async def handler(request):
            requests.append(request)
            if request.url.path == "/geo/v2/city/lookup":
                return httpx.Response(
                    200,
                    json={"code": "200", "location": [{"id": "101010100", "name": "北京"}]},
                )
            if request.url.path == "/v7/weather/now":
                return httpx.Response(200, json={"code": "200", "now": {"text": "晴", "temp": "26"}})
            if request.url.path == "/v7/weather/7d":
                return httpx.Response(
                    200,
                    json={
                        "code": "200",
                        "daily": [{"fxDate": "2026-08-11", "textDay": "晴", "textNight": "晴",
                                   "tempMin": "20", "tempMax": "30"}],
                    },
                )
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            city, current, daily = await fetch_weather_data(
                {"api_host": "weather.example", "auth_type": "api_key", "api_key": "secret"},
                "北京",
                "zh_CN",
                client,
            )

        self.assertEqual("北京", city["name"])
        self.assertEqual("晴", current["now"]["text"])
        self.assertEqual("2026-08-11", daily["daily"][0]["fxDate"])
        self.assertEqual(
            {"/geo/v2/city/lookup", "/v7/weather/now", "/v7/weather/7d"},
            {request.url.path for request in requests},
        )
        self.assertTrue(all(request.headers["X-QW-Api-Key"] == "secret" for request in requests))
        self.assertTrue(all("authorization" not in request.headers for request in requests))

    async def test_current_and_daily_requests_run_concurrently(self):
        started = []
        release = __import__("asyncio").Event()

        async def handler(request):
            if request.url.path == "/geo/v2/city/lookup":
                return httpx.Response(200, json={"code": "200", "location": [{"id": "1", "name": "城市"}]})
            started.append(request.url.path)
            if len(started) == 2:
                release.set()
            await release.wait()
            key = "now" if request.url.path.endswith("now") else "daily"
            value = {} if key == "now" else []
            return httpx.Response(200, json={"code": "200", key: value})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await fetch_weather_data(
                {"api_host": "weather.example", "api_key": "secret"}, "城市", "zh_CN", client
            )

        self.assertCountEqual(["/v7/weather/now", "/v7/weather/7d"], started)

    def test_formats_current_and_seven_day_json(self):
        report = format_weather_report(
            {"name": "北京"},
            {"now": {"text": "晴", "temp": "26", "feelsLike": "27", "humidity": "40"}},
            {"daily": [{"fxDate": "2026-08-11", "textDay": "晴", "textNight": "多云",
                        "tempMin": "20", "tempMax": "30"}]},
        )

        self.assertIn("当前天气: 晴，26℃，体感 27℃", report)
        self.assertIn("湿度: 40%", report)
        self.assertIn("2026-08-11: 晴转多云，气温 20~30℃", report)


if __name__ == "__main__":
    unittest.main()
