"""
Posture Analyzer - Analyze human posture using MediaPipe Tasks API to assess urgency/condition
Compatible with Python 3.12+ via the MediaPipe Tasks Vision API (PoseLandmarker)
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from datetime import datetime
from dataclasses import dataclass
from typing import Tuple, Optional
import os
import urllib.request
import config  # Import configuration


# ── Pose landmark indices (same order as legacy mp.solutions.pose) ──
_NOSE = 0
_LEFT_SHOULDER = 11
_RIGHT_SHOULDER = 12
_LEFT_HIP = 23
_RIGHT_HIP = 24
_LEFT_KNEE = 25
_RIGHT_KNEE = 26
_LEFT_ANKLE = 27
_RIGHT_ANKLE = 28
_LEFT_WRIST = 15
_RIGHT_WRIST = 16

# ── Model download URLs ──
_MODEL_URLS = {
    0: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    1: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    2: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
}

_MODEL_FILENAMES = {
    0: "pose_landmarker_lite.task",
    1: "pose_landmarker_full.task",
    2: "pose_landmarker_heavy.task",
}


@dataclass
class PostureAnalysis:
    """Result of posture analysis"""
    condition: str  # "Critical", "Warning", "Normal"
    priority_score: int  # 1-100, higher = more urgent
    description: str
    posture_type: str  # "Lying", "Sitting", "Standing", "Fallen", "Waving"
    confidence: float
    timestamp: datetime


def _ensure_model(complexity: int, cache_dir: Optional[str] = None) -> str:
    """
    Return the local path to the .task model file, downloading it if needed.
    
    Args:
        complexity: 0 (Lite), 1 (Full), or 2 (Heavy)
        cache_dir: Optional directory to store models. Defaults to project dir.
        
    Returns:
        Absolute path to the .task model file
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), "mediapipe_models")
    os.makedirs(cache_dir, exist_ok=True)

    filename = _MODEL_FILENAMES.get(complexity, _MODEL_FILENAMES[1])
    local_path = os.path.join(cache_dir, filename)

    if os.path.exists(local_path):
        return local_path

    url = _MODEL_URLS.get(complexity, _MODEL_URLS[1])
    print(f"⬇ Downloading MediaPipe pose model ({filename}) …")
    print(f"  URL: {url}")
    try:
        urllib.request.urlretrieve(url, local_path)
        print(f"✓ Model saved to {local_path}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to download MediaPipe pose model from {url}: {e}\n"
            f"You can manually download it and place it at: {local_path}"
        ) from e

    return local_path


class PostureAnalyzer:
    """Analyze human posture and condition using MediaPipe Tasks PoseLandmarker API"""
    
    def __init__(self):
        """Initialize MediaPipe PoseLandmarker with settings from config"""
        complexity = getattr(config, "MEDIAPIPE_MODEL_COMPLEXITY", 1)
        cache_dir = getattr(config, "MEDIAPIPE_MODEL_CACHE", None)
        min_det_conf = getattr(config, "MEDIAPIPE_MIN_DETECTION_CONFIDENCE", 0.5)
        min_trk_conf = getattr(config, "MEDIAPIPE_MIN_TRACKING_CONFIDENCE", 0.5)

        # Download model if needed
        model_path = _ensure_model(complexity, cache_dir)

        # Build PoseLandmarker options (IMAGE mode for single-frame analysis)
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            min_pose_detection_confidence=min_det_conf,
            min_tracking_confidence=min_trk_conf,
            num_poses=1,
        )

        self.landmarker = mp_vision.PoseLandmarker.create_from_options(options)

        print(f"✓ MediaPipe PoseLandmarker (Tasks API) initialized:")
        print(f"  Model: {os.path.basename(model_path)}  (complexity={complexity})")
        print(f"  Min Detection Confidence: {min_det_conf}")
        print(f"  Min Tracking Confidence: {min_trk_conf}")
        
    def analyze_snapshot(self, image: np.ndarray) -> Optional[PostureAnalysis]:
        """
        Analyze a person snapshot to determine condition and priority.

        Uses a **hybrid** approach optimised for aerial / drone footage:
        1. Bounding-box aspect-ratio gives a reliable coarse posture estimate
           even from top-down views where MediaPipe landmarks are unreliable.
        2. If MediaPipe detects landmarks with good visibility the estimate is
           refined (e.g. waving detection).

        Args:
            image: BGR image of detected person (cropped bounding box)

        Returns:
            PostureAnalysis object or None if analysis fails
        """
        if image is None or image.size == 0:
            return None

        try:
            h, w = image.shape[:2]

            # ---- Step 1: bbox aspect-ratio based classification --------
            aspect = h / max(w, 1)
            bbox_posture, bbox_conf = self._classify_by_aspect_ratio(aspect)

            # ---- Step 2: pad & resize for better MediaPipe results -----
            padded = self._pad_image(image, pad_ratio=0.25)
            min_dim = 256
            ph, pw = padded.shape[:2]
            if ph < min_dim or pw < min_dim:
                scale = max(min_dim / ph, min_dim / pw)
                padded = cv2.resize(
                    padded,
                    (int(pw * scale), int(ph * scale)),
                    interpolation=cv2.INTER_LINEAR,
                )

            rgb_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

            result = self.landmarker.detect(mp_image)

            # ---- Step 3: refine with landmarks when available ----------
            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                landmarks = result.pose_landmarks[0]
                lm_posture, lm_conf = self._classify_posture(landmarks, padded.shape)

                # Only trust landmarks when average visibility is decent
                if lm_conf > 0.55:
                    posture_type = lm_posture
                    confidence = lm_conf
                else:
                    posture_type = bbox_posture
                    confidence = bbox_conf
            else:
                posture_type = bbox_posture
                confidence = bbox_conf

            condition, priority_score, description = self._calculate_priority(posture_type)

            return PostureAnalysis(
                condition=condition,
                priority_score=priority_score,
                description=description,
                posture_type=posture_type,
                confidence=confidence,
                timestamp=datetime.now(),
            )

        except Exception as e:
            print(f"Posture analysis error: {e}")
            return None

    # ------------------------------------------------------------------ #
    @staticmethod
    def _pad_image(image: np.ndarray, pad_ratio: float = 0.25) -> np.ndarray:
        """Add proportional padding around the crop so MediaPipe gets context."""
        h, w = image.shape[:2]
        pad_y = int(h * pad_ratio)
        pad_x = int(w * pad_ratio)
        return cv2.copyMakeBorder(
            image, pad_y, pad_y, pad_x, pad_x,
            cv2.BORDER_CONSTANT, value=(0, 0, 0),
        )

    @staticmethod
    def _classify_by_aspect_ratio(aspect: float) -> Tuple[str, float]:
        """
        Coarse posture classification using bounding-box aspect ratio.

        From drone / aerial view:
        - Standing person ≈ tall & narrow  (aspect > 1.4)
        - Sitting person  ≈ roughly square (0.7 < aspect ≤ 1.4)
        - Lying person    ≈ wide & short   (aspect ≤ 0.7)
        """
        if aspect > 1.4:
            return ("Standing", 0.65)
        elif aspect > 0.7:
            return ("Sitting", 0.55)
        else:
            return ("Lying", 0.65)
    
    def _classify_posture(self, landmarks, image_shape) -> Tuple[str, float]:
        """
        Classify posture from MediaPipe landmarks.

        Designed to work with both side-view and aerial camera angles.

        Returns:
            (posture_type, confidence)
        """
        h, w = image_shape[:2]

        nose = landmarks[_NOSE]
        left_shoulder = landmarks[_LEFT_SHOULDER]
        right_shoulder = landmarks[_RIGHT_SHOULDER]
        left_hip = landmarks[_LEFT_HIP]
        right_hip = landmarks[_RIGHT_HIP]
        left_knee = landmarks[_LEFT_KNEE]
        right_knee = landmarks[_RIGHT_KNEE]
        left_ankle = landmarks[_LEFT_ANKLE]
        right_ankle = landmarks[_RIGHT_ANKLE]
        left_wrist = landmarks[_LEFT_WRIST]
        right_wrist = landmarks[_RIGHT_WRIST]

        def _vis(lm):
            return lm.visibility if lm.visibility is not None else 0.5

        avg_visibility = float(np.mean([
            _vis(nose), _vis(left_shoulder), _vis(right_shoulder),
            _vis(left_hip), _vis(right_hip)
        ]))

        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        head_y = nose.y

        torso_len = abs(hip_y - shoulder_y)

        # -- Waving: at least ONE wrist clearly above shoulders ----------
        if _vis(left_wrist) > 0.4 or _vis(right_wrist) > 0.4:
            lw_above = left_wrist.y < shoulder_y - 0.10 and _vis(left_wrist) > 0.4
            rw_above = right_wrist.y < shoulder_y - 0.10 and _vis(right_wrist) > 0.4
            if (lw_above or rw_above) and avg_visibility > 0.5:
                return ("Waving", avg_visibility)

        # -- Lying: very short torso in normalised coords ----------------
        if torso_len < 0.12:
            return ("Lying", avg_visibility)

        # -- Fallen: head lower (larger y) than hips --------------------
        if head_y > hip_y + 0.05:
            return ("Fallen", avg_visibility)

        # -- Sitting: knees close to or above hip level -----------------
        knee_y = (left_knee.y + right_knee.y) / 2
        if knee_y < hip_y + 0.08:
            return ("Sitting", avg_visibility)

        # -- Default: Standing ------------------------------------------
        return ("Standing", avg_visibility)
    
    def _calculate_priority(self, posture_type: str) -> Tuple[str, int, str]:
        """
        Calculate priority based on posture
        
        Returns:
            (condition, priority_score, description)
        """
        priority_mapping = {
            "Fallen": (
                "Critical",
                95,
                "Person appears to have fallen - immediate assistance required"
            ),
            "Lying": (
                "Critical",
                90,
                "Person lying down - possible injury or medical emergency"
            ),
            "Waving": (
                "Warning",
                70,
                "Person signaling for help - requires attention"
            ),
            "Sitting": (
                "Warning",
                40,
                "Person sitting - may need assistance"
            ),
            "Standing": (
                "Normal",
                20,
                "Person standing - appears stable"
            ),
            "Unknown": (
                "Normal",
                30,
                "Unable to determine posture clearly"
            )
        }
        
        condition, score, description = priority_mapping.get(
            posture_type, ("Normal", 30, "Unknown posture")
        )
        
        # Ensure score is within valid range (0-100)
        score = max(0, min(100, score))
        
        return (condition, score, description)
    
    def save_analyzed_snapshot(self, image: np.ndarray, analysis: PostureAnalysis, 
                               save_dir: str, tracker_id: int) -> str:
        """
        Save snapshot with analysis overlay
        
        Args:
            image: Original image
            analysis: PostureAnalysis result
            save_dir: Directory to save images
            tracker_id: Tracker ID for filename
            
        Returns:
            Path to saved image
        """
        # Create directory if needed
        os.makedirs(save_dir, exist_ok=True)
        
        # Add overlay text
        annotated = image.copy()
        
        # Add condition label
        color_map = {
            "Critical": (0, 0, 255),  # Red
            "Warning": (0, 165, 255),  # Orange
            "Normal": (0, 255, 0)  # Green
        }
        color = color_map.get(analysis.condition, (255, 255, 255))
        
        cv2.putText(
            annotated,
            f"{analysis.condition}: {analysis.posture_type}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )
        
        cv2.putText(
            annotated,
            f"Priority: {analysis.priority_score}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )
        
        # Save image
        timestamp_str = analysis.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"person_{tracker_id}_{timestamp_str}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        cv2.imwrite(filepath, annotated)
        
        return filepath
    
    def __del__(self):
        """Clean up MediaPipe resources"""
        if hasattr(self, 'landmarker'):
            self.landmarker.close()
