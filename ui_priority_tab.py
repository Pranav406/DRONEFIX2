"""
Priority Tab - Display and manage priority list based on detected human conditions
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLineEdit, QLabel, QMessageBox, QListWidgetItem, QGroupBox,
    QScrollArea, QFrame, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPixmap


class PriorityItem:
    """Data class for priority items"""
    
    def __init__(self, condition, description, posture_type, priority_score,
                 tracker_id, gps_coords=None, image_path=None, timestamp=None):
        self.condition = condition
        self.description = description
        self.posture_type = posture_type
        self.priority_score = priority_score
        self.tracker_id = tracker_id
        self.gps_coords = gps_coords
        self.image_path = image_path
        self.timestamp = timestamp or datetime.now()
        
    def to_display_string(self):
        """Convert to display string for list widget"""
        gps_str = ""
        if self.gps_coords:
            lat, lon = self.gps_coords
            gps_str = f" @ {lat:.5f}, {lon:.5f}"
        
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        return (f"[{self.priority_score}] {self.condition} - "
                f"Person #{self.tracker_id} {self.posture_type}{gps_str} ({time_str})")


class PriorityTab(QWidget):
    """Priority list UI with automatic posture-based priority generation"""
    
    # Signal to request posture analysis
    request_analysis = pyqtSignal(int)  # tracker_id
    
    def __init__(self, mavlink_manager=None):
        super().__init__()
        self.mavlink_manager = mavlink_manager
        self.priority_items = []  # List of PriorityItem objects
        self.auto_add_enabled = True
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("🚨 Priority List - Human Condition Assessment")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        main_layout.addWidget(header)
        
        # Info label
        info = QLabel(
            "Automatically generated priorities based on human posture analysis using MediaPipe.\n"
            "Higher scores indicate more urgent conditions requiring immediate attention."
        )
        info.setStyleSheet("color: #aaaaaa; font-size: 11px; margin-bottom: 5px;")
        info.setWordWrap(True)
        main_layout.addWidget(info)
        
        # Auto-add checkbox
        self.auto_checkbox = QCheckBox("Auto-add detected persons")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self.toggle_auto_add)
        self.auto_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        main_layout.addWidget(self.auto_checkbox)
        
        # Priority list widget
        list_group = QGroupBox("Priority Queue (sorted by urgency)")
        list_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        list_layout = QVBoxLayout(list_group)
        
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
        """)
        self.list_widget.itemClicked.connect(self.show_item_details)
        list_layout.addWidget(self.list_widget)
        
        main_layout.addWidget(list_group, 1)
        
        # Details panel
        self.details_panel = QTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setMaximumHeight(150)
        self.details_panel.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                font-size: 11px;
            }
        """)
        self.details_panel.setPlaceholderText("Select an item to view details...")
        main_layout.addWidget(self.details_panel)
        
        # Manual input section
        manual_group = QGroupBox("Manual Entry")
        manual_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        manual_layout = QHBoxLayout(manual_group)
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Add custom priority item...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
            }
        """)
        self.input_edit.returnPressed.connect(self.add_manual_item)
        manual_layout.addWidget(self.input_edit)
        
        add_btn = QPushButton("➕ Add")
        add_btn.clicked.connect(self.add_manual_item)
        add_btn.setStyleSheet(self._button_style("#4a90e2"))
        manual_layout.addWidget(add_btn)
        
        main_layout.addWidget(manual_group)
        
        # Control buttons
        controls = QHBoxLayout()
        controls.setSpacing(10)
        
        remove_btn = QPushButton("🗑️ Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        remove_btn.setStyleSheet(self._button_style("#e67e22"))
        controls.addWidget(remove_btn)
        
        clear_btn = QPushButton("🧹 Clear All")
        clear_btn.clicked.connect(self.clear_all)
        clear_btn.setStyleSheet(self._button_style("#e74c3c"))
        controls.addWidget(clear_btn)
        
        export_btn = QPushButton("📄 Export List")
        export_btn.clicked.connect(self.export_list)
        export_btn.setStyleSheet(self._button_style("#27ae60"))
        controls.addWidget(export_btn)
        
        main_layout.addLayout(controls)
        
        # Stats label
        self.stats_label = QLabel("Items: 0 | Critical: 0 | Warning: 0 | Normal: 0")
        self.stats_label.setStyleSheet("color: #888888; font-size: 10px;")
        main_layout.addWidget(self.stats_label)
        
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
    
    def toggle_auto_add(self, state):
        """Toggle automatic priority addition"""
        self.auto_add_enabled = (state == Qt.Checked)
        
    def add_priority_item(self, priority_item: PriorityItem):
        """
        Add a priority item from posture analysis
        
        Args:
            priority_item: PriorityItem object
        """
        if not self.auto_add_enabled:
            return
        
        # Check if this tracker already exists
        for existing in self.priority_items:
            if existing.tracker_id == priority_item.tracker_id:
                # Update existing item if priority changed significantly
                if abs(existing.priority_score - priority_item.priority_score) > 10:
                    existing.priority_score = priority_item.priority_score
                    existing.condition = priority_item.condition
                    existing.description = priority_item.description
                    existing.posture_type = priority_item.posture_type
                    existing.timestamp = priority_item.timestamp
                    self._refresh_list()
                return
        
        # Add new item
        self.priority_items.append(priority_item)
        self._refresh_list()
        
        # Notify if critical
        if priority_item.condition == "Critical":
            self._show_critical_alert(priority_item)
    
    def add_manual_item(self):
        """Add manual priority item"""
        text = self.input_edit.text().strip()
        if not text:
            return
        
        # Create manual item with medium priority
        manual_item = PriorityItem(
            condition="Manual",
            description=text,
            posture_type="N/A",
            priority_score=50,
            tracker_id=-1,
            timestamp=datetime.now()
        )
        
        self.priority_items.append(manual_item)
        self.input_edit.clear()
        self._refresh_list()
    
    def remove_selected(self):
        """Remove selected item"""
        row = self.list_widget.currentRow()
        if row >= 0 and row < len(self.priority_items):
            del self.priority_items[row]
            self._refresh_list()
        else:
            QMessageBox.information(self, "Remove", "Select an item to remove.")
    
    def clear_all(self):
        """Clear all priority items"""
        if QMessageBox.question(
            self, "Clear All",
            "Clear all priority items?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.priority_items.clear()
            self._refresh_list()
            self.details_panel.clear()
    
    def _refresh_list(self):
        """Refresh the list widget display"""
        # Sort by priority score (descending)
        self.priority_items.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Clear and repopulate
        self.list_widget.clear()
        
        for item in self.priority_items:
            list_item = QListWidgetItem(item.to_display_string())
            
            # Color code by condition
            if item.condition == "Critical":
                list_item.setForeground(QColor(255, 100, 100))
                list_item.setFont(QFont("Consolas", 11, QFont.Bold))
            elif item.condition == "Warning":
                list_item.setForeground(QColor(255, 180, 0))
            elif item.condition == "Manual":
                list_item.setForeground(QColor(100, 200, 255))
            else:
                list_item.setForeground(QColor(100, 255, 100))
            
            self.list_widget.addItem(list_item)
        
        # Update stats
        self._update_stats()
    
    def _update_stats(self):
        """Update statistics label"""
        total = len(self.priority_items)
        critical = sum(1 for x in self.priority_items if x.condition == "Critical")
        warning = sum(1 for x in self.priority_items if x.condition == "Warning")
        normal = sum(1 for x in self.priority_items if x.condition == "Normal")
        
        self.stats_label.setText(
            f"Items: {total} | Critical: {critical} | Warning: {warning} | Normal: {normal}"
        )
    
    def show_item_details(self, list_item):
        """Show detailed information for selected item"""
        row = self.list_widget.row(list_item)
        if row < 0 or row >= len(self.priority_items):
            return
        
        item = self.priority_items[row]
        
        details = f"""
<b>Priority Details</b><br>
<hr>
<b>Condition:</b> {item.condition}<br>
<b>Priority Score:</b> {item.priority_score}/100<br>
<b>Person ID:</b> #{item.tracker_id if item.tracker_id >= 0 else 'Manual'}<br>
<b>Posture:</b> {item.posture_type}<br>
<b>Description:</b> {item.description}<br>
<b>Timestamp:</b> {item.timestamp.strftime('%Y-%m-%d %H:%M:%S')}<br>
"""
        
        if item.gps_coords:
            lat, lon = item.gps_coords
            details += f"<b>GPS Location:</b> {lat:.6f}, {lon:.6f}<br>"
        
        if item.image_path and os.path.exists(item.image_path):
            details += f"<b>Image:</b> {item.image_path}<br>"
        
        self.details_panel.setHtml(details)
    
    def _show_critical_alert(self, item):
        """Show alert for critical condition"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("⚠️ Critical Priority Detected")
        msg.setText(f"Person #{item.tracker_id}: {item.description}")
        
        gps_text = ""
        if item.gps_coords:
            lat, lon = item.gps_coords
            gps_text = f"\n\nGPS: {lat:.6f}, {lon:.6f}"
        
        msg.setInformativeText(
            f"Posture: {item.posture_type}\n"
            f"Priority Score: {item.priority_score}/100"
            f"{gps_text}"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()
    
    def export_list(self):
        """Export priority list to text file"""
        from PyQt5.QtWidgets import QFileDialog
        
        if not self.priority_items:
            QMessageBox.information(self, "Export", "No items to export.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Priority List",
            f"priority_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("=== PRIORITY LIST ===\n")
                    f.write(f"Generated: {datetime.now()}\n\n")
                    
                    for i, item in enumerate(self.priority_items, 1):
                        f.write(f"{i}. {item.to_display_string()}\n")
                        f.write(f"   Description: {item.description}\n")
                        if item.gps_coords:
                            f.write(f"   GPS: {item.gps_coords[0]:.6f}, {item.gps_coords[1]:.6f}\n")
                        f.write("\n")
                
                QMessageBox.information(self, "Export", f"List exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
