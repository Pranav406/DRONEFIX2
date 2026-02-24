"""
Telemetry Tab - Real-time drone telemetry display
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QGridLayout, QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont


class TelemetryTab(QWidget):
    """Tab for displaying real-time drone telemetry"""
    
    def __init__(self, mavlink_manager):
        super().__init__()
        self.mavlink_manager = mavlink_manager
        self.init_ui()
        self.apply_stylesheet()
        
        # Connect to telemetry updates
        self.mavlink_manager.telemetry_updated.connect(self.update_telemetry)
        self.mavlink_manager.connection_status_changed.connect(self.update_connection_status)
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Live Telemetry Data")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #4a90e2; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(title)
        
        # Connection status
        self.connection_label = QLabel("● NOT CONNECTED")
        self.connection_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ff4444; padding: 5px;")
        self.connection_label.setAlignment(Qt.AlignCenter)
        self.connection_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(self.connection_label)
        
        # Create telemetry display sections
        telemetry_layout = QHBoxLayout()
        
        # Left column - GPS and Position
        left_column = QVBoxLayout()
        left_column.addWidget(self.create_gps_section())
        left_column.addWidget(self.create_attitude_section())
        left_column.addStretch()
        
        # Right column - System Status
        right_column = QVBoxLayout()
        right_column.addWidget(self.create_system_section())
        right_column.addWidget(self.create_flight_section())
        right_column.addStretch()
        
        telemetry_layout.addLayout(left_column, 1)
        telemetry_layout.addLayout(right_column, 1)
        
        layout.addLayout(telemetry_layout, 1)
        
        # Instructions
        instructions = QLabel(
            "Connect to your drone via the Mission Planner tab to view live telemetry data"
        )
        instructions.setStyleSheet("color: #888; font-size: 10pt; padding: 10px;")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(instructions)
        
    def create_gps_section(self):
        """Create GPS and position display section"""
        group = QGroupBox("📍 GPS & Position")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        # Create labels
        labels = [
            ("Latitude:", "lat"),
            ("Longitude:", "lon"),
            ("Altitude (Rel):", "alt"),
        ]
        
        self.gps_labels = {}
        for row, (label_text, key) in enumerate(labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 11pt;")
            value = QLabel("--")
            value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
            value.setAlignment(Qt.AlignRight)
            
            layout.addWidget(label, row, 0)
            layout.addWidget(value, row, 1)
            self.gps_labels[key] = value
        
        return group
    
    def create_attitude_section(self):
        """Create attitude display section"""
        group = QGroupBox("🎯 Attitude")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        labels = [
            ("Pitch:", "pitch"),
            ("Roll:", "roll"),
            ("Yaw:", "yaw"),
        ]
        
        self.attitude_labels = {}
        for row, (label_text, key) in enumerate(labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 11pt;")
            value = QLabel("--")
            value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
            value.setAlignment(Qt.AlignRight)
            
            layout.addWidget(label, row, 0)
            layout.addWidget(value, row, 1)
            self.attitude_labels[key] = value
        
        return group
    
    def create_system_section(self):
        """Create system status display section"""
        group = QGroupBox("🔋 System Status")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        # Battery
        battery_label = QLabel("Battery:")
        battery_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.battery_value = QLabel("--")
        self.battery_value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
        self.battery_value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(battery_label, 0, 0)
        layout.addWidget(self.battery_value, 0, 1)
        
        # Voltage
        voltage_label = QLabel("Voltage:")
        voltage_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.voltage_value = QLabel("--")
        self.voltage_value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
        self.voltage_value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(voltage_label, 1, 0)
        layout.addWidget(self.voltage_value, 1, 1)
        
        # Current
        current_label = QLabel("Current:")
        current_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.current_value = QLabel("--")
        self.current_value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
        self.current_value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(current_label, 2, 0)
        layout.addWidget(self.current_value, 2, 1)
        
        return group
    
    def create_flight_section(self):
        """Create flight mode display section"""
        group = QGroupBox("✈️ Flight Status")
        layout = QGridLayout(group)
        layout.setSpacing(10)
        
        # Flight Mode
        mode_label = QLabel("Flight Mode:")
        mode_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.mode_value = QLabel("--")
        self.mode_value.setStyleSheet("font-size: 12pt; color: #4a90e2;")
        self.mode_value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(mode_label, 0, 0)
        layout.addWidget(self.mode_value, 0, 1)
        
        # Armed Status
        armed_label = QLabel("Armed:")
        armed_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.armed_value = QLabel("--")
        self.armed_value.setStyleSheet("font-size: 12pt; color: #888;")
        self.armed_value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(armed_label, 1, 0)
        layout.addWidget(self.armed_value, 1, 1)
        
        return group
    
    @pyqtSlot(dict)
    def update_telemetry(self, telemetry):
        """Update telemetry display with new data"""
        # GPS & Position
        self.gps_labels['lat'].setText(f"{telemetry['lat']:.7f}°")
        self.gps_labels['lon'].setText(f"{telemetry['lon']:.7f}°")
        self.gps_labels['alt'].setText(f"{telemetry['alt']:.2f} m")
        
        # Attitude
        self.attitude_labels['pitch'].setText(f"{telemetry['pitch']:.2f}°")
        self.attitude_labels['roll'].setText(f"{telemetry['roll']:.2f}°")
        self.attitude_labels['yaw'].setText(f"{telemetry['yaw']:.2f}°")
        
        # Battery
        battery_pct = telemetry['battery']
        self.battery_value.setText(f"{battery_pct}%")
        
        # Color code battery
        if battery_pct > 50:
            self.battery_value.setStyleSheet("font-size: 12pt; color: #44ff44;")
        elif battery_pct > 20:
            self.battery_value.setStyleSheet("font-size: 12pt; color: #ffaa00;")
        else:
            self.battery_value.setStyleSheet("font-size: 12pt; color: #ff4444;")
        
        # Voltage
        voltage = telemetry.get('voltage', 0.0)
        self.voltage_value.setText(f"{voltage:.2f} V")
        
        # Current
        current = telemetry.get('current', 0.0)
        self.current_value.setText(f"{current:.1f} A")
        
        # Flight Mode
        self.mode_value.setText(telemetry['mode'])
        
        # Armed Status
        if telemetry['armed']:
            self.armed_value.setText("ARMED")
            self.armed_value.setStyleSheet("font-size: 12pt; color: #ff4444; font-weight: bold;")
        else:
            self.armed_value.setText("DISARMED")
            self.armed_value.setStyleSheet("font-size: 12pt; color: #44ff44;")
    
    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        """Update connection status display"""
        if connected:
            self.connection_label.setText("● CONNECTED")
            self.connection_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #44ff44; padding: 5px;")
        else:
            self.connection_label.setText("● NOT CONNECTED")
            self.connection_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ff4444; padding: 5px;")
            
            # Reset all values to "--"
            for label in self.gps_labels.values():
                label.setText("--")
            for label in self.attitude_labels.values():
                label.setText("--")
            self.battery_value.setText("--")
            self.voltage_value.setText("--")
            self.current_value.setText("--")
            self.mode_value.setText("--")
            self.armed_value.setText("--")
    
    def apply_stylesheet(self):
        """Apply stylesheet to tab"""
        self.setStyleSheet("""
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QGroupBox {
            border: 2px solid #3d3d3d;
            border-radius: 8px;
            margin-top: 15px;
            padding: 15px;
            font-weight: bold;
            font-size: 12pt;
            color: #4a90e2;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px;
        }
        """)
