"""
Priority Tab - Display and manage priority list based on detected human conditions
Shows person snapshot images alongside priority information.
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QMessageBox, QGroupBox,
    QScrollArea, QFrame, QCheckBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
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
        """Convert to display string"""
        gps_str = ""
        if self.gps_coords:
            lat, lon = self.gps_coords
            gps_str = f" @ {lat:.5f}, {lon:.5f}"
        time_str = self.timestamp.strftime("%H:%M:%S")
        return (f"[{self.priority_score}] {self.condition} - "
                f"Person #{self.tracker_id} {self.posture_type}{gps_str} ({time_str})")


# ────────────────────────────────────────────────────────────────────────
# Visual card widget for a single priority item
# ────────────────────────────────────────────────────────────────────────
class PriorityCardWidget(QFrame):
    """Rich card showing snapshot image + priority info for one item."""

    remove_requested = pyqtSignal(int)  # index

    _CONDITION_COLORS = {
        "Critical": "#ff4444",
        "Warning":  "#ffaa00",
        "Normal":   "#44ff44",
        "Unknown":  "#aaaaaa",
        "Manual":   "#66bbff",
    }

    def __init__(self, item: PriorityItem, index: int):
        super().__init__()
        self._item = item
        self._index = index
        self._init_ui()

    def _init_ui(self):
        item = self._item
        cond_color = self._CONDITION_COLORS.get(item.condition, "#ffffff")

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(
            f"PriorityCardWidget {{ background-color: #1e1e1e; "
            f"border: 2px solid {cond_color}; border-radius: 6px; }}"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(10)

        # ── Snapshot thumbnail (left) ──
        thumb_label = QLabel()
        thumb_label.setMinimumSize(80, 96)
        thumb_label.setMaximumSize(130, 156)
        thumb_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet(
            "background-color: #111; border: 1px solid #444; border-radius: 4px;"
        )

        if item.image_path and os.path.exists(item.image_path):
            pix = QPixmap(item.image_path)
            if not pix.isNull():
                thumb_label.setPixmap(
                    pix.scaled(thumb_label.size(), Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
                )
            else:
                thumb_label.setText("No image")
                thumb_label.setStyleSheet(
                    "background-color: #111; border: 1px solid #444; "
                    "border-radius: 4px; color: #888; font-size: 10px;"
                )
        else:
            thumb_label.setText("No image")
            thumb_label.setStyleSheet(
                "background-color: #111; border: 1px solid #444; "
                "border-radius: 4px; color: #888; font-size: 10px;"
            )

        root.addWidget(thumb_label)

        # ── Info column (right) ──
        info = QVBoxLayout()
        info.setSpacing(3)

        # Row 1 – Person ID + condition badge
        row1 = QHBoxLayout()
        id_lbl = QLabel(
            f"Person #{item.tracker_id}" if item.tracker_id >= 0 else "Manual Entry"
        )
        id_lbl.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #4a90e2; background: transparent;"
        )
        row1.addWidget(id_lbl)
        row1.addStretch()

        badge = QLabel(f"  {item.condition}  ")
        badge.setStyleSheet(
            f"background-color: {cond_color}; color: #000; font-weight: bold; "
            f"font-size: 11px; border-radius: 3px; padding: 2px 6px;"
        )
        row1.addWidget(badge)
        info.addLayout(row1)

        # Row 2 – Posture + Score
        score_lbl = QLabel(
            f"Posture: {item.posture_type}   |   Score: {item.priority_score}/100"
        )
        score_lbl.setStyleSheet(
            f"color: {cond_color}; font-size: 12px; font-weight: bold; background: transparent;"
        )
        info.addWidget(score_lbl)

        # Row 3 – Description
        desc_lbl = QLabel(item.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #cccccc; font-size: 11px; background: transparent;")
        info.addWidget(desc_lbl)

        # Row 4 – GPS + Timestamp
        meta_parts = []
        if item.gps_coords:
            lat, lon = item.gps_coords
            meta_parts.append(f"\U0001f4cd {lat:.6f}, {lon:.6f}")
        meta_parts.append(f"\U0001f552 {item.timestamp.strftime('%H:%M:%S')}")
        meta_lbl = QLabel("   ".join(meta_parts))
        meta_lbl.setStyleSheet("color: #888; font-size: 10px; background: transparent;")
        info.addWidget(meta_lbl)

        info.addStretch()

        # Small remove button
        rm_btn = QPushButton("\u2716")
        rm_btn.setFixedSize(22, 22)
        rm_btn.setToolTip("Remove this item")
        rm_btn.setStyleSheet(
            "QPushButton { background: #555; color: #fff; border-radius: 11px; font-size: 11px; }"
            "QPushButton:hover { background: #e74c3c; }"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self._index))

        btn_col = QVBoxLayout()
        btn_col.addWidget(rm_btn)
        btn_col.addStretch()

        root.addLayout(info, 1)
        root.addLayout(btn_col)


# ────────────────────────────────────────────────────────────────────────
# Main Priority Tab
# ────────────────────────────────────────────────────────────────────────
class PriorityTab(QWidget):
    """Priority list UI with automatic posture-based priority generation"""

    request_analysis = pyqtSignal(int)

    def __init__(self, mavlink_manager=None):
        super().__init__()
        self.mavlink_manager = mavlink_manager
        self.priority_items = []
        self.auto_add_enabled = True
        self.init_ui()
        self.apply_stylesheet()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        header = QLabel("\U0001f6a8 Priority List - Human Condition Assessment")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        main_layout.addWidget(header)

        info = QLabel(
            "Automatically generated priorities based on human posture analysis "
            "using MediaPipe.\nHigher scores indicate more urgent conditions "
            "requiring immediate attention."
        )
        info.setStyleSheet("color: #aaaaaa; font-size: 11px; margin-bottom: 5px;")
        info.setWordWrap(True)
        main_layout.addWidget(info)

        self.auto_checkbox = QCheckBox("Auto-add detected persons")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.stateChanged.connect(self._toggle_auto_add)
        self.auto_checkbox.setStyleSheet("color: #ffffff; font-size: 12px;")
        main_layout.addWidget(self.auto_checkbox)

        # ── Scrollable card list ──
        cards_group = QGroupBox("Priority Queue (sorted by urgency)")
        cards_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff; font-weight: bold;
                border: 1px solid #3d3d3d; border-radius: 5px;
                margin-top: 10px; padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
                color: #4a90e2;
            }
        """)
        cards_inner = QVBoxLayout(cards_group)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        self._scroll.setWidget(self._cards_container)
        cards_inner.addWidget(self._scroll)
        main_layout.addWidget(cards_group, 1)

        # ── Manual entry ──
        manual_group = QGroupBox("Manual Entry")
        manual_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff; font-weight: bold;
                border: 1px solid #3d3d3d; border-radius: 5px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { color: #4a90e2; }
        """)
        manual_layout = QHBoxLayout(manual_group)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Add custom priority item...")
        self.input_edit.setStyleSheet(
            "QLineEdit { background-color: #2b2b2b; color: #ffffff; "
            "border: 1px solid #3d3d3d; border-radius: 3px; padding: 8px; }"
        )
        self.input_edit.returnPressed.connect(self.add_manual_item)
        manual_layout.addWidget(self.input_edit)

        add_btn = QPushButton("\u2795 Add")
        add_btn.clicked.connect(self.add_manual_item)
        add_btn.setStyleSheet(self._button_style("#4a90e2"))
        manual_layout.addWidget(add_btn)
        main_layout.addWidget(manual_group)

        # ── Control buttons ──
        controls = QHBoxLayout()
        controls.setSpacing(10)

        clear_btn = QPushButton("\U0001f9f9 Clear All")
        clear_btn.clicked.connect(self.clear_all)
        clear_btn.setStyleSheet(self._button_style("#e74c3c"))
        controls.addWidget(clear_btn)

        export_btn = QPushButton("\U0001f4c4 Export List")
        export_btn.clicked.connect(self.export_list)
        export_btn.setStyleSheet(self._button_style("#27ae60"))
        controls.addWidget(export_btn)
        main_layout.addLayout(controls)

        self.stats_label = QLabel("Items: 0 | Critical: 0 | Warning: 0 | Normal: 0")
        self.stats_label.setStyleSheet("color: #888888; font-size: 10px;")
        main_layout.addWidget(self.stats_label)

    @staticmethod
    def _button_style(color):
        return (
            f"QPushButton {{ background-color: {color}; color: white; border: none; "
            f"border-radius: 4px; padding: 8px 16px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {color}dd; }}"
            f"QPushButton:pressed {{ background-color: {color}bb; }}"
        )

    def _toggle_auto_add(self, state):
        self.auto_add_enabled = (state == Qt.Checked)

    # ── public API ───────────────────────────────────────────────────
    def add_priority_item(self, priority_item):
        if not self.auto_add_enabled:
            return
        for existing in self.priority_items:
            if existing.tracker_id == priority_item.tracker_id:
                if abs(existing.priority_score - priority_item.priority_score) > 10:
                    existing.priority_score = priority_item.priority_score
                    existing.condition = priority_item.condition
                    existing.description = priority_item.description
                    existing.posture_type = priority_item.posture_type
                    existing.timestamp = priority_item.timestamp
                    if priority_item.image_path:
                        existing.image_path = priority_item.image_path
                    self._refresh_cards()
                return
        self.priority_items.append(priority_item)
        self._refresh_cards()
        if priority_item.condition == "Critical":
            self._show_critical_alert(priority_item)

    def add_manual_item(self):
        text = self.input_edit.text().strip()
        if not text:
            return
        manual_item = PriorityItem(
            condition="Manual", description=text, posture_type="N/A",
            priority_score=50, tracker_id=-1, timestamp=datetime.now()
        )
        self.priority_items.append(manual_item)
        self.input_edit.clear()
        self._refresh_cards()

    def clear_all(self):
        if QMessageBox.question(
            self, "Clear All", "Clear all priority items?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.priority_items.clear()
            self._refresh_cards()

    def _remove_item(self, index):
        if 0 <= index < len(self.priority_items):
            del self.priority_items[index]
            self._refresh_cards()

    # ── card management ──────────────────────────────────────────────
    def _refresh_cards(self):
        self.priority_items.sort(key=lambda x: x.priority_score, reverse=True)
        while self._cards_layout.count() > 1:
            child = self._cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for idx, item in enumerate(self.priority_items):
            card = PriorityCardWidget(item, idx)
            card.remove_requested.connect(self._remove_item)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._update_stats()

    def _update_stats(self):
        total = len(self.priority_items)
        critical = sum(1 for x in self.priority_items if x.condition == "Critical")
        warning = sum(1 for x in self.priority_items if x.condition == "Warning")
        normal = sum(1 for x in self.priority_items if x.condition == "Normal")
        self.stats_label.setText(
            f"Items: {total} | Critical: {critical} | Warning: {warning} | Normal: {normal}"
        )

    def _show_critical_alert(self, item):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("\u26a0\ufe0f Critical Priority Detected")
        msg.setText(f"Person #{item.tracker_id}: {item.description}")
        gps_text = ""
        if item.gps_coords:
            lat, lon = item.gps_coords
            gps_text = f"\n\nGPS: {lat:.6f}, {lon:.6f}"
        msg.setInformativeText(
            f"Posture: {item.posture_type}\n"
            f"Priority Score: {item.priority_score}/100{gps_text}"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()

    def export_list(self):
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
                        if item.image_path:
                            f.write(f"   Image: {item.image_path}\n")
                        f.write("\n")
                QMessageBox.information(self, "Export", f"List exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")

    def apply_stylesheet(self):
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
            color: #ffffff;
        }
        QGroupBox::title {
            color: #4a90e2;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QLabel {
            color: #ffffff;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        """)
