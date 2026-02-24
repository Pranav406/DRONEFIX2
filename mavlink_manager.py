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
    
    # EMA smoothing factor (0..1); smaller = smoother, slower to react
    _EMA_ALPHA = 0.04
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.connected = False
        self.telemetry_thread = None
        self.running = False
        
        # Thread safety for telemetry access
        self.telemetry_lock = threading.Lock()
        
        # Flag: once BATTERY_STATUS is received, ignore SYS_STATUS for
        # voltage/current because BATTERY_STATUS is more accurate (cell-level).
        self._has_battery_status = False
        
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
                
                # Battery status (basic) — fallback when BATTERY_STATUS is absent
                elif msg_type == 'SYS_STATUS':
                    with self.telemetry_lock:
                        # Only use SYS_STATUS when we have NOT received
                        # any BATTERY_STATUS yet (avoids flip-flop).
                        if not self._has_battery_status:
                            # battery_remaining: -1 means not available
                            if msg.battery_remaining not in (-1, 0):
                                self.telemetry['battery'] = max(0, min(100, msg.battery_remaining))

                        # Only use SYS_STATUS for voltage/current when we
                        # have NOT received any BATTERY_STATUS yet.
                        if not self._has_battery_status:
                            # voltage_battery is in millivolts; 0/65535 = invalid
                            if msg.voltage_battery not in (-1, 0, 65535) and msg.voltage_battery < 65535:
                                raw_v = msg.voltage_battery / 1000.0
                                self.telemetry['voltage'] = self._ema(
                                    self.telemetry['voltage'], raw_v
                                )
                            # current_battery is in centiamps; -1 = not available
                            if msg.current_battery not in (-1,) and msg.current_battery < 65535:
                                raw_a = msg.current_battery / 100.0
                                self.telemetry['current'] = self._ema(
                                    self.telemetry['current'], raw_a
                                )
                    updated = True

                # Detailed battery status (preferred — more accurate)
                elif msg_type == 'BATTERY_STATUS':
                    with self.telemetry_lock:
                        self._has_battery_status = True

                        # voltages[] is an array of cell voltages in mV
                        # UINT16_MAX (65535) = cell not present / invalid
                        cells = [v for v in msg.voltages if 0 < v < 65535]
                        if cells:
                            raw_v = sum(cells) / 1000.0
                            self.telemetry['voltage'] = self._ema(
                                self.telemetry['voltage'], raw_v
                            )

                        # current_battery is in centiamps (10 mA units); -1 = N/A
                        if msg.current_battery not in (-1,) and 0 <= msg.current_battery < 65535:
                            raw_a = msg.current_battery / 100.0
                            self.telemetry['current'] = self._ema(
                                self.telemetry['current'], raw_a
                            )
                            print(f"[MAVLink] BATTERY_STATUS raw_current={msg.current_battery} → {raw_a:.2f} A")

                        # battery_remaining: -1 = not sent; clamp 0-100
                        if msg.battery_remaining not in (-1,):
                            self.telemetry['battery'] = max(0, min(100, msg.battery_remaining))
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
    
    # ── helpers ──────────────────────────────────────────────────────
    def _ema(self, old_value, new_value):
        """Exponential Moving Average for smooth telemetry display.
        
        When `old_value` is 0 (first reading) the new value is taken as-is.
        """
        if old_value == 0.0:
            return new_value
        return old_value + self._EMA_ALPHA * (new_value - old_value)

    def get_telemetry(self):
        """Get current telemetry snapshot (thread-safe)"""
        with self.telemetry_lock:
            return self.telemetry.copy()
