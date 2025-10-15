"""Gazelle - A NetworkManager TUI"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Input, Button, Static
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.binding import Binding
from network import *

class PasswordScreen(ModalScreen):
    """Modal screen for entering WiFi password"""
    
    def __init__(self, ssid, is_enterprise=False):
        super().__init__()
        self.ssid = ssid
        self.is_enterprise = is_enterprise
    
    def compose(self) -> ComposeResult:
        if self.is_enterprise:
            yield Container(
                Static(f"Connect to: {self.ssid}", id="title"),
                Static("802.1X Enterprise Authentication", id="subtitle"),
                Label("Username:"),
                Input(placeholder="user@domain.com", id="username"),
                Label("Password:"),
                Input(placeholder="Password", password=True, id="password"),
                Label("Authentication: PEAP + MSCHAPv2"),
                Horizontal(
                    Button("Connect", variant="primary", id="connect"),
                    Button("Cancel", variant="default", id="cancel"),
                    classes="buttons"
                ),
                id="dialog"
            )
        else:
            yield Container(
                Static(f"Connect to: {self.ssid}", id="title"),
                Label("Password:"),
                Input(placeholder="Enter WiFi password", password=True, id="password"),
                Horizontal(
                    Button("Connect", variant="primary", id="connect"),
                    Button("Cancel", variant="default", id="cancel"),
                    classes="buttons"
                ),
                id="dialog"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "connect":
            if self.is_enterprise:
                username = self.query_one("#username", Input).value
                password = self.query_one("#password", Input).value
                if username and password:
                    self.dismiss((self.ssid, username, password, True))
            else:
                password = self.query_one("#password", Input).value
                if password:
                    self.dismiss((self.ssid, password, None, False))

class Gazelle(App):
    """A NetworkManager TUI"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #subtitle {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 1;
    }
    
    Input {
        margin: 1 0;
    }
    
    .buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    ListView {
        height: 100%;
        border: solid $accent;
    }
    
    ListItem {
        padding: 0 1;
    }
    
    ListItem.--highlight {
        background: $accent 20%;
    }
    
    #status {
        dock: top;
        height: 3;
        background: $surface;
        border: solid $accent;
        content-align: center middle;
        text-style: bold;
    }
    
    #network-container {
        height: 100%;
    }
    """
    
    TITLE = "Gazelle - NetworkManager TUI"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("space", "select", "Connect"),
        Binding("s", "scan", "Scan"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("ctrl+r", "toggle_wifi", "Toggle WiFi"),
        Binding("?", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="status")
        yield Container(
            ListView(id="networks"),
            id="network-container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_networks()
        self.update_status()
    
    def update_status(self) -> None:
        """Update status bar with current connection"""
        current = get_current_connection()
        wifi_state = "ON" if wifi_enabled() else "OFF"
        
        if current:
            status_text = f"📶 WiFi: {wifi_state} | Connected: {current}"
        else:
            status_text = f"📶 WiFi: {wifi_state} | Not connected"
        
        self.query_one("#status", Static).update(status_text)
    
    def refresh_networks(self) -> None:
        """Refresh the network list"""
        list_view = self.query_one("#networks", ListView)
        list_view.clear()
        
        networks = get_wifi_list()
        
        if not networks:
            list_view.append(ListItem(Label("No networks found. Press 's' to scan.")))
            return
        
        for net in networks:
            # Create signal strength bar
            signal_bars = int(net['signal'] / 20)
            bars = '█' * signal_bars + '░' * (5 - signal_bars)
            
            # Security indicator
            if net['security']:
                if is_enterprise(net['security']):
                    security_icon = "🔐"  # Enterprise
                else:
                    security_icon = "🔒"  # Regular encryption
            else:
                security_icon = "  "  # Open network
            
            # Connected indicator
            connected = "●" if net['connected'] else " "
            
            # Format
            label = f"{connected} {net['ssid']:30} {bars} {net['signal']:3}% {security_icon}"
            
            item = ListItem(Label(label))
            item.ssid = net['ssid']
            item.security = net['security']
            list_view.append(item)
    
    def action_cursor_down(self) -> None:
        """Move cursor down (j key)"""
        list_view = self.query_one(ListView)
        list_view.action_cursor_down()
    
    def action_cursor_up(self) -> None:
        """Move cursor up (k key)"""
        list_view = self.query_one(ListView)
        list_view.action_cursor_up()
    
    def action_scan(self) -> None:
        """Scan for networks (s key)"""
        self.notify("Scanning for networks...")
        # Trigger rescan
        subprocess.run(['nmcli', 'device', 'wifi', 'rescan'], capture_output=True)
        self.set_timer(2, self.refresh_networks)  # Refresh after 2 seconds
    
    def action_select(self) -> None:
        """Connect to selected network (space key)"""
        list_view = self.query_one(ListView)
        if not list_view.highlighted_child:
            return
        
        selected = list_view.highlighted_child
        if not hasattr(selected, 'ssid'):
            return
        
        ssid = selected.ssid
        security = selected.security
        
        # Check if enterprise network
        if is_enterprise(security):
            self.push_screen(PasswordScreen(ssid, is_enterprise=True), self.handle_connect)
        elif security:  # Regular encrypted network
            self.push_screen(PasswordScreen(ssid, is_enterprise=False), self.handle_connect)
        else:  # Open network
            self.notify(f"Connecting to {ssid}...")
            success, message = connect_wifi(ssid, "")
            if success:
                self.notify(f"✓ Connected to {ssid}", severity="information")
            else:
                self.notify(f"✗ Failed: {message}", severity="error")
            self.refresh_networks()
            self.update_status()
    
    def handle_connect(self, result) -> None:
        """Handle connection result from password screen"""
        if not result:
            return
        
        ssid, password, username, is_enterprise = result
        
        self.notify(f"Connecting to {ssid}...")
        
        if is_enterprise:
            success, message = connect_802_1x(ssid, username, password)
        else:
            success, message = connect_wifi(ssid, password)
        
        if success:
            self.notify(f"✓ Connected to {ssid}", severity="information")
        else:
            self.notify(f"✗ Connection failed: {message}", severity="error")
        
        self.refresh_networks()
        self.update_status()
    
    def action_disconnect(self) -> None:
        """Disconnect from current network (d key)"""
        if disconnect():
            self.notify("Disconnected", severity="information")
        else:
            self.notify("Not connected", severity="warning")
        self.refresh_networks()
        self.update_status()
    
    def action_toggle_wifi(self) -> None:
        """Toggle WiFi on/off (Ctrl+R)"""
        enabled = toggle_wifi()
        state = "ON" if enabled else "OFF"
        self.notify(f"WiFi turned {state}", severity="information")
        self.set_timer(1, self.refresh_networks)
        self.update_status()
    
    def action_help(self) -> None:
        """Show help (? key)"""
        help_text = """
        Gazelle Keybindings:
        
        j / ↓     - Move down
        k / ↑     - Move up
        Space     - Connect to network
        s         - Scan for networks
        d         - Disconnect
        Ctrl+R    - Toggle WiFi on/off
        q         - Quit
        ?         - Show this help
        """
        self.notify(help_text, timeout=10)
