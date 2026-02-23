"""
Live Detection Tab - Real-time video, detection, telemetry, and mapping
"""

import os
import cv2
import folium
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QScrollArea, QSplitter,
                             QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
from detection import DetectionEngine, VideoStreamCapture
from tracker import MultiObjectTracker
from posture_analyzer import PostureAnalyzer
from ui_priority_tab import PriorityItem
import config  # Import config module


class VideoProcessingThread(QThread):
    """
    Background thread for video display and detection.

    Display and detection are intentionally decoupled:
    - Every available frame is emitted for smooth video (targets ~25 FPS).
    - YOLOv8 detection runs only every DETECT_EVERY_N_FRAMES frames so that
      slow CPU inference does not stall the video feed.
    - The stream's grab-thread (inside VideoStreamCapture) continuously drains
      the decoder buffer so we always get the freshest frame.
    """

    # Emit (annotated_frame, detections, trackers) to the UI
    frame_processed = pyqtSignal(np.ndarray, list, list)
    error_occurred = pyqtSignal(str)

    # Run detection once every N frames (tune to balance CPU vs latency)
    DETECT_EVERY_N_FRAMES = 5

    def __init__(self, rtsp_url, detection_engine, tracker, mavlink_manager):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.detection_engine = detection_engine
        self.tracker = tracker
        self.mavlink_manager = mavlink_manager
        self.running = False
        self.stream = None

    def run(self):
        import time
        self.running = True
        self.stream = VideoStreamCapture(self.rtsp_url)

        try:
            success, message = self.stream.connect()
            if not success:
                self.error_occurred.emit(f"Stream connection failed: {message}")
                return

            frame_counter = 0
            last_detections = []
            last_trackers = []

            while self.running:
                # Grab the latest frame (non-blocking)
                ret, frame = self.stream.read_frame()

                if not ret or frame is None:
                    # No new frame yet – yield briefly to avoid busy-wait
                    time.sleep(0.01)
                    continue

                frame_counter += 1

                try:
                    # --- Run detection only on every Nth frame ---
                    if frame_counter % self.DETECT_EVERY_N_FRAMES == 0:
                        detections = self.detection_engine.detect(
                            frame, confidence_threshold=0.5
                        )

                        telemetry = self.mavlink_manager.get_telemetry()
                        gps_coords_list = [
                            self.detection_engine.compute_gps_coordinates(
                                det, frame.shape, telemetry
                            )
                            for det in detections
                        ]

                        last_trackers = self.tracker.update(
                            detections, gps_coords_list, frame
                        )
                        last_detections = detections

                    # --- Always draw the latest boxes on every frame ---
                    annotated_frame = self.detection_engine.draw_detections(
                        frame, last_detections, last_trackers
                    )

                    self.frame_processed.emit(
                        annotated_frame, last_detections, last_trackers
                    )

                    del frame
                    del annotated_frame

                except Exception as e:
                    self.error_occurred.emit(f"Processing error: {str(e)}")

        finally:
            if self.stream:
                self.stream.release()
                self.stream = None

    def stop(self):
        """Stop processing"""
        self.running = False


class DetectionCard(QFrame):
    """Widget displaying a single detected person"""
    
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.init_ui()
        
    def init_ui(self):
        """Initialize card UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMinimumHeight(150)
        
        layout = QVBoxLayout(self)
        
        # Person ID
        id_label = QLabel(f"Person #{self.tracker.tracker_id}")
        id_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4a90e2;")
        layout.addWidget(id_label)
        
        # Snapshot
        snapshot_label = QLabel()
        if self.tracker.snapshot is not None:
            h, w = self.tracker.snapshot.shape[:2]
            
            # Resize for display
            display_w = 120
            display_h = int(h * display_w / w)
            
            resized = cv2.resize(self.tracker.snapshot, (display_w, display_h))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            snapshot_label.setPixmap(QPixmap.fromImage(qt_image))
        else:
            snapshot_label.setText("No snapshot")
            snapshot_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(snapshot_label, alignment=Qt.AlignCenter)
        
        # GPS coordinates
        if self.tracker.gps_coords:
            lat, lon = self.tracker.gps_coords
            gps_label = QLabel(f"📍 {lat:.6f}, {lon:.6f}")
            gps_label.setStyleSheet("color: #88ff88; font-size: 11px;")
        else:
            gps_label = QLabel("📍 No GPS data")
            gps_label.setStyleSheet("color: #888; font-size: 11px;")
        
        layout.addWidget(gps_label)
        
        # Timestamp
        time_label = QLabel(f"🕒 {self.tracker.last_seen.strftime('%H:%M:%S')}")
        time_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(time_label)
        
        # Tracked frames
        frames_label = QLabel(f"Frames: {self.tracker.frames_tracked}")
        frames_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(frames_label)


class LiveDetectionTab(QWidget):
    """Tab for live video, detection, and telemetry"""
    
    def __init__(self, mavlink_manager, priority_tab=None):
        super().__init__()
        self.mavlink_manager = mavlink_manager
        self.priority_tab = priority_tab
        
        # Detection components
        self.detection_engine = None
        self.tracker = MultiObjectTracker(max_disappeared=2, distance_threshold=100)
        self.video_thread = None
        
        # Posture analyzer
        try:
            self.posture_analyzer = PostureAnalyzer()
            self.posture_enabled = True
        except Exception as e:
            print(f"Posture analyzer unavailable: {e}")
            self.posture_analyzer = None
            self.posture_enabled = False
        
        # Snapshot save directory
        self.snapshot_dir = "detected_persons"
        os.makedirs(self.snapshot_dir, exist_ok=True)
        
        # Track analyzed trackers to avoid duplicate analysis
        self.analyzed_trackers = set()
        
        # RTSP stream URL from config
        self.rtsp_url = config.RTSP_STREAM_URL
        
        # UI state
        self.is_running = False

        # Frame-rate limiter for the display (target ~25 FPS)
        self._last_display_time = 0.0
        self._display_interval = 1.0 / 25.0

        self.init_ui()
        self.apply_stylesheet()
        
        # Connect telemetry updates
        self.mavlink_manager.telemetry_updated.connect(self.update_telemetry_display)
        
        # Map update timer
        self.map_timer = QTimer()
        self.map_timer.timeout.connect(self.update_live_map)
        
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout(self)
        
        # Title and controls
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Video and map
        left_panel = self.create_left_panel()
        
        # Right: Telemetry and detections
        right_panel = self.create_right_panel()
        
        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(content_splitter)
    
    def create_header(self):
        """Create header with controls"""
        header = QWidget()
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("Live Detection & Telemetry Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a90e2;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Control buttons
        self.start_btn = QPushButton("▶ Start Detection")
        self.start_btn.clicked.connect(self.start_detection)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #44aa44;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #55bb55;
            }
        """)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #aa4444;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #bb5555;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.stop_btn)
        
        return header
    
    def create_left_panel(self):
        """Create left panel with video and map"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Video feed
        video_group = QGroupBox("Live RTSP Video Feed")
        video_layout = QVBoxLayout(video_group)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #000; border: 2px solid #3d3d3d;")
        self.video_label.setText("Video feed will appear here\nClick 'Start Detection' to begin")
        
        video_layout.addWidget(self.video_label)
        
        # Stats
        self.stats_label = QLabel("Detections: 0 | FPS: 0")
        self.stats_label.setStyleSheet("color: #4a90e2; font-weight: bold;")
        video_layout.addWidget(self.stats_label)
        
        layout.addWidget(video_group, 2)
        
        # Live map
        map_group = QGroupBox("Live Drone Location & Detections")
        map_layout = QVBoxLayout(map_group)
        
        self.live_map_view = QWebEngineView()
        self.live_map_view.setMinimumHeight(250)
        map_layout.addWidget(self.live_map_view)
        
        layout.addWidget(map_group, 1)
        
        # Initialize map
        self.init_live_map()
        
        return panel
    
    def create_right_panel(self):
        """Create right panel with telemetry and detections"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Telemetry panel
        telemetry_group = self.create_telemetry_panel()
        layout.addWidget(telemetry_group)
        
        # Detections panel
        detections_group = self.create_detections_panel()
        layout.addWidget(detections_group, 1)
        
        return panel
    
    def create_telemetry_panel(self):
        """Create telemetry display panel"""
        group = QGroupBox("Live Drone Telemetry")
        layout = QGridLayout(group)
        
        # Create telemetry labels
        labels = [
            ("Latitude:", "lat_value"),
            ("Longitude:", "lon_value"),
            ("Altitude:", "alt_value"),
            ("Pitch:", "pitch_value"),
            ("Roll:", "roll_value"),
            ("Yaw:", "yaw_value"),
            ("Battery:", "battery_value"),
            ("Mode:", "mode_value"),
            ("Armed:", "armed_value"),
        ]
        
        self.telemetry_labels = {}
        
        for i, (label_text, key) in enumerate(labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            
            value = QLabel("--")
            value.setStyleSheet("color: #4a90e2;")
            
            layout.addWidget(label, i, 0)
            layout.addWidget(value, i, 1)
            
            self.telemetry_labels[key] = value
        
        return group
    
    def create_detections_panel(self):
        """Create detected persons panel"""
        group = QGroupBox("Detected Persons")
        layout = QVBoxLayout(group)
        
        # Scroll area for detection cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.detections_container = QWidget()
        self.detections_layout = QVBoxLayout(self.detections_container)
        self.detections_layout.addStretch()
        
        scroll.setWidget(self.detections_container)
        layout.addWidget(scroll)
        
        # Count label
        self.detection_count_label = QLabel("Active Detections: 0")
        self.detection_count_label.setStyleSheet("color: #4a90e2; font-weight: bold;")
        layout.addWidget(self.detection_count_label)
        
        return group
    
    def start_detection(self):
        """Start video processing and detection"""
        if self.is_running:
            return
        
        # Initialize detection engine
        try:
            self.detection_engine = DetectionEngine('best.pt')
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Model Error",
                f"Failed to load YOLOv8 model:\n{str(e)}\n\n"
                f"Make sure 'best.pt' exists in the application directory."
            )
            return
        
        # Start video processing thread
        self.video_thread = VideoProcessingThread(
            self.rtsp_url,
            self.detection_engine,
            self.tracker,
            self.mavlink_manager
        )
        
        self.video_thread.frame_processed.connect(self.update_video_display)
        self.video_thread.error_occurred.connect(self.handle_error)
        
        self.video_thread.start()
        
        # Update UI
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Start map updates
        self.map_timer.start(1000)  # Update every second
    
    def stop_detection(self):
        """Stop video processing"""
        if not self.is_running:
            return
        
        # Stop thread
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread.wait()
        
        # Stop map updates
        self.map_timer.stop()
        
        # Update UI
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Clear video
        self.video_label.clear()
        self.video_label.setText("Stopped")
    
    def update_video_display(self, frame, detections, trackers):
        """Update video display with processed frame"""
        import time

        # Throttle display to target FPS to avoid overwhelming the Qt event loop
        now = time.monotonic()
        if now - self._last_display_time < self._display_interval:
            return
        self._last_display_time = now

        # Convert frame to QPixmap
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit label
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.video_label.setPixmap(scaled_pixmap)
        
        # Analyze posture for new trackers and add to priority list
        if self.posture_enabled and self.posture_analyzer and self.priority_tab:
            self._analyze_and_prioritize(trackers)
        
        # Update stats
        self.stats_label.setText(f"Detections: {len(detections)} | Active Trackers: {len(trackers)}")
        
        # Update detection cards
        self.update_detection_cards(trackers)
    
    def update_detection_cards(self, trackers):
        """Update detection sidebar with tracker cards"""
        # Clear existing cards
        while self.detections_layout.count() > 1:  # Keep stretch
            item = self.detections_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new cards
        for tracker in trackers:
            card = DetectionCard(tracker)
            self.detections_layout.insertWidget(
                self.detections_layout.count() - 1,
                card
            )
        
        # Update count
        self.detection_count_label.setText(f"Active Detections: {len(trackers)}")
    
    def update_telemetry_display(self, telemetry):
        """Update telemetry display"""
        self.telemetry_labels['lat_value'].setText(f"{telemetry['lat']:.6f}°")
        self.telemetry_labels['lon_value'].setText(f"{telemetry['lon']:.6f}°")
        self.telemetry_labels['alt_value'].setText(f"{telemetry['alt']:.1f} m")
        self.telemetry_labels['pitch_value'].setText(f"{telemetry['pitch']:.1f}°")
        self.telemetry_labels['roll_value'].setText(f"{telemetry['roll']:.1f}°")
        self.telemetry_labels['yaw_value'].setText(f"{telemetry['yaw']:.1f}°")
        self.telemetry_labels['battery_value'].setText(f"{telemetry['battery']}%")
        self.telemetry_labels['mode_value'].setText(telemetry['mode'])
        self.telemetry_labels['armed_value'].setText("Yes" if telemetry['armed'] else "No")
    
    def init_live_map(self):
        """Initialize empty live map"""
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        html_path = os.path.join(os.path.dirname(__file__), 'temp_live_map.html')
        m.save(html_path)
        self.live_map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def update_live_map(self):
        """Update live map with drone position and detections"""
        telemetry = self.mavlink_manager.get_telemetry()
        
        lat = telemetry.get('lat', 0)
        lon = telemetry.get('lon', 0)
        
        if lat == 0 and lon == 0:
            return
        
        # Create map
        m = folium.Map(location=[lat, lon], zoom_start=18)
        
        # Add drone marker
        folium.Marker(
            [lat, lon],
            popup=f"Drone<br>Alt: {telemetry['alt']:.1f}m",
            tooltip="Drone Position",
            icon=folium.Icon(color='red', icon='plane', prefix='fa')
        ).add_to(m)
        
        # Add detected persons
        active_trackers = self.tracker.get_active_trackers()
        for tracker in active_trackers:
            if tracker.gps_coords:
                person_lat, person_lon = tracker.gps_coords
                folium.Marker(
                    [person_lat, person_lon],
                    popup=f"Person #{tracker.tracker_id}",
                    tooltip=f"Person #{tracker.tracker_id}",
                    icon=folium.Icon(color='orange', icon='user', prefix='fa')
                ).add_to(m)
        
        # Save and load
        html_path = os.path.join(os.path.dirname(__file__), 'temp_live_map.html')
        m.save(html_path)
        self.live_map_view.setUrl(QUrl.fromLocalFile(html_path))
    
    def handle_error(self, error_message):
        """Handle errors from video thread"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", error_message)
        self.stop_detection()
    
    def _analyze_and_prioritize(self, trackers):
        """
        Analyze posture for new/updated trackers and add to priority list
        
        Args:
            trackers: List of PersonTracker objects
        """
        # Get current active tracker IDs
        active_ids = {t.tracker_id for t in trackers}
        
        # Clean up old tracker IDs to prevent memory leak
        self.analyzed_trackers = self.analyzed_trackers.intersection(active_ids)
        
        for tracker in trackers:
            # Skip if already analyzed or no snapshot
            if tracker.tracker_id in self.analyzed_trackers or tracker.snapshot is None:
                continue
            
            try:
                # Analyze posture
                analysis = self.posture_analyzer.analyze_snapshot(tracker.snapshot)
                
                if analysis is None:
                    print(f"⚠️ Failed to analyze Person #{tracker.tracker_id}")
                    continue
                
                # Mark as analyzed
                self.analyzed_trackers.add(tracker.tracker_id)
                
                # Save snapshot with analysis
                try:
                    image_path = self.posture_analyzer.save_analyzed_snapshot(
                        tracker.snapshot,
                        analysis,
                        self.snapshot_dir,
                        tracker.tracker_id
                    )
                except Exception as e:
                    print(f"Failed to save snapshot: {e}")
                    image_path = None
                
                # Create priority item
                priority_item = PriorityItem(
                    condition=analysis.condition,
                    description=analysis.description,
                    posture_type=analysis.posture_type,
                    priority_score=analysis.priority_score,
                    tracker_id=tracker.tracker_id,
                    gps_coords=tracker.gps_coords,
                    image_path=image_path,
                    timestamp=analysis.timestamp
                )
                
                # Add to priority tab
                self.priority_tab.add_priority_item(priority_item)
                
                print(f"✓ Analyzed Person #{tracker.tracker_id}: "
                      f"{analysis.condition} - {analysis.posture_type} "
                      f"(Score: {analysis.priority_score})")
                      
            except Exception as e:
                print(f"❌ Analysis error for Person #{tracker.tracker_id}: {e}")
    
    def stop_all(self):
        """Stop all processing (called on app close)"""
        self.stop_detection()
    
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
        
        QLabel {
            color: #ffffff;
        }
        
        QFrame {
            background-color: #3d3d3d;
            border-radius: 5px;
            padding: 10px;
        }
        
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        """)
