"""
Posture Analyzer - Analyze human posture using MediaPipe to assess urgency/condition
"""

import cv2
import numpy as np
import mediapipe as mp
from datetime import datetime
from dataclasses import dataclass
from typing import Tuple, Optional
import config  # Import configuration


@dataclass
class PostureAnalysis:
    """Result of posture analysis"""
    condition: str  # "Critical", "Warning", "Normal"
    priority_score: int  # 1-100, higher = more urgent
    description: str
    posture_type: str  # "Lying", "Sitting", "Standing", "Fallen", "Waving"
    confidence: float
    timestamp: datetime


class PostureAnalyzer:
    """Analyze human posture and condition using MediaPipe Pose"""
    
    def __init__(self):
        """Initialize MediaPipe Pose with settings from config"""
        self.mp_pose = mp.solutions.pose
        
        # Initialize MediaPipe Pose with config settings
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=config.MEDIAPIPE_MODEL_COMPLEXITY,
            enable_segmentation=False,
            smooth_landmarks=config.MEDIAPIPE_SMOOTH_LANDMARKS,
            min_detection_confidence=config.MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MEDIAPIPE_MIN_TRACKING_CONFIDENCE
        )
        
        print(f"✓ MediaPipe Pose initialized:")
        print(f"  Model Complexity: {config.MEDIAPIPE_MODEL_COMPLEXITY}")
        print(f"  Min Detection Confidence: {config.MEDIAPIPE_MIN_DETECTION_CONFIDENCE}")
        print(f"  Min Tracking Confidence: {config.MEDIAPIPE_MIN_TRACKING_CONFIDENCE}")
        
    def analyze_snapshot(self, image: np.ndarray) -> Optional[PostureAnalysis]:
        """
        Analyze a person snapshot to determine condition and priority
        
        Args:
            image: BGR image of detected person
            
        Returns:
            PostureAnalysis object or None if analysis fails
        """
        if image is None or image.size == 0:
            return None
        
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe
            results = self.pose.process(rgb_image)
            
            if not results.pose_landmarks:
                return PostureAnalysis(
                    condition="Unknown",
                    priority_score=30,
                    description="Person detected but pose unclear",
                    posture_type="Unknown",
                    confidence=0.3,
                    timestamp=datetime.now()
                )
            
            # Extract key landmarks
            landmarks = results.pose_landmarks.landmark
            
            # Analyze posture
            posture_type, confidence = self._classify_posture(landmarks, image.shape)
            
            # Calculate priority based on posture
            condition, priority_score, description = self._calculate_priority(posture_type)
            
            return PostureAnalysis(
                condition=condition,
                priority_score=priority_score,
                description=description,
                posture_type=posture_type,
                confidence=confidence,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Posture analysis error: {e}")
            return None
    
    def _classify_posture(self, landmarks, image_shape) -> Tuple[str, float]:
        """
        Classify posture from landmarks
        
        Returns:
            (posture_type, confidence)
        """
        h, w = image_shape[:2]
        
        # Get key landmark positions
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
        right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Calculate average visibility for confidence
        avg_visibility = np.mean([
            nose.visibility, left_shoulder.visibility, right_shoulder.visibility,
            left_hip.visibility, right_hip.visibility
        ])
        
        # Calculate vertical orientation (head to hip)
        head_y = nose.y
        hip_y = (left_hip.y + right_hip.y) / 2
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        
        # Calculate body angle
        torso_vertical_ratio = abs(hip_y - shoulder_y)
        
        # Check if person is waving (arms raised above shoulders)
        wrist_avg_y = (left_wrist.y + right_wrist.y) / 2
        if wrist_avg_y < shoulder_y - 0.15 and avg_visibility > 0.6:
            return ("Waving", avg_visibility)
        
        # Check if lying down (horizontal orientation)
        if torso_vertical_ratio < 0.15:
            # Lying orientation
            return ("Lying", avg_visibility)
        
        # Check if fallen (unusual angle or position)
        if head_y > hip_y:  # Head below hips = fallen
            return ("Fallen", avg_visibility)
        
        # Check if sitting (knees bent, torso upright)
        knee_y = (left_knee.y + right_knee.y) / 2
        ankle_y = (left_ankle.y + right_ankle.y) / 2
        
        if knee_y < hip_y + 0.1:  # Knees close to hip level
            return ("Sitting", avg_visibility)
        
        # Default: Standing
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
        import os
        
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
        if hasattr(self, 'pose'):
            self.pose.close()
