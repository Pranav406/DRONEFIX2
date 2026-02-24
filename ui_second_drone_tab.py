"""
Second Drone Tab - Rescue/Response Drone Management
Manages waypoint generation from detected humans and mission control for second drone
"""

import os
import folium
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QSplitter, QGridLayout, QComboBox,
    QMessageBox, QListWidgetItem, QTextEdit, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
from mission_upload import upload_mission_to_drone


class SecondDroneTab(QWidget):
    """Tab for managing second drone (rescue/response drone)"""
    
    def __init__(self, mavlink_manager_drone1, priority_tab=None):
        super().__init__()
        self.mavlink_manager_drone1 = mavlink_manager_drone1  # First drone connection
        self.priority_tab = priority_tab
        
        # Thread safety for waypoint management
        import threading
        self.waypoints_lock = threading.Lock()
        
        # Second drone connection (separate MAVLink connection)
        self.mavlink_manager_drone2 = None
        self.drone2_port =  None
        
        # Waypoint management
        self.rescue_waypoints = []  # List of (lat, lon, alt, description)
        self.mission_altitude = 30  # Default altitude for rescue mission
        
        # UI state
        self.is_connected = False
        
        self.init_ui()
        
        # Map update timer
        self.map_timer = QTimer()
        self.map_timer.timeout.connect(self.update_live_map)
        self.map_timer.start(2000)  # Update every 2 seconds
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("🚁 Second Drone - Rescue/Response Operations")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        main_layout.addWidget(header)
        
        # Info
        info = QLabel(
            "Automatically generates rescue waypoints from detected human coordinates. "
            "Second drone visits priority locations for rescue operations."
        )
        info.setStyleSheet("color: #aaaaaa; font-size: 11px; margin-bottom: 5px;")
        info.setWordWrap(True)
        main_layout.addWidget(info)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Connection, Waypoints, Mission Control
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Telemetry and Live Map
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create left panel with connection and mission control"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Connection group
        conn_group = QGroupBox("🔌 Second Drone Connection")
        conn_layout = QGridLayout(conn_group)
        
        # COM port selection
        port_label = QLabel("COM Port:")
        port_label.setStyleSheet("color: #ffffff;")
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        conn_layout.addWidget(port_label, 0, 0)
        conn_layout.addWidget(self.port_combo, 0, 1)
        
        scan_btn = QPushButton("🔍 Scan")
        scan_btn.clicked.connect(self.scan_ports)
        conn_layout.addWidget(scan_btn, 0, 2)
        
        # Connect button
        self.connect_btn = QPushButton("🔌 Connect Drone 2")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet(self._button_style("#4a90e2"))
        conn_layout.addWidget(self.connect_btn, 1, 0, 1, 3)
        
        # Connection status
        self.conn_status_label = QLabel("⚫ Not Connected")
        self.conn_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        conn_layout.addWidget(self.conn_status_label, 2, 0, 1, 3)
        
        layout.addWidget(conn_group)
        
        # Waypoint generation group
        waypoint_gen_group = QGroupBox("📍 Rescue Waypoint Generation")
        waypoint_gen_layout = QVBoxLayout(waypoint_gen_group)
        
        # Altitude setting
        alt_layout = QHBoxLayout()
        alt_label = QLabel("Mission Altitude (m):")
        alt_label.setStyleSheet("color: #ffffff;")
        self.altitude_spin = QSpinBox()
        self.altitude_spin.setRange(5, 120)
        self.altitude_spin.setValue(30)
        self.altitude_spin.valueChanged.connect(self.update_mission_altitude)
        alt_layout.addWidget(alt_label)
        alt_layout.addWidget(self.altitude_spin)
        alt_layout.addStretch()
        waypoint_gen_layout.addLayout(alt_layout)
        
        # Generate from priority list
        gen_btn = QPushButton("🎯 Generate from Priority List")
        gen_btn.clicked.connect(self.generate_waypoints_from_priority)
        gen_btn.setStyleSheet(self._button_style("#27ae60"))
        waypoint_gen_layout.addWidget(gen_btn)
        
        # Add takeoff/RTL options
        self.add_takeoff_check = QCheckBox("Add Takeoff Waypoint")
        self.add_takeoff_check.setChecked(True)
        self.add_rtl_check = QCheckBox("Add Return-to-Launch (RTL)")
        self.add_rtl_check.setChecked(True)
        waypoint_gen_layout.addWidget(self.add_takeoff_check)
        waypoint_gen_layout.addWidget(self.add_rtl_check)
        
        # Waypoint count
        self.waypoint_count_label = QLabel("Waypoints: 0")
        self.waypoint_count_label.setStyleSheet("color: #4a90e2; font-weight: bold;")
        waypoint_gen_layout.addWidget(self.waypoint_count_label)
        
        layout.addWidget(waypoint_gen_group)
        
        # Waypoint list group
        waypoint_list_group = QGroupBox("📋 Rescue Mission Waypoints")
        waypoint_list_layout = QVBoxLayout(waypoint_list_group)
        
        self.waypoint_list = QListWidget()
        self.waypoint_list.setAlternatingRowColors(True)
        self.waypoint_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        waypoint_list_layout.addWidget(self.waypoint_list)
        
        # Waypoint controls
        wp_controls = QHBoxLayout()
        
        clear_wp_btn = QPushButton("🗑️ Clear")
        clear_wp_btn.clicked.connect(self.clear_waypoints)
        clear_wp_btn.setStyleSheet(self._button_style("#e74c3c"))
        wp_controls.addWidget(clear_wp_btn)
        
        upload_btn = QPushButton("🚀 Upload to Drone 2")
        upload_btn.clicked.connect(self.upload_mission)
        upload_btn.setStyleSheet(self._button_style("#f39c12"))
        wp_controls.addWidget(upload_btn)
        
        waypoint_list_layout.addLayout(wp_controls)
        
        layout.addWidget(waypoint_list_group, 1)
        
        return panel
    
    def create_right_panel(self):
        """Create right panel with telemetry and map"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Telemetry group
        telemetry_group = QGroupBox("📊 Second Drone Telemetry")
        telemetry_layout = QGridLayout(telemetry_group)
        
        # Create telemetry labels
        labels = [
            ("Latitude:", "lat"),
            ("Longitude:", "lon"),
            ("Altitude:", "alt"),
            ("Pitch:", "pitch"),
            ("Roll:", "roll"),
            ("Yaw:", "yaw"),
            ("Battery:", "battery"),
            ("Mode:", "mode"),
            ("Armed:", "armed"),
        ]
        
        self.telemetry_labels = {}
        
        for i, (label_text, key) in enumerate(labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; color: #ffffff;")
            
            value = QLabel("--")
            value.setStyleSheet("color: #4a90e2;")
            
            telemetry_layout.addWidget(label, i, 0)
            telemetry_layout.addWidget(value, i, 1)
            
            self.telemetry_labels[key] = value
        
        layout.addWidget(telemetry_group)
        
        # Live map group
        map_group = QGroupBox("🗺️ Live Tracking - Both Drones")
        map_layout = QVBoxLayout(map_group)
        
        self.live_map_view = QWebEngineView()
        self.live_map_view.setMinimumHeight(200)
        map_layout.addWidget(self.live_map_view)
        
        # Map legend
        legend = QLabel(
            "🔴 Drone 1 (Surveillance) | 🟢 Drone 2 (Rescue) | 🟠 Detected Persons"
        )
        legend.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        map_layout.addWidget(legend)
        
        layout.addWidget(map_group, 1)
        
        # Mission status
        self.mission_status = QTextEdit()
        self.mission_status.setReadOnly(True)
        self.mission_status.setMaximumHeight(100)
        self.mission_status.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #3d3d3d;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        self.mission_status.setPlaceholderText("Mission status logs...")
        layout.addWidget(self.mission_status)
        
        # Initialize map
        self.init_live_map()
        
        return panel
    
    def _button_style(self, color):
        """Generate button stylesheet"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
        """
    
    def scan_ports(self):
        """Scan for available COM ports"""
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        self.port_combo.clear()
        
        if ports:
            for port in ports:
                self.port_combo.addItem(f"{port.device} - {port.description}")
            self.log_status(f"Found {len(ports)} COM port(s)")
        else:
            self.log_status("No COM ports detected")
            QMessageBox.warning(self, "No Ports", "No COM ports detected. Check drone connection.")
    
    def toggle_connection(self):
        """Connect or disconnect second drone"""
        if not self.is_connected:
            # Connect
            port_text = self.port_combo.currentText()
            if not port_text:
                QMessageBox.warning(self, "No Port", "Please scan and select a COM port first.")
                return
            
            port = port_text.split(" - ")[0]
            
            # Create second MAVLink manager
            from mavlink_manager import MavlinkManager
            self.mavlink_manager_drone2 = MavlinkManager()
            
            success = self.mavlink_manager_drone2.connect(port)
            
            if success:
                self.is_connected = True
                self.conn_status_label.setText("🟢 Drone 2 Connected")
                self.conn_status_label.setStyleSheet("color: #44ff44; font-weight: bold;")
                self.connect_btn.setText("🔌 Disconnect Drone 2")
                self.connect_btn.setStyleSheet(self._button_style("#e74c3c"))
                self.log_status(f"✓ Connected to Drone 2 on {port}")
                
                # Connect telemetry updates
                self.mavlink_manager_drone2.telemetry_updated.connect(self.update_telemetry)
            else:
                QMessageBox.critical(self, "Connection Failed", 
                                   f"Failed to connect to Drone 2 on {port}")
        else:
            # Disconnect
            if self.mavlink_manager_drone2:
                self.mavlink_manager_drone2.disconnect()
                self.mavlink_manager_drone2 = None
            
            # Clear telemetry display
            for label in self.telemetry_labels.values():
                label.setText("--")
            
            self.is_connected = False
            self.conn_status_label.setText("⚫ Not Connected")
            self.conn_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
            self.connect_btn.setText("🔌 Connect Drone 2")
            self.connect_btn.setStyleSheet(self._button_style("#4a90e2"))
            self.log_status("✗ Disconnected from Drone 2")
    
    def update_mission_altitude(self, value):
        """Update mission altitude"""
        self.mission_altitude = value
    
    def generate_waypoints_from_priority(self):
        """Generate rescue waypoints from priority list"""
        if not self.priority_tab:
            QMessageBox.warning(self, "No Priority Data", 
                              "Priority tab not available.")
            return
        
        # Get priority items with GPS coordinates
        priority_items = self.priority_tab.priority_items
        
        if not priority_items:
            QMessageBox.information(self, "No Detections", 
                                  "No detected persons in priority list yet.")
            return
        
        # Clear existing waypoints
        self.rescue_waypoints.clear()
        
        # Generate waypoints from high-priority items
        generated_count = 0
        
        for item in priority_items:
            if item.gps_coords:
                lat, lon = item.gps_coords
                description = f"Person #{item.tracker_id} - {item.condition}"
                
                # Add waypoint
                self.rescue_waypoints.append({
                    'lat': lat,
                    'lon': lon,
                    'alt': self.mission_altitude,
                    'description': description,
                    'priority_score': item.priority_score,
                    'condition': item.condition
                })
                generated_count += 1
        
        if generated_count == 0:
            QMessageBox.information(self, "No GPS Data", 
                                  "No GPS coordinates available in priority items.")
            return
        
        # Sort by priority score (highest first)
        self.rescue_waypoints.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Update display
        self.update_waypoint_list()
        
        self.log_status(f"✓ Generated {generated_count} rescue waypoint(s) from priority list")
        QMessageBox.information(self, "Waypoints Generated", 
                              f"Generated {generated_count} rescue waypoint(s)\n"
                              f"Sorted by priority (highest first)")
    
    def update_waypoint_list(self):
        """Update waypoint list display"""
        self.waypoint_list.clear()
        
        for i, wp in enumerate(self.rescue_waypoints, 1):
            wp_text = (f"{i}. [{wp['priority_score']}] {wp['description']}\n"
                      f"    GPS: {wp['lat']:.6f}, {wp['lon']:.6f} @ {wp['alt']}m")
            
            item = QListWidgetItem(wp_text)
            
            # Color code by condition
            if wp['condition'] == 'Critical':
                item.setForeground(QColor(255, 100, 100))
            elif wp['condition'] == 'Warning':
                item.setForeground(QColor(255, 180, 0))
            else:
                item.setForeground(QColor(100, 255, 100))
            
            self.waypoint_list.addItem(item)
        
        self.waypoint_count_label.setText(f"Waypoints: {len(self.rescue_waypoints)}")
        
        # Update map
        self.update_live_map()
    
    def clear_waypoints(self):
        """Clear all waypoints"""
        if not self.rescue_waypoints:
            return
        
        reply = QMessageBox.question(
            self, "Clear Waypoints",
            f"Clear all {len(self.rescue_waypoints)} waypoint(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.rescue_waypoints.clear()
            self.update_waypoint_list()
            self.log_status("✓ Cleared all waypoints")
    
    def upload_mission(self):
        """Upload mission to second drone"""
        if not self.is_connected or not self.mavlink_manager_drone2:
            QMessageBox.warning(self, "Not Connected", 
                              "Please connect to Drone 2 first.")
            return
        
        if not self.rescue_waypoints:
            QMessageBox.warning(self, "No Waypoints", 
                              "No waypoints to upload. Generate waypoints first.")
            return
        
        # Confirm upload
        reply = QMessageBox.question(
            self, "Upload Mission",
            f"Upload {len(self.rescue_waypoints)} rescue waypoint(s) to Drone 2?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Build mission waypoints
        mission_waypoints = []
        
        # Add takeoff if requested
        if self.add_takeoff_check.isChecked() and self.rescue_waypoints:
            first_wp = self.rescue_waypoints[0]
            mission_waypoints.append({
                'command': 'TAKEOFF',
                'lat': first_wp['lat'],
                'lon': first_wp['lon'],
                'alt': self.mission_altitude
            })
        
        # Add rescue waypoints
        for wp in self.rescue_waypoints:
            mission_waypoints.append({
                'command': 'WAYPOINT',
                'lat': wp['lat'],
                'lon': wp['lon'],
                'alt': wp['alt']
            })
        
        # Add RTL if requested
        if self.add_rtl_check.isChecked():
            mission_waypoints.append({'command': 'RTL'})
        
        # Upload mission
        self.log_status(f"Uploading {len(mission_waypoints)} waypoint(s) to Drone 2...")
        
        try:
            success = upload_mission_to_drone(
                self.mavlink_manager_drone2,
                mission_waypoints
            )
            
            if success:
                self.log_status("✓ Mission uploaded successfully to Drone 2!")
                QMessageBox.information(self, "Upload Success", 
                                      f"Mission with {len(mission_waypoints)} waypoint(s) "
                                      f"uploaded to Drone 2 successfully!")
            else:
                self.log_status("✗ Mission upload failed")
                QMessageBox.warning(self, "Upload Failed", 
                                  "Mission upload failed. Check connection and try again.")
        except Exception as e:
            self.log_status(f"✗ Upload error: {str(e)}")
            QMessageBox.critical(self, "Upload Error", f"Error uploading mission:\n{str(e)}")
    
    def update_telemetry(self, telemetry):
        """Update telemetry display for second drone"""
        self.telemetry_labels['lat'].setText(f"{telemetry['lat']:.6f}°")
        self.telemetry_labels['lon'].setText(f"{telemetry['lon']:.6f}°")
        self.telemetry_labels['alt'].setText(f"{telemetry['alt']:.1f} m")
        self.telemetry_labels['pitch'].setText(f"{telemetry['pitch']:.1f}°")
        self.telemetry_labels['roll'].setText(f"{telemetry['roll']:.1f}°")
        self.telemetry_labels['yaw'].setText(f"{telemetry['yaw']:.1f}°")
        self.telemetry_labels['battery'].setText(f"{telemetry['battery']}%")
        self.telemetry_labels['mode'].setText(telemetry['mode'])
        self.telemetry_labels['armed'].setText("Yes" if telemetry['armed'] else "No")
    
    def init_live_map(self):
        """Initialize empty live map"""
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        html_path = os.path.join(os.path.dirname(__file__), 'temp_second_drone_map.html')
        m.save(html_path)
        self.live_map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def update_live_map(self):
        """Update live map with both drones and waypoints"""
        # Get telemetry from first drone
        telemetry1 = self.mavlink_manager_drone1.get_telemetry()
        lat1 = telemetry1.get('lat', 0)
        lon1 = telemetry1.get('lon', 0)
        
        # Get telemetry from second drone if connected
        lat2, lon2 = 0, 0
        if self.is_connected and self.mavlink_manager_drone2:
            telemetry2 = self.mavlink_manager_drone2.get_telemetry()
            lat2 = telemetry2.get('lat', 0)
            lon2 = telemetry2.get('lon', 0)
        
        # Determine map center
        if lat1 != 0 and lon1 != 0:
            center_lat, center_lon = lat1, lon1
            zoom = 16
        elif lat2 != 0 and lon2 != 0:
            center_lat, center_lon = lat2, lon2
            zoom = 16
        elif self.rescue_waypoints:
            first_wp = self.rescue_waypoints[0]
            center_lat, center_lon = first_wp['lat'], first_wp['lon']
            zoom = 16
        else:
            center_lat, center_lon = 0, 0
            zoom = 2
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
        
        # Add first drone marker (red)
        if lat1 != 0 and lon1 != 0:
            folium.Marker(
                [lat1, lon1],
                popup=f"Drone 1 (Surveillance)<br>Alt: {telemetry1['alt']:.1f}m",
                tooltip="Drone 1",
                icon=folium.Icon(color='red', icon='plane', prefix='fa')
            ).add_to(m)
        
        # Add second drone marker (green)
        if lat2 != 0 and lon2 != 0:
            folium.Marker(
                [lat2, lon2],
                popup=f"Drone 2 (Rescue)<br>Alt: {telemetry2['alt']:.1f}m",
                tooltip="Drone 2",
                icon=folium.Icon(color='green', icon='helicopter', prefix='fa')
            ).add_to(m)
        
        # Add rescue waypoints (orange markers)
        for i, wp in enumerate(self.rescue_waypoints, 1):
            folium.Marker(
                [wp['lat'], wp['lon']],
                popup=f"WP{i}: {wp['description']}<br>Alt: {wp['alt']}m",
                tooltip=f"Waypoint {i}",
                icon=folium.Icon(color='orange', icon='user', prefix='fa')
            ).add_to(m)
        
        # Draw route line between waypoints
        if self.rescue_waypoints:
            route_coords = [[wp['lat'], wp['lon']] for wp in self.rescue_waypoints]
            folium.PolyLine(
                route_coords,
                color='orange',
                weight=3,
                opacity=0.7,
                popup='Rescue Route'
            ).add_to(m)
        
        # Save and load map
        html_path = os.path.join(os.path.dirname(__file__), 'temp_second_drone_map.html')
        m.save(html_path)
        self.live_map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def log_status(self, message):
        """Log message to mission status"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.mission_status.append(f"[{timestamp}] {message}")
