"""
Drone Human Detection & Mission Planner Ground Station
Main Entry Point

A professional Ground Control Station for ArduPilot drones with:
- Mission planning and waypoint upload
- Live YOLOv8 human detection
- Real-time telemetry and geotagging
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from ui_main_window import MainWindow


def main():
    """Initialize and run the application"""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Drone GCS - Human Detection & Mission Planner")
    app.setStyle('Fusion')  # Modern cross-platform style
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
