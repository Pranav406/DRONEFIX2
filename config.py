"""
Configuration File - Drone GCS Settings
Edit this file to customize application behavior
"""

# ========================================
# RTSP Video Stream Settings
# ========================================
RTSP_STREAM_URL = "rtsp://192.168.144.25:8554/main.264"

# Video buffer size (lower = less latency, higher = more stable)
VIDEO_BUFFER_SIZE = 1

# ========================================
# YOLOv8 Detection Settings
# ========================================
# Model path - will try multiple locations
import os
YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "C:/Users/Nick/Downloads/drone/DroneSW-Main/yolov8n.pt")

# Confidence threshold for detections (0.0 - 1.0)
DETECTION_CONFIDENCE = 0.5

# Person class ID (usually 0 for person in COCO dataset)
PERSON_CLASS_ID = 0

# ========================================
# MediaPipe Posture Analysis Settings
# ========================================
# MediaPipe automatically downloads models to cache
# No model path needed - models are managed automatically

# Minimum detection confidence (0.0 - 1.0)
MEDIAPIPE_MIN_DETECTION_CONFIDENCE = 0.5

# Minimum tracking confidence (0.0 - 1.0)
MEDIAPIPE_MIN_TRACKING_CONFIDENCE = 0.5

# Model complexity (0=Lite, 1=Full, 2=Heavy)
# Lite: Faster, less accurate
# Full: Balanced (recommended)
# Heavy: Slower, more accurate
MEDIAPIPE_MODEL_COMPLEXITY = 1

# Enable smooth landmarks over time
MEDIAPIPE_SMOOTH_LANDMARKS = True

# Optional: Custom model cache directory (None = use system default)
# MediaPipe caches models here: ~/.mediapipe/models (Linux/Mac)
#                           or: %LOCALAPPDATA%\.mediapipe\models (Windows)
MEDIAPIPE_MODEL_CACHE = None  # Set to custom path if needed, e.g., "C:/mediapipe_models"

# ========================================
# Camera Settings
# ========================================
# Horizontal field of view in degrees
CAMERA_FOV_HORIZONTAL = 62.2

# Vertical field of view in degrees
CAMERA_FOV_VERTICAL = 48.8

# ========================================
# Tracking Settings
# ========================================
# Maximum frames a tracker can disappear before being removed
TRACKER_MAX_DISAPPEARED = 30

# Maximum distance (pixels) for matching detections to trackers
TRACKER_DISTANCE_THRESHOLD = 100

# ========================================
# Snapshot Storage Settings
# ========================================
# Maximum number of snapshots to keep
MAX_SNAPSHOTS = 1000

# Maximum age of snapshots in days
MAX_SNAPSHOT_AGE_DAYS = 7

# ========================================
# Altitude Limits (in meters)
# ========================================
# Maximum altitude - regulatory limit in most countries
MAX_ALTITUDE_M = 120

# Minimum altitude for safe operations
MIN_ALTITUDE_M = 5

# Minimum altitude for effective detection
MIN_DETECTION_ALTITUDE_M = 10

# ========================================
# Battery Settings
# ========================================
# Minimum battery percentage for mission start
MIN_BATTERY_PERCENT = 30

# ========================================
# MAVLink Connection Settings
# ========================================
# Default baudrate for serial connection
MAVLINK_BAUDRATE = 57600

# Connection timeout in seconds
MAVLINK_TIMEOUT = 10

# Telemetry update rate (seconds)
TELEMETRY_UPDATE_RATE = 0.1

# ========================================
# Mission Planning Settings
# ========================================
# Default waypoint altitude in meters
DEFAULT_ALTITUDE = 10

# Minimum altitude (meters)
MIN_ALTITUDE = 5

# Maximum altitude (meters)
MAX_ALTITUDE = 120

# Default waypoint spacing for smoothing (meters)
DEFAULT_SPACING = 10

# Waypoint acceptance radius (meters)
WAYPOINT_ACCEPTANCE_RADIUS = 2

# ========================================
# Map Settings
# ========================================
# Default map zoom level for mission preview
MISSION_MAP_ZOOM = 15

# Default map zoom level for live view
LIVE_MAP_ZOOM = 18

# Live map update interval (milliseconds)
LIVE_MAP_UPDATE_INTERVAL = 1000

# ========================================
# UI Settings
# ========================================
# Main window default size
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# Video display size
VIDEO_DISPLAY_WIDTH = 640
VIDEO_DISPLAY_HEIGHT = 480

# ========================================
# Logging Settings
# ========================================
# Enable debug logging
DEBUG_MODE = False

# Log file path (None = no file logging)
LOG_FILE_PATH = None

# ========================================
# Advanced Settings
# ========================================
# Enable GPU acceleration for YOLOv8 (requires CUDA)
USE_GPU = True

# Number of threads for video processing
VIDEO_PROCESSING_THREADS = 1

# Enable mission verification after upload
VERIFY_MISSION_UPLOAD = True

