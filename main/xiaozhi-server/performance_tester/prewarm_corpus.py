# prewarm_corpus.py — 按 device_simulator_tui 的 md5 约定预合成全部语料(SAPI)
import hashlib
import os
import subprocess
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

phrases = [ln.strip() for ln in open("phrases.txt", encoding="utf-8")
           if ln.strip() and not ln.strip().startswith("#")]
for idx, text in enumerate(phrases, 1):
    cache = f"cache_{hashlib.md5(text.encode()).hexdigest()[:10]}.wav"
    if os.path.exists(cache) and os.path.getsize(cache) > 1000:
        print(f"[{idx}] cached: {text}")
        continue
    r = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", "speak.ps1", text,
         os.path.abspath(cache)], capture_output=True, timeout=40)
    size = os.path.getsize(cache) if os.path.exists(cache) else 0
    print(f"[{idx}] {size}B: {text}")
print("done")
