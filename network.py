"""NetworkManager interface using nmcli"""
import subprocess
import re

def get_wifi_list():
    """Get list of available WiFi networks"""
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        networks = []
        seen_ssids = set()
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split(':')
            if len(parts) < 4:
                continue
                
            ssid = parts[0].strip()
            if not ssid or ssid in seen_ssids:
                continue
                
            seen_ssids.add(ssid)
            
            networks.append({
                'ssid': ssid,
                'signal': int(parts[1]) if parts[1] else 0,
                'security': parts[2],
                'connected': parts[3] == '*'
            })
        
        return sorted(networks, key=lambda x: x['signal'], reverse=True)
    
    except Exception as e:
        return []

def get_current_connection():
    """Get currently connected network"""
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active'],
            capture_output=True,
            text=True,
            check=True
        )
        connections = result.stdout.strip().split('\n')
        return connections[0] if connections and connections[0] else None
    except:
        return None

def connect_wifi(ssid, password):
    """Connect to regular WiFi network"""
    try:
        result = subprocess.run(
            ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

def connect_802_1x(ssid, username, password, auth_method='peap'):
    """Connect to 802.1X enterprise WiFi (eduroam)"""
    try:
        # Remove existing connection if it exists
        subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                      capture_output=True)
        
        # Create new 802.1X connection
        result = subprocess.run([
            'nmcli', 'connection', 'add',
            'type', 'wifi',
            'con-name', ssid,
            'ifname', 'wlan0',
            'ssid', ssid,
            'wifi-sec.key-mgmt', 'wpa-eap',
            '802-1x.eap', auth_method,
            '802-1x.phase2-auth', 'mschapv2',
            '802-1x.identity', username,
            '802-1x.password', password
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, result.stderr
        
        # Activate connection
        result = subprocess.run(
            ['nmcli', 'connection', 'up', ssid],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stderr or "Connected!"
    
    except Exception as e:
        return False, str(e)

def disconnect():
    """Disconnect from current network"""
    try:
        result = subprocess.run(
            ['nmcli', 'device', 'disconnect', 'wlan0'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def wifi_enabled():
    """Check if WiFi is enabled"""
    try:
        result = subprocess.run(
            ['nmcli', 'radio', 'wifi'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == 'enabled'
    except:
        return True

def toggle_wifi():
    """Toggle WiFi on/off"""
    try:
        enabled = wifi_enabled()
        state = 'off' if enabled else 'on'
        subprocess.run(['nmcli', 'radio', 'wifi', state])
        return not enabled
    except:
        return wifi_enabled()

def is_enterprise(security):
    """Check if network uses 802.1X"""
    return 'WPA-EAP' in security or '802.1X' in security
