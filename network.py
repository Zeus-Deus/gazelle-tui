"""NetworkManager interface"""
import subprocess

def get_wifi_interface():
    """Auto-detect WiFi interface"""
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'DEVICE,TYPE', 'device'],
                               capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if ':wifi' in line:
                return line.split(':')[0]
    except:
        pass
    return 'wlan0'

def get_wifi_list():
    """Get available WiFi networks"""
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True, text=True, check=True)
        
        networks, seen = [], set()
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 4 and parts[0] and parts[0] not in seen:
                seen.add(parts[0])
                networks.append({
                    'ssid': parts[0],
                    'signal': int(parts[1]) if parts[1] else 0,
                    'security': parts[2],
                    'connected': parts[3] == '*'
                })
        return sorted(networks, key=lambda x: x['signal'], reverse=True)
    except:
        return []

def get_current_connection():
    """Get active connection name"""
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active'],
                               capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')[0] or None
    except:
        return None

def get_station_info():
    """Get station status"""
    try:
        current = get_current_connection()
        info = {'state': 'connected' if current else 'disconnected', 
                'scanning': 'false', 'frequency': '-', 'security': '-'}
        
        if current:
            result = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SSID,FREQ,SECURITY', 
                                    'device', 'wifi', 'list'], capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if line.startswith('yes:') or line.startswith('*:'):
                    parts = line.split(':')
                    if len(parts) >= 4:
                        info['frequency'] = parts[2] or '-'
                        info['security'] = parts[3] or '-'
                    break
        return info
    except:
        return {'state': 'disconnected', 'scanning': 'false', 'frequency': '-', 'security': '-'}

def connect_wifi(ssid, password, hidden=False):
    """Connect to WiFi (supports hidden SSIDs)"""
    try:
        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid]
        if password:
            cmd.extend(['password', password])
        if hidden:
            cmd.append('hidden')
            cmd.append('yes')
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # If connection failed, delete the connection profile that was created
        if result.returncode != 0:
            subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                          capture_output=True, text=True)
        
        return result.returncode == 0, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

def connect_802_1x(ssid, username, password, eap_method="peap", phase2_auth="mschapv2", hidden=False):
    """Connect to 802.1X enterprise WiFi (supports hidden SSIDs)
    
    Supports:
    - EAP: peap, ttls, tls
    - Phase2: mschapv2, mschap, pap, chap, gtc, md5
    - Hidden SSID networks
    """
    try:
        iface = get_wifi_interface()
        subprocess.run(['nmcli', 'connection', 'delete', ssid], capture_output=True)
        
        # Build command based on EAP method
        cmd = [
            'nmcli', 'connection', 'add', 'type', 'wifi', 'con-name', ssid,
            'ifname', iface, 'ssid', ssid, 'wifi-sec.key-mgmt', 'wpa-eap',
            '802-1x.eap', eap_method.lower(), '802-1x.identity', username
        ]
        
        # Add hidden SSID support
        if hidden:
            cmd.extend(['wifi.hidden', 'yes'])
        
        # Add auth-specific parameters
        if eap_method.lower() in ['peap', 'ttls']:
            # PEAP and TTLS use phase2 auth + password
            cmd.extend(['802-1x.phase2-auth', phase2_auth.lower()])
            cmd.extend(['802-1x.password', password])
        elif eap_method.lower() == 'tls':
            # TLS uses certificates (for now, treat password as private key password)
            cmd.extend(['802-1x.private-key-password', password])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, result.stderr
        
        result = subprocess.run(['nmcli', 'connection', 'up', ssid],
                               capture_output=True, text=True)
        
        # If connection failed, delete the connection profile that was created
        if result.returncode != 0:
            subprocess.run(['nmcli', 'connection', 'delete', ssid], 
                          capture_output=True, text=True)
        
        return result.returncode == 0, result.stderr or "Connected"
    except Exception as e:
        return False, str(e)

def disconnect():
    """Disconnect from network"""
    try:
        result = subprocess.run(['nmcli', 'device', 'disconnect', get_wifi_interface()],
                               capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def wifi_enabled():
    """Check if WiFi is enabled"""
    try:
        result = subprocess.run(['nmcli', 'radio', 'wifi'], capture_output=True, text=True)
        return result.stdout.strip() == 'enabled'
    except:
        return True

def toggle_wifi():
    """Toggle WiFi on/off"""
    try:
        enabled = wifi_enabled()
        subprocess.run(['nmcli', 'radio', 'wifi', 'off' if enabled else 'on'])
        return not enabled
    except:
        return wifi_enabled()

def is_enterprise(security):
    """Check if network is 802.1X"""
    return 'WPA-EAP' in security or '802.1X' in security

def is_owe(security):
    """Check if network uses OWE (Enhanced Open / WPA3-OWE)"""
    return 'OWE' in security or 'WPA3-OWE' in security

def get_vpn_list():
    """Get all VPN connections configured in NetworkManager"""
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                               capture_output=True, text=True, check=True)
        active_vpn = get_active_vpn()
        vpns = []
        for line in result.stdout.strip().split('\n'):
            if ':vpn' in line:
                name = line.split(':')[0]
                vpns.append({
                    'name': name,
                    'active': name == active_vpn
                })
        return sorted(vpns, key=lambda x: (not x['active'], x['name']))
    except:
        return []

def get_active_vpn():
    """Get currently active VPN connection name"""
    try:
        result = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'],
                               capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if ':vpn' in line:
                return line.split(':')[0]
        return None
    except:
        return None

def connect_vpn(name):
    """Connect to VPN by name"""
    try:
        result = subprocess.run(['nmcli', 'connection', 'up', name],
                               capture_output=True, text=True)
        return result.returncode == 0, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

def disconnect_vpn(name):
    """Disconnect VPN by name"""
    try:
        result = subprocess.run(['nmcli', 'connection', 'down', name],
                               capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False
