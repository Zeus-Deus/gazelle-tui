# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gazelle is a minimal, keyboard-driven NetworkManager TUI for Linux with complete 802.1X enterprise WiFi support. Built with Python's Textual framework, it wraps `nmcli`/`mmcli`/DBus to manage WiFi, VPN, and WWAN/cellular connections.

## Development Setup & Running

```bash
pip install -r requirements.txt
chmod +x gazelle
./gazelle
```

With Nix: `nix develop` then `python3 gazelle`.

There is no test suite. There is no CI/CD pipeline. There is no linter configured.

## Architecture

The application is three files:

- **`gazelle`** - Entry point script (8 lines). Imports and runs the `Gazelle` App class.
- **`app.py`** - Main TUI application (~817 lines). Contains all UI: the `Gazelle(App)` main class plus modal screens (`PasswordScreen`, `VPNScreen`, `WWANScreen`, `HiddenNetworkScreen`). Uses Textual's reactive widget system with inline CSS for styling.
- **`network.py`** - Network abstraction layer (~414 lines). Purely functional (no classes). Every function wraps `subprocess.run` calls to `nmcli`/`mmcli` or DBus operations. Returns parsed data as lists/dicts.

### Key Patterns

- **Functional network layer**: `network.py` has zero classes. Each function runs a subprocess command, parses output, and returns data. All error handling is try/except around subprocess calls.
- **DBus-with-fallback**: Toggle operations (WiFi/WWAN radio) attempt DBus first for speed, then fall back to `nmcli` if DBus is unavailable.
- **Async scanning**: Network scans use `asyncio.to_thread()` to avoid blocking the TUI event loop.
- **Modal screen pattern**: Dialogs (VPN, WWAN, hidden network, password) are Textual `ModalScreen` subclasses that return results via `dismiss()`.
- **4-section layout**: Device info, Station info, Known Networks (saved, in range), New Networks (unsaved). Tab switches between the two network sections.

### Theme System

Three theme sources with priority:
1. **Omarchy auto-detection** - reads `~/.config/omarchy/current/theme/alacritty.toml` (or `ghostty.conf`)
2. **User custom theme** - `~/.config/gazelle/theme.toml`
3. **Built-in Textual themes** - selected via command palette (`Ctrl+P`)

Theme choice persists in `~/.config/gazelle/config.json`. Helper functions `load_omarchy_colors()`, `load_user_colors()`, and `normalize_color_format()` handle color loading and format conversion (0xRRGGBB to #RRGGBB).

### Configuration

- Config dir: `~/.config/gazelle/` (uses `platformdirs` constant `CONFIG_DIR`)
- Config file: `config.json` (currently only stores theme preference)
- Theme file: `theme.toml` (user custom colors, auto-generated template on first run)

## Packaging

- **AUR**: `PKGBUILD` at repo root
- **Nix**: `flake.nix` with Home Manager module in `home-manager/gazelle.nix`
- **Gentoo**: packaged in GURU overlay (externally maintained, not in this repo)

## Dependencies

Runtime: Python 3.8+, `textual>=0.47.0`, `rich`, `platformdirs`, `dbus-python`. Optional: `ModemManager` (WWAN), `networkmanager-openvpn`, `wireguard-tools`.
