"""
Mission Planner Tab - KML upload, waypoint configuration, and mission upload
"""

import os
import folium
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QCheckBox, QGroupBox,
                             QComboBox, QSpinBox, QTextEdit, QSplitter,
                             QMessageBox, QProgressBar, QScrollArea, QRadioButton,
                             QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from kml_parser import KMLParser, WaypointConverter
from mission_upload import MissionUploader


class MissionUploadThread(QThread):
    """Background thread for mission upload"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, uploader, waypoints, add_takeoff, add_rtl):
        super().__init__()
        self.uploader = uploader
        self.waypoints = waypoints
        self.add_takeoff = add_takeoff
        self.add_rtl = add_rtl
    
    def run(self):
        """Execute mission upload"""
        success, message = self.uploader.upload_mission(
            self.waypoints,
            self.add_takeoff,
            self.add_rtl
        )
        self.finished.emit(success, message)


class MissionPlannerTab(QWidget):
    """Tab for mission planning and waypoint upload"""
    
    def __init__(self, mavlink_manager):
        super().__init__()
        self.mavlink_manager = mavlink_manager
        self.mission_uploader = MissionUploader(mavlink_manager)
        
        self.kml_file_path = None
        self.waypoints = []
        self.raw_coordinates = []
        self.is_polygon = False  # Track if KML is a polygon for area scan
        
        self.init_ui()
        self.apply_stylesheet()
        
        # Auto-scan ports on startup
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, self.scan_ports)
        
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QHBoxLayout(self)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        
        # Right panel - Map preview
        right_panel = self.create_right_panel()
        
        # Splitter - Give more space to map (responsive)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)  # Map gets 2x more space (1:2 ratio)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create left control panel"""
        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(200)
        
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)  # Compact spacing
        
        # Title
        title = QLabel("Mission Planner")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a90e2;")
        layout.addWidget(title)
        
        # KML Upload Section
        kml_group = self.create_kml_section()
        layout.addWidget(kml_group)
        
        # Mission Options Section
        options_group = self.create_options_section()
        layout.addWidget(options_group)
        
        # Connection Section
        connection_group = self.create_connection_section()
        layout.addWidget(connection_group)
        
        # Telemetry Display Section
        telemetry_group = self.create_telemetry_section()
        layout.addWidget(telemetry_group)
        
        # Mission Upload Section
        upload_group = self.create_upload_section()
        layout.addWidget(upload_group)
        
        # Status Log
        log_label = QLabel("Status Log:")
        layout.addWidget(log_label)
        
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMaximumHeight(100)
        self.status_log.setPlaceholderText("Status messages will appear here...")
        layout.addWidget(self.status_log)
        
        # Debug Log (expandable)
        debug_label = QLabel("Debug Log:")
        layout.addWidget(debug_label)
        
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setMaximumHeight(100)
        self.debug_log.setPlaceholderText("Debug information...")
        self.debug_log.setStyleSheet("background-color: #1a1a1a; color: #00ff00; font-family: 'Consolas', monospace; font-size: 12px;")
        layout.addWidget(self.debug_log)
        
        layout.addStretch()
        
        scroll.setWidget(panel)
        return scroll
    
    def create_kml_section(self):
        """Create KML upload section"""
        group = QGroupBox("1. KML Route File")
        layout = QVBoxLayout(group)
        
        # File selector
        file_layout = QHBoxLayout()
        
        self.kml_label = QLabel("No file selected")
        self.kml_label.setStyleSheet("color: #888;")
        
        self.upload_btn = QPushButton("📁 Browse KML")
        self.upload_btn.clicked.connect(self.upload_kml)
        
        file_layout.addWidget(self.kml_label, 1)
        file_layout.addWidget(self.upload_btn)
        
        layout.addLayout(file_layout)
        
        # Waypoint info
        self.waypoint_info = QLabel("Waypoints: 0 | Distance: 0 m")
        self.waypoint_info.setStyleSheet("color: #4a90e2; font-weight: bold;")
        layout.addWidget(self.waypoint_info)
        
        return group
    
    def create_options_section(self):
        """Create mission options section"""
        group = QGroupBox("2. Mission Options")
        layout = QVBoxLayout(group)
        
        # Altitude setting
        alt_layout = QHBoxLayout()
        alt_label = QLabel("Waypoint Altitude:")
        self.altitude_spin = QSpinBox()
        self.altitude_spin.setRange(5, 120)
        self.altitude_spin.setValue(10)
        self.altitude_spin.setSuffix(" m")
        self.altitude_spin.valueChanged.connect(self.update_mission)
        alt_layout.addWidget(alt_label)
        alt_layout.addWidget(self.altitude_spin)
        layout.addLayout(alt_layout)
        
        # Mission mode selector
        mode_label = QLabel("Mission Mode:")
        mode_label.setStyleSheet("font-weight: bold; color: #4a90e2; margin-top: 5px;")
        layout.addWidget(mode_label)
        
        self.route_mode_radio = QRadioButton("Route Mode (waypoint path)")
        self.route_mode_radio.setChecked(True)
        self.route_mode_radio.toggled.connect(self.update_mission)
        
        self.area_scan_radio = QRadioButton("Area Scan (lawnmower coverage)")
        self.area_scan_radio.toggled.connect(self.update_mission)
        
        layout.addWidget(self.route_mode_radio)
        layout.addWidget(self.area_scan_radio)
        
        # Area scan options
        self.area_scan_group = QWidget()
        area_scan_layout = QVBoxLayout(self.area_scan_group)
        area_scan_layout.setContentsMargins(20, 0, 0, 0)
        
        sweep_layout = QHBoxLayout()
        sweep_label = QLabel("Sweep Spacing: (beta)")
        self.sweep_spacing_spin = QSpinBox()
        self.sweep_spacing_spin.setRange(3, 50)
        self.sweep_spacing_spin.setValue(10)
        self.sweep_spacing_spin.setSuffix(" m")
        self.sweep_spacing_spin.valueChanged.connect(self.update_mission)
        sweep_layout.addWidget(sweep_label)
        sweep_layout.addWidget(self.sweep_spacing_spin)
        area_scan_layout.addLayout(sweep_layout)
        
        # Waypoint spacing control
        waypoint_spacing_layout = QHBoxLayout()
        waypoint_spacing_label = QLabel("Waypoint Spacing:")
        self.waypoint_spacing_spin = QSpinBox()
        self.waypoint_spacing_spin.setRange(3, 30)
        self.waypoint_spacing_spin.setValue(10)
        self.waypoint_spacing_spin.setSuffix(" m")
        self.waypoint_spacing_spin.setToolTip("Distance between waypoints (smaller = more waypoints)")
        self.waypoint_spacing_spin.valueChanged.connect(self.update_mission)
        waypoint_spacing_layout.addWidget(waypoint_spacing_label)
        waypoint_spacing_layout.addWidget(self.waypoint_spacing_spin)
        area_scan_layout.addLayout(waypoint_spacing_layout)
        
        angle_layout = QHBoxLayout()
        angle_label = QLabel("Sweep Angle:")
        self.sweep_angle_spin = QSpinBox()
        self.sweep_angle_spin.setRange(0, 180)
        self.sweep_angle_spin.setValue(0)
        self.sweep_angle_spin.setSuffix(" °")
        self.sweep_angle_spin.valueChanged.connect(self.update_mission)
        angle_layout.addWidget(angle_label)
        angle_layout.addWidget(self.sweep_angle_spin)
        area_scan_layout.addLayout(angle_layout)
        
        self.area_scan_group.setEnabled(False)
        layout.addWidget(self.area_scan_group)
        
        # General checkboxes
        self.takeoff_checkbox = QCheckBox("Add Takeoff waypoint at start")
        self.takeoff_checkbox.setChecked(True)
        
        self.rtl_checkbox = QCheckBox("Add Return-to-Launch (RTL) at end")
        self.rtl_checkbox.setChecked(True)
        
        layout.addWidget(self.takeoff_checkbox)
        layout.addWidget(self.rtl_checkbox)
        
        # Route mode smoothing options
        self.route_smooth_group = QWidget()
        route_smooth_layout = QVBoxLayout(self.route_smooth_group)
        route_smooth_layout.setContentsMargins(20, 0, 0, 0)
        
        self.smooth_checkbox = QCheckBox("Smooth waypoint spacing")
        self.smooth_checkbox.stateChanged.connect(self.on_smooth_toggle)
        route_smooth_layout.addWidget(self.smooth_checkbox)
        
        self.smooth_spacing_widget = QWidget()
        smooth_layout = QHBoxLayout(self.smooth_spacing_widget)
        smooth_layout.setContentsMargins(0, 0, 0, 0)
        smooth_label = QLabel("Spacing:")
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(5, 50)
        self.spacing_spin.setValue(10)
        self.spacing_spin.setSuffix(" m")
        self.spacing_spin.valueChanged.connect(self.update_mission)
        smooth_layout.addWidget(smooth_label)
        smooth_layout.addWidget(self.spacing_spin)
        route_smooth_layout.addWidget(self.smooth_spacing_widget)
        self.smooth_spacing_widget.setEnabled(False)
        
        layout.addWidget(self.route_smooth_group)
        
        return group
    
    def create_connection_section(self):
        """Create drone connection section"""
        group = QGroupBox("3. Drone Connection")
        layout = QVBoxLayout(group)
        
        # Scan ports button row
        scan_layout = QHBoxLayout()
        self.scan_btn = QPushButton("🔍 Scan Ports")
        self.scan_btn.clicked.connect(self.scan_ports)
        scan_layout.addWidget(self.scan_btn)
        
        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.clicked.connect(self.scan_ports)
        self.refresh_btn.setMaximumWidth(80)
        scan_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(scan_layout)
        
        # Port selector
        port_layout = QHBoxLayout()
        port_label = QLabel("COM Port:")
        self.port_combo = QComboBox()
        self.port_combo.addItem("Select port...")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo, 1)
        layout.addLayout(port_layout)
        
        # Connect button
        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.clicked.connect(self.connect_drone)
        layout.addWidget(self.connect_btn)
        
        # Status indicator
        self.connection_status = QLabel("● Not Connected")
        self.connection_status.setStyleSheet("color: #ff4444; font-weight: bold;")
        layout.addWidget(self.connection_status)
        
        # Connect signal
        self.mavlink_manager.connection_status_changed.connect(self.update_connection_status)
        
        return group
    
    def create_telemetry_section(self):
        """Create telemetry display section"""
        group = QGroupBox("📡 Live Telemetry Data")
        layout = QVBoxLayout(group)
        
        # Create a grid layout for telemetry data
        grid = QGridLayout()
        grid.setSpacing(5)
        
        # Row 0: GPS Latitude
        gps_lat_label = QLabel("Latitude:")
        gps_lat_label.setStyleSheet("color: #888; font-size: 11px;")
        self.gps_lat_value = QLabel("0.000000°")
        self.gps_lat_value.setStyleSheet("color: #4a90e2; font-weight: bold; font-size: 11px;")
        grid.addWidget(gps_lat_label, 0, 0)
        grid.addWidget(self.gps_lat_value, 0, 1)
        
        # Row 1: GPS Longitude
        gps_lon_label = QLabel("Longitude:")
        gps_lon_label.setStyleSheet("color: #888; font-size: 11px;")
        self.gps_lon_value = QLabel("0.000000°")
        self.gps_lon_value.setStyleSheet("color: #4a90e2; font-weight: bold; font-size: 11px;")
        grid.addWidget(gps_lon_label, 1, 0)
        grid.addWidget(self.gps_lon_value, 1, 1)
        
        # Row 2: Altitude
        alt_label = QLabel("Altitude:")
        alt_label.setStyleSheet("color: #888; font-size: 11px;")
        self.alt_value = QLabel("0.0 m")
        self.alt_value.setStyleSheet("color: #4a90e2; font-weight: bold; font-size: 11px;")
        grid.addWidget(alt_label, 2, 0)
        grid.addWidget(self.alt_value, 2, 1)
        
        # Row 3: Battery
        battery_label = QLabel("Battery:")
        battery_label.setStyleSheet("color: #888; font-size: 11px;")
        self.battery_value = QLabel("0%")
        self.battery_value.setStyleSheet("color: #44ff44; font-weight: bold; font-size: 11px;")
        grid.addWidget(battery_label, 3, 0)
        grid.addWidget(self.battery_value, 3, 1)
        
        # Row 4: Flight Mode
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("color: #888; font-size: 11px;")
        self.mode_value = QLabel("Unknown")
        self.mode_value.setStyleSheet("color: #ff9900; font-weight: bold; font-size: 11px;")
        grid.addWidget(mode_label, 4, 0)
        grid.addWidget(self.mode_value, 4, 1)
        
        # Row 5: Armed Status
        armed_label = QLabel("Armed:")
        armed_label.setStyleSheet("color: #888; font-size: 11px;")
        self.armed_value = QLabel("Disarmed")
        self.armed_value.setStyleSheet("color: #888; font-weight: bold; font-size: 11px;")
        grid.addWidget(armed_label, 5, 0)
        grid.addWidget(self.armed_value, 5, 1)
        
        # Row 6: Pitch
        pitch_label = QLabel("Pitch:")
        pitch_label.setStyleSheet("color: #888; font-size: 11px;")
        self.pitch_value = QLabel("0.0°")
        self.pitch_value.setStyleSheet("color: #aaa; font-size: 11px;")
        grid.addWidget(pitch_label, 6, 0)
        grid.addWidget(self.pitch_value, 6, 1)
        
        # Row 7: Roll
        roll_label = QLabel("Roll:")
        roll_label.setStyleSheet("color: #888; font-size: 11px;")
        self.roll_value = QLabel("0.0°")
        self.roll_value.setStyleSheet("color: #aaa; font-size: 11px;")
        grid.addWidget(roll_label, 7, 0)
        grid.addWidget(self.roll_value, 7, 1)
        
        # Row 8: Yaw/Heading
        yaw_label = QLabel("Heading:")
        yaw_label.setStyleSheet("color: #888; font-size: 11px;")
        self.yaw_value = QLabel("0.0°")
        self.yaw_value.setStyleSheet("color: #aaa; font-size: 11px;")
        grid.addWidget(yaw_label, 8, 0)
        grid.addWidget(self.yaw_value, 8, 1)
        
        layout.addLayout(grid)
        
        # Status message
        self.telemetry_status = QLabel("⚫ No telemetry data")
        self.telemetry_status.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        layout.addWidget(self.telemetry_status)
        
        # Connect to telemetry updates
        self.mavlink_manager.telemetry_updated.connect(self.update_telemetry_display)
        
        return group
    
    def create_upload_section(self):
        """Create mission upload section"""
        group = QGroupBox("4. Upload Mission")
        layout = QVBoxLayout(group)
        
        # Upload button
        self.upload_mission_btn = QPushButton("🚀 Upload Mission to Drone")
        self.upload_mission_btn.setEnabled(False)
        self.upload_mission_btn.clicked.connect(self.upload_mission)
        self.upload_mission_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.upload_mission_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return group
    
    def create_right_panel(self):
        """Create right map preview panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)  # Remove spacing
        
        title = QLabel("Mission Preview Map")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4a90e2; padding: 5px;")
        title.setMaximumHeight(30)  # Limit title height
        layout.addWidget(title)
        
        # Web view for map
        self.map_view = QWebEngineView()
        layout.addWidget(self.map_view, 1)  # Stretch factor 1 to fill space
        
        # Initialize empty map
        self.show_empty_map()
        
        return panel
    
    def upload_kml(self):
        """Handle KML file upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select KML File",
            "",
            "KML Files (*.kml);;All Files (*)"
        )
        
        if file_path:
            try:
                self.kml_file_path = file_path
                self.kml_label.setText(os.path.basename(file_path))
                self.kml_label.setStyleSheet("color: #4a90e2;")
                
                self.log_debug(f"Parsing KML file: {file_path}")
                
                # Parse KML
                self.raw_coordinates, self.is_polygon = KMLParser.parse_kml(file_path)
                
                self.log_debug(f"Parsed {len(self.raw_coordinates)} coordinates, is_polygon={self.is_polygon}")
                
                # Auto-select mode based on KML type
                if self.is_polygon:
                    self.area_scan_radio.setChecked(True)
                    self.log_status(f"✓ Loaded polygon boundary ({len(self.raw_coordinates)} points) - Area Scan mode")
                else:
                    self.route_mode_radio.setChecked(True)
                    self.log_status(f"✓ Loaded route ({len(self.raw_coordinates)} points) - Route mode")
                
                # Update mission
                self.update_mission()
                
            except Exception as e:
                self.log_status(f"✗ Error loading KML: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load KML: {str(e)}")
    
    def on_smooth_toggle(self, state):
        """Handle smooth waypoint checkbox toggle"""
        self.smooth_spacing_widget.setEnabled(state == Qt.Checked)
        self.update_mission()
    
    def update_mission(self):
        """Update mission waypoints based on settings"""
        if not self.raw_coordinates:
            return
        
        # Update UI based on mode
        is_area_scan = self.area_scan_radio.isChecked()
        self.area_scan_group.setEnabled(is_area_scan)
        self.route_smooth_group.setEnabled(not is_area_scan)
        
        altitude = self.altitude_spin.value()
        
        if is_area_scan:
            # Generate coverage path for area scan
            sweep_spacing = self.sweep_spacing_spin.value()
            sweep_angle = self.sweep_angle_spin.value()
            waypoint_spacing = self.waypoint_spacing_spin.value()
            
            self.log_debug(f"Generating coverage: sweep={sweep_spacing}m, wp_spacing={waypoint_spacing}m, angle={sweep_angle}°")
            
            # Set altitude for boundary coordinates
            boundary_with_alt = [(lat, lon, altitude) for lat, lon, _ in self.raw_coordinates]
            
            self.waypoints = KMLParser.generate_coverage_path(
                boundary_with_alt,
                sweep_spacing,
                sweep_angle,
                waypoint_spacing
            )
            
            if not self.waypoints:
                self.log_status("⚠ Failed to generate coverage path")
                self.log_debug("Coverage path generation returned empty")
                return
            
            self.log_debug(f"Generated {len(self.waypoints)} waypoints for coverage")
        else:
            # Route mode - convert to waypoints with fixed altitude
            self.waypoints = WaypointConverter.convert_to_waypoints(
                self.raw_coordinates,
                altitude
            )
            
            # Apply smoothing if enabled
            if self.smooth_checkbox.isChecked():
                spacing = self.spacing_spin.value()
                self.waypoints = KMLParser.smooth_waypoints(self.waypoints, spacing)
        
        # Update info
        stats = WaypointConverter.get_route_stats(self.waypoints)
        self.waypoint_info.setText(
            f"Waypoints: {stats['waypoint_count']} | "
            f"Distance: {stats['total_distance']:.1f} m"
        )
        
        # Update map
        self.update_map()
        
        # Enable upload if connected
        if self.mavlink_manager.connected:
            self.upload_mission_btn.setEnabled(True)
    
    def show_empty_map(self):
        """Show empty default map"""
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        # Save and load
        html_path = os.path.join(os.path.dirname(__file__), 'temp_map.html')
        m.save(html_path)
        self.map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def update_map(self):
        """Update map with waypoints"""
        if not self.waypoints:
            return
        
        stats = WaypointConverter.get_route_stats(self.waypoints)
        
        # Calculate bounds for auto-zoom
        lats = [wp[0] for wp in self.waypoints]
        lons = [wp[1] for wp in self.waypoints]
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        
        # Create map centered on route with auto-zoom
        m = folium.Map(
            location=[stats['center_lat'], stats['center_lon']],
            zoom_start=15
        )
        
        # Fit map to show all waypoints with padding
        m.fit_bounds(bounds, padding=[30, 30])
        
        is_area_scan = self.area_scan_radio.isChecked()
        
        if is_area_scan and self.raw_coordinates:
            # Draw polygon boundary
            boundary_coords = [(lat, lon) for lat, lon, _ in self.raw_coordinates]
            folium.Polygon(
                boundary_coords,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.1,
                weight=2,
                popup='Scan Area Boundary'
            ).add_to(m)
            
            # Draw coverage path line
            route_coords = [(lat, lon) for lat, lon, _ in self.waypoints]
            folium.PolyLine(
                route_coords,
                color='orange',
                weight=1,
                opacity=0.5,
                popup='Coverage Path'
            ).add_to(m)
            
            # Add ALL waypoints as markers (like the image)
            for i, (lat, lon, alt) in enumerate(self.waypoints):
                folium.CircleMarker(
                    [lat, lon],
                    radius=4,
                    popup=f"WP{i+1}<br>Alt: {alt}m",
                    tooltip=f"WP{i+1}",
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.8,
                    weight=1
                ).add_to(m)
        else:
            # Route mode - show all waypoints
            for i, (lat, lon, alt) in enumerate(self.waypoints):
                folium.Marker(
                    [lat, lon],
                    popup=f"WP{i+1}<br>Alt: {alt}m",
                    tooltip=f"Waypoint {i+1}",
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(m)
            
            # Add route line
            route_coords = [(lat, lon) for lat, lon, _ in self.waypoints]
            folium.PolyLine(
                route_coords,
                color='red',
                weight=3,
                opacity=0.8
            ).add_to(m)
        
        # Add RTL return path (last waypoint to home) in cyan
        if self.waypoints and len(self.waypoints) > 1 and self.rtl_checkbox.isChecked():
            rtl_path = [
                [self.waypoints[-1][0], self.waypoints[-1][1]],  # Last waypoint
                [self.waypoints[0][0], self.waypoints[0][1]]     # Home
            ]
            folium.PolyLine(
                rtl_path,
                color='cyan',
                weight=3,
                opacity=0.7,
                dash_array='10, 5',
                popup='Return to Launch Path'
            ).add_to(m)
        
        # Add home marker (first point)
        if self.waypoints:
            folium.Marker(
                [self.waypoints[0][0], self.waypoints[0][1]],
                popup="Home/Start",
                icon=folium.Icon(color='green', icon='home')
            ).add_to(m)
        
        # Save and load
        html_path = os.path.join(os.path.dirname(__file__), 'temp_map.html')
        m.save(html_path)
        self.map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def scan_ports(self):
        """Scan for available COM ports"""
        self.log_debug("Starting COM port scan...")
        
        try:
            import serial.tools.list_ports
            ports_info = list(serial.tools.list_ports.comports())
            
            self.log_debug(f"Found {len(ports_info)} serial devices")
            
            ports = []
            for port_info in ports_info:
                port_name = port_info.device
                port_desc = port_info.description
                port_hwid = port_info.hwid if hasattr(port_info, 'hwid') else 'N/A'
                
                ports.append(port_name)
                self.log_debug(f"  {port_name}: {port_desc} [{port_hwid}]")
            
            self.port_combo.clear()
            
            if ports:
                self.port_combo.addItems(ports)
                self.log_status(f"✓ Found {len(ports)} port(s): {', '.join(ports)}")
            else:
                self.port_combo.addItem("No ports found")
                self.log_status("✗ No COM ports detected")
                self.log_debug("No serial devices found. Check:")
                self.log_debug("  1. Device is connected via USB")
                self.log_debug("  2. Drivers are installed")
                self.log_debug("  3. Device is powered on")
                self.log_debug("  4. Check Windows Device Manager")
                
        except Exception as e:
            self.log_status(f"✗ Error scanning ports: {str(e)}")
            self.log_debug(f"Exception during port scan: {e}")
    
    def connect_drone(self):
        """Connect to drone"""
        port = self.port_combo.currentText()
        
        if not port or port in ["Select port...", "No ports found"]:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Please select a valid COM port")
            return
        
        self.log_status(f"Connecting to {port}...")
        self.log_debug(f"Attempting MAVLink connection on {port} at 57600 baud")
        self.connect_btn.setEnabled(False)
        
        try:
            success, message = self.mavlink_manager.connect(port)
            
            self.connect_btn.setEnabled(True)
            
            if success:
                self.log_status(f"✓ {message}")
                self.log_debug(f"MAVLink heartbeat received on {port}")
            else:
                self.log_status(f"✗ Connection Failed")
                self.log_debug("=" * 50)
                self.log_debug(f"ERROR: {message}")
                self.log_debug("=" * 50)
                
                # Show detailed error dialog
                from PyQt5.QtWidgets import QMessageBox
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Critical)
                error_dialog.setWindowTitle("Connection Error")
                error_dialog.setText(f"Failed to connect to {port}")
                error_dialog.setDetailedText(message)
                error_dialog.setStandardButtons(QMessageBox.Ok)
                error_dialog.exec_()
                
        except Exception as e:
            self.connect_btn.setEnabled(True)
            self.log_status(f"✗ Exception: {str(e)}")
            self.log_debug(f"Connection exception: {e}")
    
    def update_connection_status(self, connected):
        """Update connection status indicator"""
        if connected:
            self.connection_status.setText("● Connected")
            self.connection_status.setStyleSheet("color: #44ff44; font-weight: bold;")
            self.connect_btn.setText("🔌 Disconnect")
            self.telemetry_status.setText("⚫ Receiving telemetry data...")
            self.telemetry_status.setStyleSheet("color: #44ff44; font-size: 10px; font-style: italic;")
            
            if self.waypoints:
                self.upload_mission_btn.setEnabled(True)
        else:
            self.connection_status.setText("● Not Connected")
            self.connection_status.setStyleSheet("color: #ff4444; font-weight: bold;")
            self.connect_btn.setText("🔌 Connect")
            self.upload_mission_btn.setEnabled(False)
            self.telemetry_status.setText("⚫ No telemetry data")
            self.telemetry_status.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
    
    def update_telemetry_display(self, telemetry):
        """Update telemetry display with live data"""
        try:
            # GPS Coordinates
            self.gps_lat_value.setText(f"{telemetry.get('lat', 0.0):.6f}°")
            self.gps_lon_value.setText(f"{telemetry.get('lon', 0.0):.6f}°")
            
            # Altitude
            alt = telemetry.get('alt', 0.0)
            self.alt_value.setText(f"{alt:.1f} m")
            
            # Battery
            battery = telemetry.get('battery', 0)
            self.battery_value.setText(f"{battery}%")
            
            # Color-code battery level
            if battery > 50:
                self.battery_value.setStyleSheet("color: #44ff44; font-weight: bold; font-size: 11px;")
            elif battery > 25:
                self.battery_value.setStyleSheet("color: #ff9900; font-weight: bold; font-size: 11px;")
            else:
                self.battery_value.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 11px;")
            
            # Flight Mode
            mode = telemetry.get('mode', 'Unknown')
            self.mode_value.setText(str(mode))
            
            # Armed Status
            armed = telemetry.get('armed', False)
            if armed:
                self.armed_value.setText("⚠ ARMED")
                self.armed_value.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 11px;")
            else:
                self.armed_value.setText("Disarmed")
                self.armed_value.setStyleSheet("color: #888; font-weight: bold; font-size: 11px;")
            
            # Attitude
            pitch = telemetry.get('pitch', 0.0)
            roll = telemetry.get('roll', 0.0)
            yaw = telemetry.get('yaw', 0.0)
            
            self.pitch_value.setText(f"{pitch:.1f}°")
            self.roll_value.setText(f"{roll:.1f}°")
            self.yaw_value.setText(f"{yaw:.1f}°")
            
            # Update status to show data is flowing
            self.telemetry_status.setText(f"⚫ Live • Alt: {alt:.0f}m • Bat: {battery}%")
            
        except Exception as e:
            self.log_debug(f"Error updating telemetry display: {e}")
    
    def upload_mission(self):
        """Upload mission to drone"""
        if not self.waypoints:
            QMessageBox.warning(self, "Warning", "No waypoints to upload")
            return
        
        if not self.mavlink_manager.connected:
            QMessageBox.warning(self, "Warning", "Not connected to drone")
            return
        
        # Confirm upload
        mode_text = "Area Scan" if self.area_scan_radio.isChecked() else "Route"
        reply = QMessageBox.question(
            self,
            "Confirm Upload",
            f"Upload {len(self.waypoints)} waypoints to drone?\n\n"
            f"Mode: {mode_text}\n"
            f"Takeoff: {'Yes' if self.takeoff_checkbox.isChecked() else 'No'}\n"
            f"RTL: {'Yes' if self.rtl_checkbox.isChecked() else 'No'}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Start upload in background thread
        self.upload_mission_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        self.upload_thread = MissionUploadThread(
            self.mission_uploader,
            self.waypoints,
            self.takeoff_checkbox.isChecked(),
            self.rtl_checkbox.isChecked()
        )
        
        self.upload_thread.finished.connect(self.on_upload_complete)
        self.mavlink_manager.mission_upload_progress.connect(self.on_upload_progress)
        
        self.upload_thread.start()
        self.log_status("🚀 Starting mission upload...")
    
    def on_upload_progress(self, message):
        """Handle upload progress message"""
        self.log_status(message)
    
    def on_upload_complete(self, success, message):
        """Handle upload completion"""
        self.upload_mission_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log_status(f"✓ {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self.log_status(f"✗ {message}")
            QMessageBox.critical(self, "Upload Failed", message)
    
    def log_status(self, message):
        """Add message to status log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_log.append(f"[{timestamp}] {message}")
    
    def log_debug(self, message):
        """Add message to debug log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.debug_log.append(f"[{timestamp}] {message}")
        # Also print to console
        print(f"[DEBUG] {message}")
    
    def apply_stylesheet(self):
        """Apply stylesheet to tab"""
        self.setStyleSheet("""
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QGroupBox {
            border: 2px solid #3d3d3d;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            color: #4a90e2;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        
        QPushButton {
            background-color: #3d3d3d;
            color: #ffffff;
            border: none;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
        
        QComboBox, QSpinBox {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
        }
        
        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 3px;
        }
        
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        
        QProgressBar {
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            text-align: center;
            background-color: #1e1e1e;
        }
        
        QProgressBar::chunk {
            background-color: #4a90e2;
        }
        """)
