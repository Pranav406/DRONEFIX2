"""
MAVLink Manager - Handles connection and telemetry streaming
Implements QGroundControl-style mission protocol for ArduPilot
"""

import time
import threading
from pymavlink import mavutil
from PyQt5.QtCore import QObject, pyqtSignal
import serial.tools.list_ports


class MavlinkManager(QObject):
    """Manages MAVLink connection and telemetry"""
    
    # Signals for UI updates
    connection_status_changed = pyqtSignal(bool)
    telemetry_updated = pyqtSignal(dict)
    mission_upload_progress = pyqtSignal(str)
    mission_upload_complete = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.connected = False
        self.telemetry_thread = None
        self.running = False
        
        # Thread safety for telemetry access
        self.telemetry_lock = threading.Lock()
        
        # Latest telemetry data
        self.telemetry = {
            'lat': 0.0,
            'lon': 0.0,
            'alt': 0.0,
            'pitch': 0.0,
            'roll': 0.0,
            'yaw': 0.0,
            'battery': 0,
            'voltage': 0.0,
            'current': 0.0,
            'mode': 'Unknown',
            'armed': False
        }
        
    @staticmethod
    def scan_ports():
        """Scan for available COM ports"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        
        # Debug output
        print(f"[MAVLink] Scanning COM ports...")
        print(f"[MAVLink] Found {len(port_list)} ports: {port_list}")
        for port in ports:
            print(f"[MAVLink]   {port.device}: {port.description} - {port.hwid}")
        
        return port_list
    
    def connect(self, port, baudrate=57600, retries=3):
        """Connect to drone via MAVLink with retry logic"""
        for attempt in range(retries):
            try:
                print(f"[MAVLink] Connection attempt {attempt + 1}/{retries}...")
                print(f"[MAVLink] Connecting to {port} at {baudrate} baud...")
                
                self.connection = mavutil.mavlink_connection(
                    port,
                    baud=baudrate,
                    source_system=255
                )
                
                print(f"[MAVLink] Waiting for heartbeat (timeout: 10s)...")
                
                # Wait for heartbeat
                self.connection.wait_heartbeat(timeout=10)
                
                print(f"[MAVLink] Heartbeat received!")
                
                self.connected = True
                self.connection_status_changed.emit(True)
                
                # Start telemetry streaming thread
                self.running = True
                self.telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
                self.telemetry_thread.start()
                
                return True, "Connected successfully"
                
            except PermissionError as e:
                print(f"[MAVLink] Attempt {attempt + 1} - PermissionError: {str(e)}")
                if attempt < retries - 1:
                    print(f"[MAVLink] Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    self.connected = False
                    self.connection_status_changed.emit(False)
                    error_msg = (
                        f"Port {port} is already in use or requires admin access.\n\n"
                        "Try these solutions:\n"
                        "1. Close Mission Planner, QGroundControl, or any other GCS software\n"
                        "2. Unplug and reconnect the telemetry device\n"
                        "3. Try a different USB port\n"
                        "4. Run this application as Administrator (right-click → Run as admin)"
                    )
                    return False, error_msg
                    
            except Exception as e:
                print(f"[MAVLink] Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    print(f"[MAVLink] Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    self.connected = False
                    self.connection_status_changed.emit(False)
                    error_msg = f"Connection failed after {retries} attempts: {str(e)}"
                    print(f"[MAVLink] Connection error: {error_msg}")
                    return False, error_msg
    
    def disconnect(self):
        """Disconnect from drone"""
        self.running = False
        self.connected = False
        
        if self.telemetry_thread:
            self.telemetry_thread.join(timeout=2)
            
        if self.connection:
            self.connection.close()
            self.connection = None
            
        self.connection_status_changed.emit(False)
    
    def _telemetry_loop(self):
        """Background thread for receiving telemetry"""
        print("[MAVLink] Telemetry loop started")
        while self.running and self.connected:
            try:
                msg = self.connection.recv_match(blocking=True, timeout=1)
                
                if msg is None:
                    continue
                
                msg_type = msg.get_type()
                updated = False
                
                # GPS position
                if msg_type == 'GLOBAL_POSITION_INT':
                    with self.telemetry_lock:
                        self.telemetry['lat'] = msg.lat / 1e7
                        self.telemetry['lon'] = msg.lon / 1e7
                        self.telemetry['alt'] = msg.relative_alt / 1000.0
                    updated = True
                    print(f"[MAVLink] GPS: {self.telemetry['lat']:.6f}, {self.telemetry['lon']:.6f}, {self.telemetry['alt']:.2f}m")
                
                # Attitude (pitch, roll, yaw)
                elif msg_type == 'ATTITUDE':
                    with self.telemetry_lock:
                        self.telemetry['pitch'] = msg.pitch * 57.2958  # rad to deg
                        self.telemetry['roll'] = msg.roll * 57.2958
                        self.telemetry['yaw'] = msg.yaw * 57.2958
                    updated = True
                
                # Battery status (basic)
                elif msg_type == 'SYS_STATUS':
                    with self.telemetry_lock:
                        if msg.battery_remaining != -1:
                            self.telemetry['battery'] = msg.battery_remaining
                        # voltage_battery is in millivolts
                        if msg.voltage_battery not in (-1, 0, 65535):
                            self.telemetry['voltage'] = msg.voltage_battery / 1000.0
                        # current_battery is in 10*milliamperes (centiamps)
                        if msg.current_battery != -1:
                            self.telemetry['current'] = msg.current_battery / 100.0
                    updated = True
                
                # Detailed battery status (preferred over SYS_STATUS)
                elif msg_type == 'BATTERY_STATUS':
                    with self.telemetry_lock:
                        # voltages[] is an array of cell voltages in mV
                        # UINT16_MAX (65535) = cell not present
                        cells = [v for v in msg.voltages if v != 65535 and v > 0]
                        if cells:
                            self.telemetry['voltage'] = sum(cells) / 1000.0
                        if msg.current_battery != -1:
                            self.telemetry['current'] = msg.current_battery / 100.0
                        if msg.battery_remaining != -1:
                            self.telemetry['battery'] = msg.battery_remaining
                    updated = True
                
                # Heartbeat (mode and armed status)
                elif msg_type == 'HEARTBEAT':
                    with self.telemetry_lock:
                        self.telemetry['armed'] = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                        self.telemetry['mode'] = mavutil.mode_string_v10(msg)
                    updated = True
                    print(f"[MAVLink] Mode: {self.telemetry['mode']}, Armed: {self.telemetry['armed']}")
                
                # Emit signal for UI update when data changes
                if updated:
                    with self.telemetry_lock:
                        self.telemetry_updated.emit(self.telemetry.copy())
                
            except Exception as e:
                print(f"[MAVLink] Telemetry error: {e}")
                time.sleep(0.1)
        
        print("[MAVLink] Telemetry loop stopped")
    
    def get_telemetry(self):
        """Get current telemetry snapshot (thread-safe)"""
        with self.telemetry_lock:
            return self.telemetry.copy()
