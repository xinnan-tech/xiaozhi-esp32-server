# Claude Code Web Terminal

Expose a local **Claude Code CLI** session through a browser-based terminal.

This project is a small, self-contained deployment recipe for people who want to open a browser, visit a private URL, and control Claude Code running on their own computer in a chosen working directory.

> It uses [`ttyd`](https://github.com/tsl0922/ttyd) for the browser terminal. For public access, the recommended path is Tailscale Funnel + Nginx + Basic Auth.

---

## Why this exists

Claude Code is a local CLI. It is great in a terminal, but sometimes you may want to:

- control Claude Code from another computer;
- use a browser instead of SSH/RDP;
- keep all file access and credentials on your own machine;
- expose only a controlled web terminal to a specific project directory;
- give yourself a lightweight remote maintenance entry point.

This tool does **not** turn Claude Code into a web app. It provides a secure-ish browser terminal that runs on your machine, where you can start Claude Code.

---

## Architecture

```text
Browser
  -> https://cc.example.com
  -> Nginx reverse proxy + Basic Auth
  -> Tailscale Funnel
  -> Local machine 127.0.0.1:18792
  -> ttyd
  -> cmd.exe / PowerShell / bash
  -> claude
```

Recommended runtime:

```text
Local ttyd:      http://127.0.0.1:18792
Tailscale URL:   https://your-machine.your-tailnet.ts.net:18790
Public URL:      https://cc.example.com
```

---

## Security warning

This exposes a terminal on your computer.

Anyone who can access the terminal may be able to:

- read and modify files;
- run arbitrary commands;
- access environment variables;
- use local credentials;
- run git operations;
- use Claude Code tools;
- damage or exfiltrate data.

Do **not** expose this without authentication.

Recommended minimum protections:

- bind `ttyd` to `127.0.0.1` only;
- expose it through a tunnel, not by opening the raw port to the Internet;
- put Basic Auth or stronger auth in front;
- use HTTPS;
- rotate passwords;
- stop the tunnel when not in use;
- use a dedicated OS user if possible;
- avoid running as Administrator/root.

---

## Requirements

### Local machine

- Windows 10/11, macOS, or Linux
- Claude Code installed and authenticated
- `ttyd`
- Optional: Tailscale, if exposing outside your local network

### Public server, optional

- Nginx
- TLS certificate
- Basic Auth file
- Reachability to the Tailscale Funnel URL

---

## Quick start: Windows local only

### 1. Install Claude Code

Install Claude Code normally, then check:

```powershell
claude --version
```

Example output:

```text
2.x.x (Claude Code)
```

### 2. Install ttyd

Using winget:

```powershell
winget install --id tsl0922.ttyd
```

If `ttyd` is not found immediately, restart PowerShell or use the full installed path.

Typical winget path:

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\tsl0922.ttyd_Microsoft.Winget.Source_8wekyb3d8bbwe\ttyd.exe
```

### 3. Configure `.env`

Copy the example:

```powershell
copy .env.example .env
```

Edit `.env`:

```env
PROJECT_DIR=E:\code\learn_p\xiaozhi-esp32-server
LOCAL_HOST=127.0.0.1
LOCAL_PORT=18792
SHELL_CMD=cmd.exe
FUNNEL_PORT=18790
```

### 4. Start the terminal

```powershell
.\scripts\start-windows.ps1
```

Open:

```text
http://127.0.0.1:18792/
```

You should see a browser terminal.

Run:

```bat
claude
```

If the terminal is not in your desired directory:

```bat
cd /d E:\code\learn_p\xiaozhi-esp32-server
claude
```

---

## Recommended Windows command

The most stable setup is to start a **plain shell** first, then type `claude` manually:

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\code\learn_p\xiaozhi-esp32-server" cmd.exe
```

Why not auto-start `claude`?

Some Windows PTY setups are less stable when the web terminal launches a complex interactive child command directly. Starting `cmd.exe` first and typing `claude` manually is usually more reliable.

If you still want to try auto-start:

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\code\learn_p\xiaozhi-esp32-server" cmd.exe /k claude
```

---

## Expose using Tailscale Funnel

> Use this only if you understand the security implications.

Expose local `18792` as Tailscale public HTTPS port `18790`:

```powershell
tailscale funnel --bg --https=18790 18792
```

Check:

```powershell
tailscale serve status
```

Expected:

```text
https://your-machine.your-tailnet.ts.net:18790
|-- / proxy http://127.0.0.1:18792
```

Disable it:

```powershell
tailscale funnel --https=18790 off
```

---

## Expose through public Nginx

Use:

```text
nginx/cc.example.com.conf
```

Important Nginx settings:

```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 86400s;
proxy_send_timeout 86400s;
proxy_buffering off;
```

Also configure the WebSocket connection map once inside `http {}` or `conf.d`:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

### Basic Auth

Create password file:

```bash
sudo sh -c 'printf "claude:%s\n" "$(openssl passwd -apr1 YOUR_STRONG_PASSWORD)" > /etc/nginx/.htpasswd-cc'
sudo chmod 640 /etc/nginx/.htpasswd-cc
sudo chown root:www-data /etc/nginx/.htpasswd-cc
```

Then in Nginx:

```nginx
auth_basic "Claude Code Web";
auth_basic_user_file /etc/nginx/.htpasswd-cc;
```

---

## Day-to-day usage

1. Start local terminal:

   ```powershell
   .\scripts\start-windows.ps1
   ```

2. Start Funnel if needed:

   ```powershell
   tailscale funnel --bg --https=18790 18792
   ```

3. Open public URL:

   ```text
   https://cc.example.com/
   ```

4. Login.

5. In terminal:

   ```bat
   claude
   ```

6. Work normally.

7. When finished, either close the browser tab or type:

   ```bat
   exit
   ```

8. For better security, stop the public tunnel:

   ```powershell
   tailscale funnel --https=18790 off
   ```

---

## Stop local service

```powershell
.\scripts\stop-windows.ps1
```

Or manually:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'ttyd.*18792' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## Troubleshooting

### Page opens but input does not work

Usually the WebSocket is not connected.

Check:

- browser DevTools -> Network -> WS;
- Nginx `/ws` returns `101 Switching Protocols`;
- `ttyd` process is still running;
- Tailscale Funnel points to the correct local port.

Test local service:

```powershell
curl.exe -I http://127.0.0.1:18792/
```

Test through Nginx:

```bash
curl -k -i --http1.1 \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  -H 'Sec-WebSocket-Version: 13' \
  https://cc.example.com/ws
```

Expected:

```http
HTTP/1.1 101 Switching Protocols
```

### Browser shows `/socket.io` errors

That usually means you previously used WeTTY and the old Service Worker is still cached.

Fix:

- open DevTools;
- Application -> Service Workers -> Unregister;
- Application -> Storage -> Clear site data;
- reload;
- or use a new incognito window.

### `sw.js` Cache error with `chrome-extension`

This is usually caused by a browser extension or old Service Worker cache. It is not normally a server-side error. Clear site data or test in incognito mode.

### Windows command exits immediately

Use a plain shell:

```powershell
ttyd -i 127.0.0.1 -p 18792 -W -w "E:\path\to\repo" cmd.exe
```

Then type:

```bat
claude
```

### Port conflict

If `18792` is already used, change `.env`:

```env
LOCAL_PORT=18793
```

Then update Funnel:

```powershell
tailscale funnel --bg --https=18790 18793
```

### Tailscale Funnel points to the wrong local port

Run:

```powershell
tailscale serve status
```

If needed, reset and reconfigure:

```powershell
tailscale funnel --https=18790 off
tailscale funnel --bg --https=18790 18792
```

---

## Hardening ideas

For teams or open-source users, consider:

- using OAuth or SSO at Nginx / Cloudflare Access / Tailscale ACL level;
- using an allowlist of source IPs;
- using a dedicated low-privilege OS user;
- binding the project directory read/write permissions carefully;
- logging all access;
- disabling Funnel when not needed;
- running in a disposable VM or container;
- requiring explicit confirmation before destructive commands.

---

## FAQ

### Is this an official Claude Code browser UI?

No. Claude Code is a CLI. This project exposes a local terminal in the browser and lets you run Claude Code inside that terminal.

### Can multiple people use it?

Technically yes, but be careful. Multiple sessions share access to the same machine/user account. For team use, prefer separate users or isolated environments.

### Can it run on macOS/Linux?

Yes. `ttyd` supports macOS/Linux. Replace `cmd.exe` with your shell, for example:

```bash
ttyd -i 127.0.0.1 -p 18792 -W -w /path/to/repo bash
```

### Can I auto-start Claude Code?

You can try, but starting a plain shell first is more reliable:

```bash
claude
```

### Is Tailscale required?

No. You can use any tunnel/reverse proxy. Tailscale Funnel is convenient because it avoids exposing local raw ports directly.

---

## License

Choose a license before publishing. MIT is a common default for small tooling recipes.
