"""
Main Window UI - Container for all tabs and application state
"""

from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QStatusBar, QAction, QMenuBar, QLabel, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from ui_mission_planner_tab import MissionPlannerTab
from ui_telemetry_tab import TelemetryTab
from ui_priority_tab import PriorityTab
from ui_second_drone_tab import SecondDroneTab

# Try to import detection tab - may fail if PyTorch/OpenCV not properly installed
try:
    from ui_live_detection_tab import LiveDetectionTab
    DETECTION_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"Warning: Detection features unavailable: {e}")
    DETECTION_AVAILABLE = False
    
from mavlink_manager import MavlinkManager


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.mavlink_manager = MavlinkManager()
        self.init_ui()
        self.apply_stylesheet()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("DroneSW")

        # ── Responsive initial size: 80% of screen, clamped to reasonable range ──
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = max(960, int(avail.width() * 0.80))
            h = max(600, int(avail.height() * 0.80))
            x = avail.x() + (avail.width() - w) // 2
            y = avail.y() + (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.setGeometry(100, 100, 1400, 900)

        self.setMinimumSize(800, 540)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        
        # Create tabs
        self.mission_planner_tab = MissionPlannerTab(self.mavlink_manager)
        self.priority_tab = PriorityTab(self.mavlink_manager)
        self.second_drone_tab = SecondDroneTab(self.mavlink_manager, self.priority_tab)
        self.telemetry_tab = TelemetryTab(self.mavlink_manager)
        
        # Add Mission tab
        self.tabs.addTab(self.mission_planner_tab, "🗺️  Mission")

        # Add Priority tab
        self.tabs.addTab(self.priority_tab, "📋  Priority")
        
        # Add Second Drone tab
        self.tabs.addTab(self.second_drone_tab, "🚁  Rescue Drone")
        
        # Add Detection tab if available
        if DETECTION_AVAILABLE:
            self.live_detection_tab = LiveDetectionTab(self.mavlink_manager, self.priority_tab)
            self.tabs.addTab(self.live_detection_tab, "📹  Detection")
        else:
            # Add placeholder tab with instructions
            placeholder_tab = QWidget()
            placeholder_layout = QVBoxLayout(placeholder_tab)
            placeholder_label = QLabel(
                "⚠️ Detection Features Unavailable\n\n"
                "PyTorch/OpenCV dependencies could not be loaded.\n\n"
                "This is usually due to missing Visual C++ Redistributables.\n\n"
                "To enable detection features:\n"
                "1. Download and install Microsoft Visual C++ Redistributable:\n"
                "   https://aka.ms/vs/17/release/vc_redist.x64.exe\n\n"
                "2. Restart the computer\n\n"
                "3. Relaunch the application\n\n"
                "Mission Planning features are still fully functional!"
            )
            placeholder_label.setAlignment(Qt.AlignCenter)
            placeholder_label.setStyleSheet("font-size: 14px; color: #ffaa00; padding: 50px;")
            placeholder_layout.addWidget(placeholder_label)
            self.tabs.addTab(placeholder_tab, "⚠️  Detection (Unavailable)")
            self.live_detection_tab = None
        
        # Add Telemetry tab
        self.tabs.addTab(self.telemetry_tab, "📊  Telemetry")
        
        layout.addWidget(self.tabs)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Not Connected")
        
        # Connect signals
        self.mavlink_manager.connection_status_changed.connect(self.update_status_bar)
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def update_status_bar(self, status):
        """Update status bar with connection status"""
        if status:
            self.status_bar.showMessage(f"✓ Connected to Drone | MAVLink Active")
        else:
            self.status_bar.showMessage("✗ Not Connected")
            
    def show_about(self):
        """Show about dialog"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "About", 
                         "Drone Human Detection & Mission Planner GCS\n\n"
                         "Version 2.0 - Dual Drone System\n"
                         "Professional Ground Control Station for ArduPilot\n\n"
                         "Features:\n"
                         "• KML-based mission planning\n"
                         "• QGroundControl-compatible waypoint upload\n"
                         "• YOLOv8 human detection with MediaPipe posture analysis\n"
                         "• Automatic priority assessment based on human condition\n"
                         "• Real-time GPS geotagging\n"
                         "• Dual drone coordination (Surveillance + Rescue)\n"
                         "• Automatic rescue waypoint generation\n"
                         "• Live telemetry dashboard for both drones\n" \
                         "• Developed by Harigovind\n")
    
    def apply_stylesheet(self):
        """Apply modern stylesheet to the application"""
        stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QWidget {
            color: #ffffff;
        }

        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            background-color: #2b2b2b;
        }

        QTabBar::tab {
            background-color: #3d3d3d;
            color: #ffffff;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }

        QTabBar::tab:selected {
            background-color: #4a90e2;
        }

        QTabBar::tab:hover {
            background-color: #505050;
        }

        QStatusBar {
            background-color: #1e1e1e;
            color: #ffffff;
            border-top: 1px solid #3d3d3d;
        }

        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 4px;
        }

        QMenuBar::item:selected {
            background-color: #4a90e2;
        }

        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #3d3d3d;
        }

        QMenu::item:selected {
            background-color: #4a90e2;
        }

        QLabel {
            color: #ffffff;
        }

        QGroupBox {
            color: #ffffff;
            border: 2px solid #3d3d3d;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            color: #4a90e2;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }

        QCheckBox {
            color: #ffffff;
        }

        QRadioButton {
            color: #ffffff;
        }

        QLineEdit {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            padding: 5px;
        }

        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #3d3d3d;
        }

        QComboBox {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView {
            background-color: #2b2b2b;
            color: #ffffff;
            selection-background-color: #4a90e2;
        }

        QSpinBox {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
        }

        QScrollArea {
            border: none;
            background-color: transparent;
        }

        QMessageBox {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QMessageBox QLabel {
            color: #ffffff;
        }
        """
        self.setStyleSheet(stylesheet)
        
    def closeEvent(self, event):
        """Clean up on window close"""
        # Disconnect first drone
        self.mavlink_manager.disconnect()
        
        # Stop detection if running
        if hasattr(self, 'live_detection_tab') and self.live_detection_tab is not None:
            self.live_detection_tab.stop_all()
        
        # Disconnect second drone if connected
        if hasattr(self.second_drone_tab, 'mavlink_manager_drone2'):
            if self.second_drone_tab.mavlink_manager_drone2:
                self.second_drone_tab.mavlink_manager_drone2.disconnect()
        
        event.accept()
