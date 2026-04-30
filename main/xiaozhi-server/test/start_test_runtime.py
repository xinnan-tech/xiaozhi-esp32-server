import threading
from pathlib import Path

from wakeword_runtime.config import load_config, setup_logging
from wakeword_runtime.runtime import TestRuntimeApplication, TestRuntimeHttpServer


def main() -> int:
    test_root = Path(__file__).resolve().parent
    runtime_root = test_root / "wakeword_runtime"

    config = load_config(runtime_root)
    setup_logging(config.log_file, config.log_level)
    http_server = TestRuntimeHttpServer(test_root)
    app_lock = threading.RLock()
    app = TestRuntimeApplication(config, http_server.event_bridge)

    def restart_runtime() -> None:
        nonlocal app
        with app_lock:
            app.shutdown()
            next_config = load_config(runtime_root)
            setup_logging(next_config.log_file, next_config.log_level)
            next_app = TestRuntimeApplication(next_config, http_server.event_bridge)
            next_app.setup()
            next_app.start()
            app = next_app

    http_server.set_restart_handler(restart_runtime)

    print(f"test runtime started: {http_server.page_url}")
    print(f"wakeword bridge websocket: {http_server.bridge_url}")
    print(f"wakeword enabled: {config.wakeword_enabled}")
    print("press Ctrl+C to stop")

    try:
        with app_lock:
            try:
                app.setup()
                app.start()
            except Exception as e:
                print(f"警告: 唤醒词服务启动失败({e})，测试页面仍可正常使用")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("test runtime stopped")
    finally:
        with app_lock:
            app.shutdown()
        http_server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())