# All-in-one Digital Human Configuration Guide

This project deploys a complete digital human display system on x86 devices (e.g., mini PCs, industrial PCs, standard computers), implementing the following features:
- Auto-launch Kiosk full-screen browser on boot to display the specified webpage
- Run wake word detection service in background, supporting voice interaction

> **Note**: This document uses the **Intel N100 mini PC (Tianhong QN10-100B4)** as an example for deployment. Other x86 devices can refer to this guide with adjustments (note differences in network configuration and sound card devices).

## Environment

| Item | Description |
|------|------|
| Example Hardware | Tianhong QN10-100B4 (Intel N100) |
| OS | Ubuntu 24.04 LTS (Noble Numbat) |
| Example user | xz (replace as needed) |
| Network | Wi-Fi connection, static IP (can be changed to wired if needed) |

## Deployment Process

1. System initialization (switch source, connect network)
2. Install graphical components and Kiosk browser
3. Configure auto-login and GUI
4. Deploy wake word service (Python environment + microphone)
5. Optimize boot speed and hide startup info

---


### System initialization (switch source, connect network)

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


Install network management tool (ignore if already exists)

Bash

```
sudo apt update
sudo apt install network-manager -y
sudo systemctl start NetworkManager
sudo systemctl enable NetworkManager
```


Set Wi-Fi password and static IP

> **Note**: The Wi-Fi name, password, and IP address in the following commands are examples. Replace them with your actual information.

Bash

```
sudo nmcli device wifi connect "MERCURY_1812" password "12345678"

sudo nmcli connection modify "MERCURY_1812" ipv4.addresses "192.168.0.86/24" ipv4.gateway "192.168.0.1" ipv4.dns "8.8.8.8,114.114.114.114" ipv4.method "manual"

sudo nmcli connection up "MERCURY_1812"
```


### Step 1: Install core graphics components and browser

We adhere to "minimalism", strictly avoiding unnecessary desktop environments (such as GNOME/KDE), installing only low-level drivers, the lightest window manager (Openbox), mouse hiding tools, and the Chromium browser.

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

### Step 2: Configure passwordless auto-login for TTY1 on boot

To avoid the awkwardness of manually entering credentials, we modify the systemd service to automatically log in as `xz` on boot. Use the one-click write command to completely avoid save failures caused by improper `nano` or `vi` operations.

**1. Create config directory:**

Bash

```
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
```

**2. Write auto-login rules:**

Bash

```
echo -e "[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin xz --noclear %I \$TERM" | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf
```

**3. Reload service and set default startup target:**

Bash

```
sudo systemctl daemon-reload
sudo systemctl set-default multi-user.target
```

### Step 3: Configure GUI to auto-start after login

After automatic system login, the default state is a black-background white-text command line. Configure a script to launch the X11 graphical environment immediately upon login.

**1. Trigger the startup logic for `startx`:**

Append trigger code directly to your personal environment config file:

Bash

```
cat << 'EOF' >> ~/.bash_profile
if [ -z "$DISPLAY" ] && [ "$(fgconsole)" -eq 1 ]; then
    exec startx
fi
EOF
```

**2. Tell `startx` to start Openbox:**

Bash

```
echo "exec openbox-session" > ~/.xinitrc
```

### Step 4: Configure 'fortress-like' Openbox and browser

Critical step: Disable screen sleep, hide the mouse, lock the browser in fullscreen, and implement a watchdog loop to instantly restart the browser if it closes unexpectedly.

**1. Create Openbox config directory:**

Bash

```
mkdir -p ~/.config/openbox
```

**2. Write autostart script (`autostart`):**

Copy the entire code block below and press Enter (this automatically writes all protection rules to the file):

Bash

```
cat << 'EOF' > ~/.config/openbox/autostart
# Disable screensaver
xset -dpms
xset s noblank
xset s off

# Hide Cursor
unclutter -idle 0.1 -root &

# Infinite loop to launch Chromium (instant restart on crash or close)
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

**3. Disable the `Alt+F4` exit shortcut:**

To prevent others from closing the window via keyboard shortcuts, disable Openbox default system shortcuts.

Bash

```
cp /etc/xdg/openbox/rc.xml ~/.config/openbox/
sed -i '/<keybind key="A-F4">/,/<\/keybind>/d' ~/.config/openbox/rc.xml
```

### Step 5: Restart to verify results

If the network cable is unplugged or waiting for all networks to come online is unnecessary, disable the network wait service to avoid boot lag

Bash

```
sudo systemctl mask systemd-networkd-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
```

Hide boot info (GRUB)

Bash

```
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 systemd.show_status=false vt.global_cursor_default=0"/g' /etc/default/grub

echo 'GRUB_TIMEOUT_STYLE="hidden"' | sudo tee -a /etc/default/grub
echo 'GRUB_RECORDFAIL_TIMEOUT=0' | sudo tee -a /etc/default/grub

sudo update-grub
```

Set volume to 100%, then restart:

Bash

```
amixer -q sset Master 100% unmute
sudo reboot
```

### Deploy wake word service

To deploy the wake word detection service on an all-in-one device, install the Python environment, upload project files, configure the Camera microphone, and set up auto-start on boot.

#### 1. Install Miniconda

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
~/miniconda3/bin/conda init bash
source ~/.bashrc
rm Miniconda3-latest-Linux-x86_64.sh
```


Ensure automatic entry into the conda environment upon login

```bash
if ! grep -q '.bashrc' ~/.bash_profile; then
    cat << 'EOF' >> ~/.bash_profile

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
EOF
fi
```


#### 2. Create Python virtual environment

```bash
conda create -n test python=3.10 -y
conda activate test
```

If the 'Terms of Service have not been accepted' error occurs, run:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

#### 3. Upload project files

Upload the entire `main/digital-human/` directory from the dev machine to the `~/digital-human/` directory on the all-in-one device:

```bash
# Execute on the development machine (replace <All-in-One IP> with the actual IP)
scp -r main/digital-human/ xz@<All-in-One IP>:~/digital-human/
```

#### 4. Install system dependencies

The wake word service requires audio capture libraries and ALSA PulseAudio plugins:

```bash
sudo apt install libportaudio2 portaudio19-dev libasound2-plugins -y
```

#### 5. Install Python dependencies

```bash
cd ~/digital-human/wakeword_runtime
pip install numpy
pip install -r requirements.txt
```

#### 6. Download wake word model

Model files are not included in the project and must be downloaded and configured separately. See the "Model Download" section in [docs/digital-human-wakeword.md](digital-human-wakeword.md).

#### 7. Modify Openbox autostart script

Add PulseAudio and Camera microphone configs to autostart, and change Chrome URL to the test page.

First verify the Camera microphone device name in PulseAudio:

```bash
pulseaudio --start
pactl list sources short
```

Find the line containing `USB_Camera`, note the full name, e.g.:

```
alsa_input.usb-SN0002_2K_USB_Camera_46435000_P030D00_SN0002-02.mono-fallback
```

Then overwrite autostart with the full content (replace `TARGET_MIC` with your actual device name):

```bash
cat << 'EOF' > ~/.config/openbox/autostart
# 1. Start the audio service and wait briefly
pulseaudio --start
sleep 1

# 2. Lock Camera microphone (replace with your actual device name)
TARGET_MIC="alsa_input.usb-SN0002_2K_USB_Camera_46435000_P030D00_SN0002-02.mono-fallback"

# 3. Set as system default microphone
pactl set-default-source "$TARGET_MIC"

# 4. Unmute
pactl set-source-mute "$TARGET_MIC" 0

# 5. Set volume to 100%
pactl set-source-volume "$TARGET_MIC" 100%

# --- Minimal desktop and browser environment configuration ---

# Disable screensaver
xset -dpms
xset s noblank
xset s off

# Hide Cursor
unclutter -idle 0.1 -root &

# Start browser in infinite loop (restarts instantly on crash or close)
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

#### 8. Configure wake word service to start on boot

Create a systemd service file to enable the wake word service to run automatically on boot.

First confirm the current user's UID:

```bash
id -u $(whoami)
```

Then replace the UID below with the one you found `1000` (the first user is usually 1000):

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

> **Important Note**:
> - `User=xz` - Replace with your actual username
> - `/run/user/1000` - Replace with your actual UID
> - Paths in `WorkingDirectory` and `ExecStart` - Replace with your actual deployment paths
> - The PulseAudio environment variables in `Environment` **must be preserved**, otherwise the wake word service and browser cannot simultaneously use the Camera microphone

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable digital-human
sudo systemctl start digital-human
```

#### 9. Common service management commands

```bash
sudo systemctl start digital-human     # Start now
sudo systemctl stop digital-human      # Stop
sudo systemctl restart digital-human   # Restart
sudo systemctl status digital-human    # View status
journalctl -u digital-human -f         # View real-time logs
```

