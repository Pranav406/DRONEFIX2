"""
Object Tracker - Track detected persons across frames
"""

import numpy as np
from datetime import datetime
from scipy.spatial import distance
import cv2


class PersonTracker:
    """Track a single detected person"""
    
    _next_id = 1
    
    @classmethod
    def reset_id_counter(cls):
        """Reset tracker ID counter (call at start of new mission)"""
        cls._next_id = 1
    
    def __init__(self, bbox, gps_coords=None):
        """
        Initialize tracker
        
        Args:
            bbox: (x1, y1, x2, y2) bounding box
            gps_coords: (lat, lon) GPS coordinates
        """
        self.tracker_id = PersonTracker._next_id
        PersonTracker._next_id += 1
        
        self.bbox = bbox
        self.gps_coords = gps_coords
        self.last_seen = datetime.now()
        self.frames_tracked = 1
        self.snapshot = None
        
        # Calculate centroid
        self.centroid = self._calculate_centroid(bbox)
        
    def update(self, bbox, gps_coords=None):
        """Update tracker with new detection"""
        self.bbox = bbox
        self.centroid = self._calculate_centroid(bbox)
        self.last_seen = datetime.now()
        self.frames_tracked += 1
        
        if gps_coords:
            self.gps_coords = gps_coords
    
    def _calculate_centroid(self, bbox):
        """Calculate center of bounding box"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def get_age_seconds(self):
        """Get age in seconds since last seen"""
        return (datetime.now() - self.last_seen).total_seconds()
    
    def extract_snapshot(self, frame):
        """Extract person snapshot from frame with padding for better analysis"""
        if frame is None:
            return
        
        x1, y1, x2, y2 = self.bbox
        
        # Ensure bounds are within frame
        h, w = frame.shape[:2]
        
        # Add 15% padding on each side for better posture analysis
        bw = x2 - x1
        bh = y2 - y1
        pad_x = int(bw * 0.15)
        pad_y = int(bh * 0.15)
        
        x1 = max(0, int(x1) - pad_x)
        y1 = max(0, int(y1) - pad_y)
        x2 = min(w, int(x2) + pad_x)
        y2 = min(h, int(y2) + pad_y)
        
        # Extract and store snapshot
        if y2 > y1 and x2 > x1:
            self.snapshot = frame[y1:y2, x1:x2].copy()


class MultiObjectTracker:
    """Manage multiple person trackers"""
    
    def __init__(self, max_disappeared=30, distance_threshold=50):
        """
        Initialize multi-object tracker
        
        Args:
            max_disappeared: Max frames before removing tracker
            distance_threshold: Max distance for matching (pixels)
        """
        self.trackers = []
        self.max_disappeared = max_disappeared
        self.distance_threshold = distance_threshold
        
    def update(self, detections, gps_coords_list=None, frame=None):
        """
        Update trackers with new detections
        
        Args:
            detections: List of (x1, y1, x2, y2, conf, class_id)
            gps_coords_list: List of (lat, lon) for each detection
            frame: Current frame for snapshot extraction
            
        Returns:
            List of active PersonTracker objects
        """
        # Remove old trackers
        self.trackers = [t for t in self.trackers 
                        if t.get_age_seconds() < self.max_disappeared]
        
        if not detections:
            return self.trackers
        
        # Extract bounding boxes
        new_bboxes = [det[:4] for det in detections]
        new_centroids = [self._calculate_centroid(bbox) for bbox in new_bboxes]
        
        # Match detections to existing trackers
        if self.trackers:
            tracker_centroids = [t.centroid for t in self.trackers]
            
            # Calculate distance matrix
            D = distance.cdist(np.array(tracker_centroids), 
                             np.array(new_centroids))
            
            # Match using Hungarian algorithm (simplified greedy)
            matched_trackers = set()
            matched_detections = set()
            
            # Sort by distance
            rows, cols = np.where(D < self.distance_threshold)
            indices = np.argsort(D[rows, cols])
            
            for idx in indices:
                row = rows[idx]
                col = cols[idx]
                
                if row not in matched_trackers and col not in matched_detections:
                    # Update existing tracker
                    gps = gps_coords_list[col] if gps_coords_list else None
                    self.trackers[row].update(new_bboxes[col], gps)
                    
                    # Extract snapshot
                    if frame is not None:
                        self.trackers[row].extract_snapshot(frame)
                    
                    matched_trackers.add(row)
                    matched_detections.add(col)
            
            # Create new trackers for unmatched detections
            for col in range(len(new_bboxes)):
                if col not in matched_detections:
                    gps = gps_coords_list[col] if gps_coords_list else None
                    tracker = PersonTracker(new_bboxes[col], gps)
                    
                    if frame is not None:
                        tracker.extract_snapshot(frame)
                    
                    self.trackers.append(tracker)
        
        else:
            # No existing trackers, create new ones
            for i, bbox in enumerate(new_bboxes):
                gps = gps_coords_list[i] if gps_coords_list else None
                tracker = PersonTracker(bbox, gps)
                
                if frame is not None:
                    tracker.extract_snapshot(frame)
                
                self.trackers.append(tracker)
        
        return self.trackers
    
    def _calculate_centroid(self, bbox):
        """Calculate center of bounding box"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def get_active_trackers(self):
        """Get list of active trackers"""
        return [t for t in self.trackers 
                if t.get_age_seconds() < self.max_disappeared]
    
    def clear(self):
        """Clear all trackers"""
        self.trackers = []
        PersonTracker._next_id = 1
