# 一体机数字人配置指南

本项目用于在 x86 架构设备（如迷你主机、工控机、普通电脑等）上部署一套完整的数字人展示系统，实现以下功能：
- 开机自动进入 Kiosk 全屏浏览器，展示指定网页
- 后台运行唤醒词检测服务，支持语音交互

> **说明**：本文档以 **Intel N100 迷你主机（天虹 QN10-100B4）** 为例进行部署演示，其他 x86 设备可参考调整（注意网络配置和声卡设备差异）。

## 适用环境

| 项目 | 说明 |
|------|------|
| 示例硬件 | 天虹 QN10-100B4（Intel N100） |
| 操作系统 | Ubuntu 24.04 LTS (Noble Numbat) |
| 示例用户 | xz（请根据实际情况替换） |
| 网络 | Wi-Fi 连接，固定 IP（可按需改为有线） |

## 部署流程

1. 系统初始化（换源、连网）
2. 安装图形组件与 Kiosk 浏览器
3. 配置自动登录与图形界面
4. 部署唤醒词服务（Python 环境 + 麦克风）
5. 优化开机速度与隐藏启动信息

---


### 系统初始化（换源、连网）

```
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb http://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse
# deb-src http://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse

deb http://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse
# deb-src http://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse

deb http://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse
# deb-src http://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse

deb http://mirrors.aliyun.com/ubuntu/ noble-proposed main restricted universe multiverse
# deb-src http://mirrors.aliyun.com/ubuntu/ noble-proposed main restricted universe multiverse

deb http://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse
# deb-src http://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse
EOF

echo 'Acquire::ForceIPv4 "true";' | sudo tee /etc/apt/apt.conf.d/99force-ipv4
```


安装网络管理工具（若已存在可忽略）

Bash

```
sudo apt update
sudo apt install network-manager -y
sudo systemctl start NetworkManager
sudo systemctl enable NetworkManager
```


设置wifi密码，固定ip

> **提醒**：以下命令中的 Wi-Fi 名称、密码、IP 地址均为示例，请务必替换为你自己的实际信息。

Bash

```
sudo nmcli device wifi connect "MERCURY_1812" password "12345678"

sudo nmcli connection modify "MERCURY_1812" ipv4.addresses "192.168.0.86/24" ipv4.gateway "192.168.0.1" ipv4.dns "8.8.8.8,114.114.114.114" ipv4.method "manual"

sudo nmcli connection up "MERCURY_1812"
```


### 第一步：安装核心图形组件与浏览器

这里我们坚持“极简主义”，坚决不装多余的桌面环境（如 GNOME/KDE），只装底层驱动、最轻量的窗口管理器（Openbox）、隐藏鼠标工具以及 Chromium 浏览器。

Bash

```
sudo timedatectl set-timezone Asia/Shanghai


sudo apt install net-tools vim fonts-wqy-microhei fonts-wqy-zenhei alsa-utils pulseaudio -y
sudo apt install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox unclutter -y

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y
rm google-chrome-stable_current_amd64.deb

sudo apt purge snapd -y

```

### 第二步：配置 TTY1 开机免密自动登录

为了避免手动输入账号密码的尴尬，我们通过修改 systemd 服务，让系统一开机就自动以 `xz` 的身份登录。这里使用一键写入命令，彻底避开由于 `nano` 或 `vi` 操作不当导致的保存失败问题。

**1. 创建配置目录：**

Bash

```
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
```

**2. 写入自动登录规则：**

Bash

```
echo -e "[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin xz --noclear %I \$TERM" | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf
```

**3. 重载服务并设置默认启动目标：**

Bash

```
sudo systemctl daemon-reload
sudo systemctl set-default multi-user.target
```

### 第三步：配置登录后自动启动图形界面

系统自动登录后默认停留在黑底白字的命令行，我们需要配置脚本，让它一旦登录立马启动 X11 图形环境。

**1. 触发 `startx` 的启动逻辑：**

直接将触发代码追加写入你的个人环境配置文件中：

Bash

```
cat << 'EOF' >> ~/.bash_profile
if [ -z "$DISPLAY" ] && [ "$(fgconsole)" -eq 1 ]; then
    exec startx
fi
EOF
```

**2. 告诉 `startx` 去启动 Openbox：**

Bash

```
echo "exec openbox-session" > ~/.xinitrc
```

### 第四步：配置“铜墙铁壁”的 Openbox 与浏览器

这是最核心的一步：关闭屏幕休眠、隐藏鼠标、全屏锁定浏览器，并写一个“死循环”保证浏览器被意外关闭后也能瞬间复活。

**1. 创建 Openbox 配置目录：**

Bash

```
mkdir -p ~/.config/openbox
```

**2. 写入自启动脚本 (`autostart`)：**

复制以下整段代码并回车（这会自动把所有保护规则写进文件里）：

Bash

```
cat << 'EOF' > ~/.config/openbox/autostart
# 关闭屏幕保护
xset -dpms
xset s noblank
xset s off

# 隐藏鼠标
unclutter -idle 0.1 -root &

# 死循环启动 Chromium（崩溃或被关也能秒重启）
while true; do
    google-chrome \
        --kiosk \
        --no-first-run \
        --no-default-browser-check \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-translate \
        --disable-external-intent-requests \
        --autoplay-policy=no-user-gesture-required \
        --use-fake-ui-for-media-stream \
        "https://www.douyin.com"
    sleep 2
done &
EOF
```

**3. 屏蔽 `Alt+F4` 退出快捷键：**

为了防止别人插上键盘强行关掉窗口，我们把 Openbox 默认的系统快捷键干掉。

Bash

```
cp /etc/xdg/openbox/rc.xml ~/.config/openbox/
sed -i '/<keybind key="A-F4">/,/<\/keybind>/d' ~/.config/openbox/rc.xml
```

### 第五步：重启验收成果

如果拔掉网线或不需要等待所有网络上线，可禁用网络等待服务，避免开机卡顿

Bash

```
sudo systemctl mask systemd-networkd-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
```

隐藏开机信息（GRUB）

Bash

```
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 systemd.show_status=false vt.global_cursor_default=0"/g' /etc/default/grub

echo 'GRUB_TIMEOUT_STYLE="hidden"' | sudo tee -a /etc/default/grub
echo 'GRUB_RECORDFAIL_TIMEOUT=0' | sudo tee -a /etc/default/grub

sudo update-grub
```

声音设置成100%，然后 重启：

Bash

```
amixer -q sset Master 100% unmute
sudo reboot
```

### 部署唤醒词服务

在一体机上部署唤醒词检测服务，需要安装 Python 环境、上传项目文件、配置 Camera 麦克风和开机自启。

#### 1. 安装 Miniconda

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
~/miniconda3/bin/conda init bash
source ~/.bashrc
rm Miniconda3-latest-Linux-x86_64.sh
```


确保登录时自动进入conda环境

```bash
if ! grep -q '.bashrc' ~/.bash_profile; then
    cat << 'EOF' >> ~/.bash_profile

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
EOF
fi
```


#### 2. 创建 Python 虚拟环境

```bash
conda create -n test python=3.10 -y
conda activate test
```

若出现 Terms of Service have not been accepted 错误，执行：

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

#### 3. 上传项目文件

将开发机上的 `main/digital-human/` 整个目录上传到一体机的 `~/digital-human/` 目录：

```bash
# 在开发机上执行（将 <一体机IP> 替换为实际 IP）
scp -r main/digital-human/ xz@<一体机IP>:~/digital-human/
```

#### 4. 安装系统依赖

唤醒词服务需要音频采集库和 ALSA PulseAudio 插件：

```bash
sudo apt install libportaudio2 portaudio19-dev libasound2-plugins -y
```

#### 5. 安装 Python 依赖

```bash
cd ~/digital-human/wakeword_runtime
pip install numpy
pip install -r requirements.txt
```

#### 6. 下载唤醒词模型

模型文件不包含在项目中，需要单独下载配置，详见 [docs/digital-human-wakeword.md](digital-human-wakeword.md) 中的“模型下载”章节。

#### 7. 修改 Openbox 自启动脚本

需要在 autostart 中加上 PulseAudio 和 Camera 麦克风配置，并将 Chrome 地址改为测试页面。

先确认 Camera 麦克风在 PulseAudio 中的设备名：

```bash
pulseaudio --start
pactl list sources short
```

找到包含 `USB_Camera` 的那一行，记下完整名称，例如：

```
alsa_input.usb-SN0002_2K_USB_Camera_46435000_P030D00_SN0002-02.mono-fallback
```

然后用完整内容覆盖 autostart（将 `TARGET_MIC` 替换为你的实际设备名）：

```bash
cat << 'EOF' > ~/.config/openbox/autostart
# 1. 启动声音服务并稍作等待
pulseaudio --start
sleep 1

# 2. 锁定 Camera 的麦克风（请替换为你的实际设备名）
TARGET_MIC="alsa_input.usb-SN0002_2K_USB_Camera_46435000_P030D00_SN0002-02.mono-fallback"

# 3. 设为系统默认麦克风
pactl set-default-source "$TARGET_MIC"

# 4. 解除静音
pactl set-source-mute "$TARGET_MIC" 0

# 5. 音量拉到 100%
pactl set-source-volume "$TARGET_MIC" 100%

# --- 极简桌面与浏览器环境配置 ---

# 关闭屏幕保护
xset -dpms
xset s noblank
xset s off

# 隐藏鼠标
unclutter -idle 0.1 -root &

# 死循环启动浏览器（崩溃或被关也能秒重启）
while true; do
    google-chrome \
        --kiosk \
        --no-first-run \
        --no-default-browser-check \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-translate \
        --disable-external-intent-requests \
        --autoplay-policy=no-user-gesture-required \
        --use-fake-ui-for-media-stream \
        "http://127.0.0.1:8006/index.html"
    sleep 2
done &
EOF
```

#### 8. 配置唤醒词服务开机自启

创建 systemd 服务文件，让唤醒词服务开机自动运行。

先确认当前用户的 UID：

```bash
id -u $(whoami)
```

然后用查到的 UID 替换下面 `1000`（通常第一个用户就是 1000）：

```bash
sudo tee /etc/systemd/system/digital-human.service << 'EOF'
[Unit]
Description=Digital Human Runtime
After=network.target sound.target

[Service]
Type=simple
User=xz
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PULSE_SERVER=unix:/run/user/1000/pulse/native
WorkingDirectory=/home/xz/digital-human
ExecStartPre=/bin/sleep 10
ExecStart=/home/xz/miniconda3/envs/test/bin/python start.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

> **重要说明**：
> - `User=xz` — 替换为你的实际用户名
> - `/run/user/1000` — 替换为你实际的 UID
> - `WorkingDirectory` 和 `ExecStart` 中的路径 — 替换为你的实际部署路径
> - `Environment` 中的 PulseAudio 环境变量**必须保留**，否则唤醒词服务和浏览器无法同时使用 Camera 麦克风

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable digital-human
sudo systemctl start digital-human
```

#### 9. 常用服务管理命令

```bash
sudo systemctl start digital-human     # 立即启动
sudo systemctl stop digital-human      # 停止
sudo systemctl restart digital-human   # 重启
sudo systemctl status digital-human    # 查看状态
journalctl -u digital-human -f         # 查看实时日志
```

