import os
import subprocess
import sys
import time


def restart_server(logger):
    """实际执行重启的方法"""
    time.sleep(1)
    logger.info("执行服务器重启...")
    subprocess.Popen(
        [sys.executable, "app.py"],
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        start_new_session=True,
    )
    os._exit(0)