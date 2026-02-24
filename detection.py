"""
Detection Engine - YOLOv8 Human Detection with Geotagging
"""

import cv2
import numpy as np
from ultralytics import YOLO
import math
import os
from datetime import datetime


class DetectionEngine:
    """YOLOv8-based human detection engine"""
    
    def __init__(self, model_path='best.pt'):
        """
        Initialize detection engine
        
        Args:
            model_path: Path to YOLOv8 model weights
        """
        self.model = None
        self.model_path = model_path
        self.class_names = []
        self.person_class_id = 0
        
        # Camera parameters (adjust based on your camera)
        self.camera_fov_h = 62.2  # Horizontal FOV in degrees
        self.camera_fov_v = 48.8  # Vertical FOV in degrees
        
        try:
            self.load_model()
        except Exception as e:
            print(f"Model load error: {e}")
    
    def load_model(self):
        """Load YOLOv8 model - tries multiple paths"""
        _here = os.path.dirname(os.path.abspath(__file__))
        _parent = os.path.dirname(_here)

        # Try multiple possible paths (explicit path first, then local,
        # then parent directory where the .pt file often lives)
        paths = [
            self.model_path,
            "best.pt",
            "yolov8n.pt",
            "yolov8s.pt",
            os.path.join(_here, "best.pt"),
            os.path.join(_here, "yolov8n.pt"),
            os.path.join(_parent, "best.pt"),
            os.path.join(_parent, "yolov8n.pt"),
            os.path.join(_parent, "yolov8s.pt"),
        ]
        
        for path in paths:
            if os.path.exists(path):
                try:
                    self.model = YOLO(path)
                    self.class_names = self.model.names
                    
                    # Find person class ID
                    for class_id, name in self.class_names.items():
                        if name.lower() == 'person':
                            self.person_class_id = class_id
                            break
                    
                    print(f"✓ Model loaded: {path}")
                    print(f"✓ Person class ID: {self.person_class_id}")
                    return True
                    
                except Exception as e:
                    print(f"✗ Failed to load model from {path}: {e}")
                    continue
        
        # If no model found
        print("✗ No model file found in any expected location")
        print(f"  Tried: {', '.join(paths)}")
        print(f"  Please place a YOLOv8 model file (best.pt or yolov8n.pt) in the project directory")
        self.model = None
        return False
    
    def detect(self, frame, confidence_threshold=0.5):
        """
        Detect humans in frame
        
        Args:
            frame: OpenCV frame (BGR)
            confidence_threshold: Minimum confidence score
            
        Returns:
            List of detections: [(x1, y1, x2, y2, confidence, class_id), ...]
        """
        if self.model is None:
            return []
        
        try:
            # Run inference - restrict to person class only for efficiency
            results = self.model(
                frame,
                conf=confidence_threshold,
                classes=[self.person_class_id],
                verbose=False,
            )
            
            detections = []
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    
                    # Only person class (already filtered by classes= above)
                    detections.append((
                        int(x1), int(y1), int(x2), int(y2),
                        confidence, class_id
                    ))
            
            return detections
            
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def draw_detections(self, frame, detections, trackers=None):
        """
        Draw bounding boxes on frame
        
        Args:
            frame: OpenCV frame
            detections: List of detections
            trackers: Optional tracker objects with IDs
            
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        for i, detection in enumerate(detections):
            x1, y1, x2, y2, confidence, class_id = detection
            
            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Label
            if trackers and i < len(trackers):
                tracker_id = trackers[i].tracker_id
                label = f"Person #{tracker_id} ({confidence:.2f})"
            else:
                label = f"Person ({confidence:.2f})"
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(
                annotated_frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated_frame,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )
        
        return annotated_frame
    
    def compute_gps_coordinates(self, detection, frame_shape, telemetry):
        """
        Compute GPS coordinates of detected person using drone telemetry
        
        Args:
            detection: (x1, y1, x2, y2, conf, class_id)
            frame_shape: (height, width)
            telemetry: Dict with drone position and attitude
            
        Returns:
            (lat, lon) or None if computation fails
        """
        try:
            x1, y1, x2, y2, _, _ = detection
            frame_h, frame_w = frame_shape[:2]
            
            # Calculate detection center in pixel coordinates
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Convert to normalized coordinates (-0.5 to 0.5)
            norm_x = (center_x / frame_w) - 0.5
            norm_y = (center_y / frame_h) - 0.5
            
            # Get drone telemetry
            drone_lat = telemetry.get('lat', 0)
            drone_lon = telemetry.get('lon', 0)
            drone_alt = telemetry.get('alt', 0)
            pitch = telemetry.get('pitch', 0)  # degrees
            
            if drone_lat == 0 or drone_lon == 0:
                return None
            
            # Calculate angle offsets based on camera FOV
            angle_x = norm_x * self.camera_fov_h
            angle_y = norm_y * self.camera_fov_v
            
            # Adjust for pitch (camera looking down)
            effective_pitch = pitch + angle_y
            
            # Estimate ground distance using altitude and pitch
            if abs(effective_pitch) > 85:  # Nearly vertical
                ground_distance = 0
            else:
                ground_distance = drone_alt / math.tan(math.radians(abs(effective_pitch)))
            
            # Calculate GPS offset
            # Convert angle_x to bearing offset
            bearing = angle_x  # Simplified, should include yaw
            
            # Calculate new GPS coordinates
            # Earth radius in meters
            R = 6371000
            
            # Convert to radians
            lat_rad = math.radians(drone_lat)
            lon_rad = math.radians(drone_lon)
            bearing_rad = math.radians(bearing)
            
            # Calculate new position
            new_lat_rad = math.asin(
                math.sin(lat_rad) * math.cos(ground_distance / R) +
                math.cos(lat_rad) * math.sin(ground_distance / R) * math.cos(bearing_rad)
            )
            
            new_lon_rad = lon_rad + math.atan2(
                math.sin(bearing_rad) * math.sin(ground_distance / R) * math.cos(lat_rad),
                math.cos(ground_distance / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
            )
            
            new_lat = math.degrees(new_lat_rad)
            new_lon = math.degrees(new_lon_rad)
            
            return (new_lat, new_lon)
            
        except Exception as e:
            print(f"GPS computation error: {e}")
            return None


class VideoStreamCapture:
    """
    RTSP video stream capture using an **ffmpeg subprocess pipe** with
    **hardware HEVC decoding**.

    The drone camera outputs HEVC (H.265) with a non-standard GOP /
    reference-picture structure.  FFmpeg's *software* HEVC decoder
    cannot resolve the broken inter-frame references and produces
    all-gray frames.

    **Hardware decoders** (NVIDIA CUVID, Intel QSV, DXVA2) are more
    tolerant and decode every frame correctly.  This class tries them
    in order and falls back to software decode + OpenCV only as a
    last resort.
    """

    # Hardware decoders to try, in priority order.
    # hevc_cuvid  = NVIDIA GPU  (fastest, most tolerant)
    # hevc_qsv    = Intel iGPU  (also works perfectly)
    # d3d11va     = generic Windows HW accel
    HW_DECODERS = ["hevc_cuvid", "hevc_qsv"]

    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.connected = False

        self._proc = None
        self._latest_frame = None
        self._frame_lock = __import__('threading').Lock()
        self._frame_ready = __import__('threading').Event()
        self._reader_thread = None
        self._stderr_thread = None
        self._stop = False

        # Resolution – default 1920x1080 (correct for this camera)
        self._width = 1920
        self._height = 1080
        self._frame_size = self._width * self._height * 3

    # ------------------------------------------------------------------
    @staticmethod
    def _find_ffmpeg():
        """Return path to an ffmpeg executable."""
        import shutil, glob

        # 1. System PATH
        ff = shutil.which("ffmpeg")
        if ff:
            return ff

        # 2. imageio-ffmpeg vendored binary
        try:
            import imageio_ffmpeg
            try:
                path = imageio_ffmpeg.get_ffmpeg_exe()
                if path and os.path.isfile(path):
                    return path
            except Exception:
                pass
            # Direct lookup in the package's binaries folder
            pkg_dir = os.path.dirname(imageio_ffmpeg.__file__)
            bin_dir = os.path.join(pkg_dir, "binaries")
            for c in glob.glob(os.path.join(bin_dir, "ffmpeg*")):
                if os.path.isfile(c):
                    return c
        except ImportError:
            pass

        return None

    # ------------------------------------------------------------------
    def _try_start_ffmpeg(self, ffmpeg, decoder_args, label):
        """Try to start ffmpeg with given decoder args, read 3 test
        frames, and return True if they contain real image data."""
        import subprocess, threading
        import numpy as np

        cmd = [
            ffmpeg,
            "-rtsp_transport", "tcp",
            *decoder_args,
            "-i", self.rtsp_url,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-an", "-sn",
            "-loglevel", "error",
            "-",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self._frame_size * 2,
            )
        except Exception as e:
            print(f"  ✗ {label}: failed to start ({e})")
            return None

        # Read up to 3 test frames with a timeout
        import time
        start = time.time()
        for i in range(3):
            if time.time() - start > 8:
                print(f"  ✗ {label}: timeout waiting for frames")
                proc.terminate()
                try: proc.wait(timeout=2)
                except: proc.kill()
                return None

            raw = proc.stdout.read(self._frame_size)
            if len(raw) != self._frame_size:
                print(f"  ✗ {label}: incomplete frame ({len(raw)} bytes)")
                proc.terminate()
                try: proc.wait(timeout=2)
                except: proc.kill()
                return None

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                (self._height, self._width, 3)
            )

            if frame.std() > 10:
                # Valid frame! This decoder works.
                print(f"  ✓ {label}: valid frame (std={frame.std():.1f})")
                # Store this frame and return the running process
                with self._frame_lock:
                    self._latest_frame = frame
                self._frame_ready.set()
                return proc

        # All 3 frames were gray
        print(f"  ✗ {label}: all frames gray")
        proc.terminate()
        try: proc.wait(timeout=2)
        except: proc.kill()
        return None

    # ------------------------------------------------------------------
    def connect(self):
        """Start the ffmpeg subprocess and reader thread.

        Tries hardware decoders first (NVIDIA CUVID, Intel QSV), then
        falls back to software decode, then OpenCV as last resort.
        """
        import subprocess, threading

        ffmpeg = self._find_ffmpeg()
        if ffmpeg is None:
            print("⚠ No ffmpeg binary found – falling back to OpenCV")
            return self._connect_opencv_fallback()

        print(f"✓ Using ffmpeg: {ffmpeg}")
        print(f"✓ Trying hardware decoders for HEVC stream...")

        # Try each hardware decoder
        self._stop = False
        proc = None

        for hw_dec in self.HW_DECODERS:
            proc = self._try_start_ffmpeg(
                ffmpeg, ["-c:v", hw_dec], label=hw_dec
            )
            if proc is not None:
                break

        # Fallback: software decode (will likely produce gray, but try)
        if proc is None:
            print("  ⚠ No hardware decoder worked, trying software decode...")
            proc = self._try_start_ffmpeg(
                ffmpeg, [], label="software"
            )

        if proc is None:
            print("  ⚠ ffmpeg decode failed – falling back to OpenCV")
            return self._connect_opencv_fallback()

        self._proc = proc
        self.connected = True

        # Background thread: read decoded frames from pipe
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="ffmpeg-reader"
        )
        self._reader_thread.start()

        # Background thread: drain stderr (filter POC noise)
        self._stderr_thread = threading.Thread(
            target=self._stderr_drain, daemon=True, name="ffmpeg-stderr"
        )
        self._stderr_thread.start()

        print("✓ Video stream active – hardware HEVC decoding")
        return True, "Connected to video stream (hardware HEVC decode)"

    # ------------------------------------------------------------------
    def _reader_loop(self):
        """Read raw BGR24 frames from the ffmpeg stdout pipe."""
        import numpy as np

        while not self._stop and self._proc and self._proc.poll() is None:
            raw = self._proc.stdout.read(self._frame_size)
            if len(raw) != self._frame_size:
                break  # stream ended or error

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                (self._height, self._width, 3)
            )

            with self._frame_lock:
                self._latest_frame = frame
            self._frame_ready.set()

    # ------------------------------------------------------------------
    def _stderr_drain(self):
        """Drain ffmpeg stderr; suppress known HEVC / HW decode warnings."""
        if not self._proc or not self._proc.stderr:
            return
        for raw_line in self._proc.stderr:
            line = raw_line.decode(errors="ignore").strip()
            # Suppress known non-fatal warnings
            if "Could not find ref with POC" in line:
                continue
            if "Failed to execute" in line:
                continue
            if "hardware accelerator failed to decode picture" in line:
                continue
            if line:
                print(f"[ffmpeg] {line}")

    # ------------------------------------------------------------------
    def _connect_opencv_fallback(self):
        """Fall back to cv2.VideoCapture if ffmpeg binary is unavailable."""
        import threading

        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            return False, "Failed to open video stream"

        self._stop = False
        self.connected = True

        self._reader_thread = threading.Thread(
            target=self._opencv_reader_loop, daemon=True, name="cv-reader"
        )
        self._reader_thread.start()

        if self._frame_ready.wait(timeout=5.0):
            return True, "Connected (OpenCV fallback)"
        return True, "Connected (waiting for first frame…)"

    def _opencv_reader_loop(self):
        """Fallback: decode via OpenCV (may show POC warnings in console)."""
        import time
        while not self._stop:
            cap = getattr(self, "_cap", None)
            if cap is None or not cap.isOpened():
                break
            ret, frame = cap.read()
            if ret and frame is not None:
                with self._frame_lock:
                    self._latest_frame = frame
                self._frame_ready.set()
            else:
                time.sleep(0.005)

    # ------------------------------------------------------------------
    def read_frame(self):
        """Return the most recently decoded frame (non-blocking)."""
        if not self.connected:
            return False, None

        with self._frame_lock:
            frame = self._latest_frame
        self._frame_ready.clear()

        if frame is None:
            return False, None
        return True, frame

    # ------------------------------------------------------------------
    def release(self):
        """Stop ffmpeg / OpenCV and clean up all threads."""
        self._stop = True
        self.connected = False

        if self._proc:
            try:
                self._proc.stdout.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

        cap = getattr(self, "_cap", None)
        if cap:
            cap.release()
            self._cap = None

        for t in [self._reader_thread, self._stderr_thread]:
            if t and t.is_alive():
                t.join(timeout=2.0)

    # ------------------------------------------------------------------
    def is_connected(self):
        if self._proc:
            return self.connected and self._proc.poll() is None
        cap = getattr(self, "_cap", None)
        if cap:
            return self.connected and cap.isOpened()
        return False
