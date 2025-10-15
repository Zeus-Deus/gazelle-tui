# Gazelle

A minimal NetworkManager TUI for Linux with **complete 802.1X enterprise WiFi support**.

## Why Gazelle?

A minimal, keyboard-driven TUI for NetworkManager with **full 802.1X enterprise WiFi support**. Perfect for connecting to eduroam, corporate networks, and regular WiFi from the terminal.

## Installation

```bash
conda activate gazelle
pip install -r requirements.txt
chmod +x gazelle
./gazelle
```

## Features

- ✅ **Complete 802.1X Support** (PEAP/TTLS/TLS with all phase2 auth methods)
- ✅ Connect to regular WiFi (WPA/WPA2-PSK)
- ✅ Connect to enterprise WiFi (eduroam, corporate networks)
- ✅ Scan for networks
- ✅ Auto-connect to known networks in range
- ✅ Toggle WiFi on/off
- ✅ Clean 4-section layout (Device, Station, Known Networks, New Networks)

## 802.1X Enterprise WiFi

Gazelle supports **all common enterprise authentication methods**:

**EAP Methods:**
- PEAP (most common, used by eduroam)
- TTLS
- TLS (certificate-based)

**Phase 2 Authentication:**
- MSCHAPv2 (most common)
- MSCHAP
- PAP
- CHAP
- GTC
- MD5

When connecting to an 802.1X network, simply select your authentication method from the dropdowns.

## Keybindings

- `j`/`k` or `↓`/`↑` - Move cursor
- `Tab` - Switch between Known/New Networks sections
- `Space` - Connect to selected network
- `s` - Scan for networks
- `d` - Disconnect
- `Ctrl+R` - Toggle WiFi on/off
- `?` - Show help
- `q` - Quit

## Connecting to eduroam

1. Select eduroam network (shows as "802.1x" in Security column)
2. Press Space
3. Choose EAP Method: **PEAP** (default)
4. Choose Phase 2: **MSCHAPv2** (default)
5. Enter username (e.g., `user@university.edu`)
6. Enter password
7. Connect!

The connection is saved and will auto-reconnect when in range.

## NetworkManager Integration

Gazelle uses real NetworkManager commands (`nmcli`) - the same backend as:
- GNOME Network Settings
- KDE Network Manager
- nmtui

All connections are stored in `/etc/NetworkManager/` and persist across reboots.

## Requirements

- Linux with NetworkManager
- Python 3.8+
- textual>=0.47.0

## License

MIT
