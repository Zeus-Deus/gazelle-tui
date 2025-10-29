"""Gazelle - Minimal NetworkManager TUI"""
import os
os.environ["RICH_COLOR_SYSTEM"] = "standard"
from textual.app import App, ComposeResult
from textual.theme import Theme
from textual.widgets import Header, Footer, Static, Input, Button, DataTable, Select
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from network import *
import subprocess
import asyncio
import json
from pathlib import Path
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        tomllib = None  # Will use fallback colors

class HiddenNetworkScreen(ModalScreen):
    """Modal for connecting to hidden SSID"""
    
    BINDINGS = [
        ("enter", "submit", "Submit"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Connect to Hidden Network", id="title"),
            Static("SSID:"), Input(placeholder="Network name", id="ssid"),
            Static("Security:"),
            Select([("Open", "open"), ("WPA2/WPA3", "psk"), ("802.1X Enterprise", "8021x")], 
                   value="psk", id="sec"),
            Horizontal(Button("Next", variant="primary", id="next"), Button("Cancel", id="cancel")),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "next":
            self._submit()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in Input field"""
        self._submit()
    
    def _submit(self) -> None:
        """Submit the form"""
        ssid = self.query_one("#ssid", Input).value
        sec = self.query_one("#sec", Select).value
        if ssid:
            self.dismiss((ssid, sec))
    
    def action_cancel(self) -> None:
        """Handle Esc key"""
        self.app.pop_screen()

class VPNScreen(ModalScreen):
    """Screen for VPN connection management"""
    
    BINDINGS = [
        ("escape", "cancel", "Back"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("space", "toggle_vpn", "Connect/Disconnect"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "cancel", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("VPN Connections", classes="section-title"),
            DataTable(id="vpn-table", cursor_type="row"),
            classes="section"
        )
    
    def on_mount(self) -> None:
        """Initialize VPN table"""
        table = self.query_one("#vpn-table", DataTable)
        table.add_columns("Status", "Name")
        self.refresh_vpn_list()
        table.focus()
    
    def refresh_vpn_list(self) -> None:
        """Refresh VPN connection list"""
        table = self.query_one("#vpn-table", DataTable)
        table.clear()
        for vpn in get_vpn_list():
            status = "🟢" if vpn['active'] else "⚪"
            table.add_row(status, vpn['name'])
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)"""
        self.action_toggle_vpn()
    
    def action_toggle_vpn(self) -> None:
        """Toggle VPN connection on Space/Enter key"""
        table = self.query_one("#vpn-table", DataTable)
        if table.cursor_row >= 0 and table.cursor_row < table.row_count:
            row = table.get_row_at(table.cursor_row)
            status, name = str(row[0]), str(row[1])
            
            if status == "🟢":
                # Disconnect
                self.notify("Disconnecting...")
                success = disconnect_vpn(name)
                self.notify("✓ Disconnected" if success else "✗ Failed")
            else:
                # Connect
                self.notify("Connecting...")
                success, msg = connect_vpn(name)
                self.notify("✓ Connected" if success else "✗ Failed")
            
            self.refresh_vpn_list()
    
    def action_cursor_down(self) -> None:
        """Move cursor down"""
        table = self.query_one("#vpn-table", DataTable)
        if table.row_count > 0:
            table.action_cursor_down()
    
    def action_cursor_up(self) -> None:
        """Move cursor up"""
        table = self.query_one("#vpn-table", DataTable)
        if table.row_count > 0:
            table.action_cursor_up()
    
    def action_refresh(self) -> None:
        """Refresh VPN list"""
        self.refresh_vpn_list()
        self.notify("Refreshed")
    
    def action_cancel(self) -> None:
        """Return to main screen on Escape"""
        self.app.pop_screen()

class PasswordScreen(ModalScreen):
    BINDINGS = [
        ("enter", "submit", "Submit"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, ssid, is_enterprise=False, is_hidden=False):
        super().__init__()
        self.ssid, self.is_enterprise, self.is_hidden = ssid, is_enterprise, is_hidden
    
    def compose(self) -> ComposeResult:
        if self.is_enterprise:
            yield Container(
                Static(f"Connect: {self.ssid}", id="title"),
                Static("EAP Method:"),
                Select([("PEAP", "peap"), ("TTLS", "ttls"), ("TLS", "tls")], value="peap", id="eap"),
                Static("Phase 2 Auth:"),
                Select([("MSCHAPv2", "mschapv2"), ("MSCHAP", "mschap"), ("PAP", "pap"), 
                       ("CHAP", "chap"), ("GTC", "gtc"), ("MD5", "md5")], value="mschapv2", id="phase2"),
                Static("Username:"), Input(placeholder="user@domain.com", id="user"),
                Static("Password:"), Input(placeholder="Password", password=True, id="pwd"),
                Horizontal(Button("Connect", variant="primary", id="ok"), Button("Cancel", id="no")),
                id="dialog"
            )
        else:
            yield Container(
                Static(f"Connect: {self.ssid}", id="title"),
                Static("Password:"), Input(placeholder="Password", password=True, id="pwd"),
                Horizontal(Button("Connect", variant="primary", id="ok"), Button("Cancel", id="no")),
                id="dialog"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "no":
            self.app.pop_screen()
        elif event.button.id == "ok":
            self._submit()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in Input fields"""
        self._submit()
    
    def _submit(self) -> None:
        """Submit the form"""
        if self.is_enterprise:
            u = self.query_one("#user", Input).value
            p = self.query_one("#pwd", Input).value
            eap = self.query_one("#eap", Select).value
            phase2 = self.query_one("#phase2", Select).value
            if u and p:
                self.dismiss((self.ssid, p, u, True, eap, phase2, self.is_hidden))
        else:
            p = self.query_one("#pwd", Input).value
            if p:
                self.dismiss((self.ssid, p, None, False, None, None, self.is_hidden))
    
    def action_cancel(self) -> None:
        """Handle Esc key"""
        self.app.pop_screen()

def load_omarchy_colors():
    """
    Load colors from Omarchy's active theme.
    Returns dict with RGB color values, or None if not found.
    """
    if tomllib is None:
        return None
    
    theme_file = Path.home() / ".config/omarchy/current/theme/alacritty.toml"
    
    if not theme_file.exists():
        return None
    
    try:
        with open(theme_file, "rb") as f:
            data = tomllib.load(f)
        
        colors = data.get("colors", {})
        normal = colors.get("normal", {})
        bright = colors.get("bright", {})
        primary = colors.get("primary", {})
        
        return {
            "accent": normal.get("yellow") or bright.get("yellow") or "#EBCB8B",
            "primary": normal.get("red") or bright.get("red") or "#BF616A",
            "foreground": primary.get("foreground") or "#D8DEE9",
            "background": primary.get("background") or "#2E3440",
        }
    except Exception:
        # If parsing fails, return None to use fallback
        return None

class Gazelle(App):
    ansi_color = True  # Enable terminal ANSI color support
    CSS = """
    PasswordScreen, HiddenNetworkScreen { align: center middle; }
    #dialog { width: 60; height: auto; border: thick $accent; background: $background; padding: 1 2; }
    #title { text-style: bold; color: $accent; margin-bottom: 1; }
    .section { border: solid $accent; margin: 1 2; padding: 0 1; }
    .section-title { text-style: bold; color: $accent; background: $background; padding: 0 1; }
    #device-section, #station-section { height: 5; }
    Static { height: auto; }
    Input { height: 3; margin-bottom: 1; }
    Select { height: 3; margin-bottom: 1; }
    Horizontal { height: auto; margin-top: 1; }
    Button { min-width: 12; }

    /* DataTable selection/cursor colors */
    DataTable > .datatable--cursor {
        background: $accent 30%;
        color: $foreground;
    }

    DataTable > .datatable--hover {
        background: $accent 20%;
    }
    """
    
    TITLE = "Gazelle"
    CONFIG_DIR = Path.home() / ".config" / "gazelle"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("tab", "switch_section", "Switch"),
        Binding("space", "select", "Connect"),
        Binding("s", "scan", "Scan"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("h", "hidden", "Hidden"),
        Binding("v", "vpn_screen", "VPN"),
        Binding("ctrl+r", "toggle_wifi", "WiFi"),
        Binding("?", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(Static("Device", classes="section-title"), 
                     DataTable(id="dev"), classes="section", id="device-section"),
            Container(Static("Station", classes="section-title"),
                     DataTable(id="sta"), classes="section", id="station-section"),
            Container(Static("Known Networks", classes="section-title"),
                     DataTable(id="known", cursor_type="row"), classes="section"),
            Container(Static("New Networks", classes="section-title"),
                     DataTable(id="new", cursor_type="row"), classes="section"),
        )
        yield Footer()
    
    def on_mount(self) -> None:
        # Try to load Omarchy colors
        omarchy_colors = load_omarchy_colors()
        
        if omarchy_colors:
            # Register Omarchy-specific theme with exact RGB values
            self.register_theme(
                Theme(
                    name="omarchy-auto",
                    primary=omarchy_colors["primary"],
                    secondary=omarchy_colors["accent"],
                    accent=omarchy_colors["accent"],
                    foreground=omarchy_colors["foreground"],
                    background=omarchy_colors["background"],
                    surface=omarchy_colors["background"],
                    panel=omarchy_colors["background"],
                    dark=True,
                )
            )
            default_theme = "omarchy-auto"
        else:
            # Fallback: Use ANSI colors for non-Omarchy users
            self.register_theme(
                Theme(
                    name="auto",
                    primary="ansi_yellow",
                    secondary="ansi_cyan",
                    accent="ansi_yellow",
                    foreground="ansi_white",
                    background="ansi_black",
                    surface="ansi_black",
                    panel="ansi_black",
                    dark=True,
                )
            )
            default_theme = "auto"

        # Load saved theme or use default
        config = self.load_config()
        saved_theme = config.get("theme", default_theme)
        try:
            self.theme = saved_theme
        except Exception:
            self.theme = default_theme
        
        self.query_one("#dev").add_columns("Name", "Mode", "Powered", "Address")
        self.query_one("#dev").cursor_type = "none"
        self.query_one("#sta").add_columns("State", "Scanning", "Frequency", "Security")
        self.query_one("#sta").cursor_type = "none"
        self.query_one("#known").add_columns("Name", "Security", "Signal")
        self.query_one("#new").add_columns("Name", "Security", "Signal")
        
        # Show placeholder while scanning
        new_table = self.query_one("#new")
        new_table.add_row("Scanning for networks...", "", "")
        
        # Trigger async network scan
        self.run_worker(self.scan_networks_async, exclusive=True)
        
        self.query_one("#new").focus()
    
    def load_config(self) -> dict:
        """Load configuration from ~/.config/gazelle/config.json
        
        Returns:
            dict: Configuration dictionary, or empty dict if file doesn't exist
        """
        try:
            if self.CONFIG_FILE.exists():
                return json.loads(self.CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            # If config is corrupted, log error and return empty dict
            self.log.error(f"Failed to load config: {e}")
        return {"theme": "auto"}  # Default new installations to auto theme
    
    def save_config(self, data: dict) -> None:
        """Save configuration to ~/.config/gazelle/config.json
        
        Args:
            data: Dictionary to save as JSON
        """
        try:
            # Create config directory if it doesn't exist
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            # Write config file with pretty formatting
            self.CONFIG_FILE.write_text(json.dumps(data, indent=2))
        except OSError as e:
            self.log.error(f"Failed to save config: {e}")
    
    def watch_theme(self, new_theme: str) -> None:
        """Automatically called by Textual when self.theme changes.
        
        Saves the new theme to config file for persistence.
        
        Args:
            new_theme: The new theme name that was just set
        """
        # Load existing config, update theme, save back
        config = self.load_config()
        config["theme"] = new_theme
        self.save_config(config)
        self.log.info(f"Theme changed to: {new_theme}")
    
    async def scan_networks_async(self) -> None:
        """Async WiFi network scanning in background"""
        try:
            # Run blocking get_wifi_list() in background thread
            await asyncio.to_thread(get_wifi_list)
            # Update UI with results
            self.refresh_all()
        except Exception as e:
            self.notify(f"Scan failed: {str(e)}")
    
    def refresh_all(self) -> None:
        # Device
        t = self.query_one("#dev")
        t.clear()
        iface = get_wifi_interface()
        try:
            mac = subprocess.run(['cat', f'/sys/class/net/{iface}/address'], 
                                capture_output=True, text=True).stdout.strip()
        except:
            mac = "-"
        t.add_row(iface, "station", "On" if wifi_enabled() else "Off", mac)
        
        # Station
        t = self.query_one("#sta")
        t.clear()
        i = get_station_info()
        t.add_row(i['state'], i['scanning'], i['frequency'], i['security'])
        
        # Known (only show networks that are in range)
        t = self.query_one("#known")
        t.clear()
        known_ssids = set()
        try:
            r = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                              capture_output=True, text=True)
            avail = {n['ssid']: n for n in get_wifi_list()}
            for line in r.stdout.strip().split('\n'):
                if ':802-11-wireless' in line or ':wifi' in line:
                    name = line.split(':')[0]
                    known_ssids.add(name)
                    # Only show if network is in range
                    if name in avail:
                        s = avail[name]['security']
                        if is_enterprise(s):
                            sec = "802.1x"
                        elif is_owe(s):
                            sec = "owe"
                        elif s:
                            sec = "psk"
                        else:
                            sec = "-"
                        sig = f"{avail[name]['signal']}%"
                        t.add_row(name, sec, sig)
        except:
            pass
        
        # New (exclude networks that are already known)
        t = self.query_one("#new")
        t.clear()
        for n in get_wifi_list():
            if n['ssid'] not in known_ssids:
                if is_enterprise(n['security']):
                    sec = "802.1x"
                elif is_owe(n['security']):
                    sec = "owe"
                elif n['security']:
                    sec = "psk"
                else:
                    sec = "-"
                t.add_row(n['ssid'], sec, f"{n['signal']}%")
    
    def _get_focused_table(self):
        """Get the currently focused table"""
        known = self.query_one("#known")
        new = self.query_one("#new")
        if known.has_focus:
            return known
        else:
            return new
    
    def action_cursor_down(self) -> None:
        t = self._get_focused_table()
        if t.row_count > 0:
            t.action_cursor_down()
    
    def action_cursor_up(self) -> None:
        t = self._get_focused_table()
        if t.row_count > 0:
            t.action_cursor_up()
    
    def action_switch_section(self) -> None:
        known = self.query_one("#known")
        new = self.query_one("#new")
        if known.has_focus:
            new.focus()
        else:
            known.focus()
    
    def action_scan(self) -> None:
        self.notify("Scanning...")
        subprocess.run(['nmcli', 'device', 'wifi', 'rescan'], capture_output=True)
        self.run_worker(self.scan_networks_async, exclusive=True)
    
    def action_select(self) -> None:
        t = self._get_focused_table()
        is_known = self.query_one("#known").has_focus
        
        if t.cursor_row >= 0 and t.cursor_row < t.row_count:
            row = t.get_row_at(t.cursor_row)
            ssid, sec = str(row[0]), str(row[1])
            
            if is_known:
                self.notify(f"Connecting...")
                r = subprocess.run(['nmcli', 'connection', 'up', ssid], 
                                  capture_output=True, text=True)
                self.notify("✓ Connected" if r.returncode == 0 else "✗ Failed")
                self.refresh_all()
            else:
                if sec == "802.1x":
                    self.push_screen(PasswordScreen(ssid, is_enterprise=True), self.handle_connect)
                elif sec == "psk":
                    self.push_screen(PasswordScreen(ssid, is_enterprise=False), self.handle_connect)
                else:  # Open or OWE - NetworkManager handles OWE automatically
                    ok, msg = connect_wifi(ssid, "", hidden=False)
                    self.notify("✓ Connected" if ok else f"✗ {msg}")
                    self.refresh_all()
    
    def handle_connect(self, result) -> None:
        if not result:
            return
        ssid, pwd, user, is_ent, eap, phase2, is_hidden = result
        self.notify("Connecting...")
        if is_ent:
            ok, msg = connect_802_1x(ssid, user, pwd, eap or "peap", phase2 or "mschapv2", is_hidden)
        else:
            ok, msg = connect_wifi(ssid, pwd, is_hidden)
        self.notify("✓ Connected" if ok else f"✗ {msg}")
        self.refresh_all()
    
    def action_hidden(self) -> None:
        """Connect to hidden network (h key)"""
        def handle_hidden(result):
            if not result:
                return
            ssid, sec = result
            if sec == "open":
                self.notify("Connecting...")
                ok, msg = connect_wifi(ssid, "", hidden=True)
                self.notify("✓ Connected" if ok else f"✗ {msg}")
                self.refresh_all()
            elif sec == "psk":
                self.push_screen(PasswordScreen(ssid, is_enterprise=False, is_hidden=True), self.handle_connect)
            else:  # 8021x
                self.push_screen(PasswordScreen(ssid, is_enterprise=True, is_hidden=True), self.handle_connect)
        
        self.push_screen(HiddenNetworkScreen(), handle_hidden)
    
    def action_disconnect(self) -> None:
        self.notify("Disconnected" if disconnect() else "Not connected")
        self.refresh_all()
    
    def action_toggle_wifi(self) -> None:
        self.notify(f"WiFi {'ON' if toggle_wifi() else 'OFF'}")
        self.set_timer(1, self.refresh_all)
    
    def action_vpn_screen(self) -> None:
        """Open VPN management screen"""
        self.push_screen(VPNScreen())
    
    def action_help(self) -> None:
        self.notify("j/k:Move Tab:Switch Space:Connect s:Scan h:Hidden v:VPN d:Disconnect q:Quit", timeout=5)
