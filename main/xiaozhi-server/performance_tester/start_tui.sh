#!/usr/bin/env bash
# device-simulator-tui launcher — ./start_tui.sh
cd "$(dirname "$0")"
python3 -X utf8 device_simulator_tui.py "$@"
