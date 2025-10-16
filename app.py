"""Gazelle - Minimal NetworkManager TUI"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Button, DataTable, Select
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from network import *
import subprocess

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

class Gazelle(App):
    CSS = """
    PasswordScreen, HiddenNetworkScreen { align: center middle; }
    #dialog { width: 60; height: auto; border: thick $accent; background: $surface; padding: 1 2; }
    #title { text-style: bold; color: $accent; margin-bottom: 1; }
    .section { border: solid $accent; margin: 1 2; padding: 0 1; }
    .section-title { text-style: bold; color: $accent; background: $background; padding: 0 1; }
    #device-section, #station-section { height: 5; }
    Static { height: auto; }
    Input { height: 3; margin-bottom: 1; }
    Select { height: 3; margin-bottom: 1; }
    Horizontal { height: auto; margin-top: 1; }
    Button { min-width: 12; }
    """
    
    TITLE = "Gazelle"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("tab", "switch_section", "Switch"),
        Binding("space", "select", "Connect"),
        Binding("s", "scan", "Scan"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("h", "hidden", "Hidden"),
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
        self.query_one("#dev").add_columns("Name", "Mode", "Powered", "Address")
        self.query_one("#dev").cursor_type = "none"
        self.query_one("#sta").add_columns("State", "Scanning", "Frequency", "Security")
        self.query_one("#sta").cursor_type = "none"
        self.query_one("#known").add_columns("Name", "Security", "Signal")
        self.query_one("#new").add_columns("Name", "Security", "Signal")
        self.refresh_all()
        self.query_one("#new").focus()
    
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
        self.set_timer(2, self.refresh_all)
    
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
    
    def action_help(self) -> None:
        self.notify("j/k:Move Tab:Switch Space:Connect s:Scan h:Hidden d:Disconnect q:Quit", timeout=5)
