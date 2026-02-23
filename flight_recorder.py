"""
Flight Data Recorder - Record flight data for analysis and replay
"""

import json
import time
from datetime import datetime
from typing import Dict, List


class FlightRecorder:
    """Record flight data for later analysis"""
    
    def __init__(self, filename: str = None):
        """
        Initialize flight recorder
        
        Args:
            filename: Output filename (default: auto-generated from timestamp)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flight_data_{timestamp}.json"
        
        self.filename = filename
        self.data = []
        self.mission_start = None
        self.mission_metadata = {
            'start_time': None,
            'end_time': None,
            'total_detections': 0,
            'waypoints_visited': 0
        }
    
    def start_mission(self, mission_name: str = "Unnamed Mission"):
        """Start recording a mission"""
        self.mission_start = time.time()
        self.mission_metadata = {
            'mission_name': mission_name,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'total_detections': 0,
            'waypoints_visited': 0
        }
        self.data = []
        print(f"[Recorder] Started recording: {mission_name}")
    
    def record(self, telemetry: Dict, detections: List, trackers: List = None):
        """
        Record a data point
        
        Args:
            telemetry: Telemetry dict from MAVLink
            detections: List of detections
            trackers: Optional list of trackers
        """
        if self.mission_start is None:
            return
        
        timestamp = time.time()
        elapsed = timestamp - self.mission_start
        
        data_point = {
            'timestamp': timestamp,
            'elapsed_seconds': elapsed,
            'datetime': datetime.now().isoformat(),
            'telemetry': telemetry.copy(),
            'detection_count': len(detections),
            'tracker_count': len(trackers) if trackers else 0
        }
        
        self.data.append(data_point)
        self.mission_metadata['total_detections'] += len(detections)
    
    def end_mission(self):
        """End mission recording"""
        if self.mission_start is None:
            return
        
        self.mission_metadata['end_time'] = datetime.now().isoformat()
        self.mission_metadata['duration_seconds'] = time.time() - self.mission_start
        self.mission_metadata['data_points'] = len(self.data)
        
        print(f"[Recorder] Mission ended: {len(self.data)} data points recorded")
    
    def save(self, filename: str = None):
        """
        Save recorded data to file
        
        Args:
            filename: Output filename (uses default if None)
        """
        if filename:
            self.filename = filename
        
        output = {
            'metadata': self.mission_metadata,
            'data': self.data
        }
        
        try:
            with open(self.filename, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"✓ Flight data saved: {self.filename}")
            return True
        except Exception as e:
            print(f"✗ Failed to save flight data: {e}")
            return False
    
    def load(self, filename: str):
        """
        Load previously recorded data
        
        Args:
            filename: Input filename
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.mission_metadata = data.get('metadata', {})
            self.data = data.get('data', [])
            
            print(f"✓ Flight data loaded: {filename}")
            print(f"  Mission: {self.mission_metadata.get('mission_name', 'Unknown')}")
            print(f"  Duration: {self.mission_metadata.get('duration_seconds', 0):.1f}s")
            print(f"  Data points: {len(self.data)}")
            
            return True
        except Exception as e:
            print(f"✗ Failed to load flight data: {e}")
            return False


class MissionHistory:
    """Track mission history for later review"""
    
    def __init__(self, history_file: str = "mission_history.json"):
        """
        Initialize mission history
        
        Args:
            history_file: JSON file storing mission history
        """
        self.history_file = history_file
        self.history = []
        self.load_history()
    
    def load_history(self):
        """Load existing mission history from file"""
        try:
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
            print(f"✓ Loaded {len(self.history)} missions from history")
        except FileNotFoundError:
            self.history = []
            print(f"No existing history found, starting fresh")
        except Exception as e:
            print(f"Failed to load history: {e}")
            self.history = []
    
    def add_mission(self, mission_name: str, waypoints: List[Dict], 
                    detection_count: int = 0, notes: str = ""):
        """
        Add a mission to history
        
        Args:
            mission_name: Name or description of mission
            waypoints: List of waypoint dicts
            detection_count: Number of detections made
            notes: Optional notes about the mission
        """
        mission = {
            'mission_name': mission_name,
            'timestamp': datetime.now().isoformat(),
            'waypoint_count': len(waypoints),
            'waypoints': waypoints,
            'detection_count': detection_count,
            'notes': notes
        }
        
        self.history.append(mission)
        self.save_history()
        
        print(f"✓ Mission added to history: {mission_name}")
    
    def save_history(self):
        """Save mission history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save history: {e}")
            return False
    
    def get_recent(self, count: int = 10) -> List[Dict]:
        """
        Get recent missions
        
        Args:
            count: Number of recent missions to return
            
        Returns:
            List of mission dicts
        """
        return self.history[-count:] if len(self.history) > count else self.history
    
    def clear_history(self):
        """Clear all mission history"""
        self.history = []
        self.save_history()
        print("Mission history cleared")
    
    def export_mission(self, index: int, output_file: str):
        """
        Export a specific mission to separate file
        
        Args:
            index: Index of mission in history
            output_file: Output filename
        """
        if 0 <= index < len(self.history):
            mission = self.history[index]
            try:
                with open(output_file, 'w') as f:
                    json.dump(mission, f, indent=2)
                print(f"✓ Mission exported: {output_file}")
                return True
            except Exception as e:
                print(f"✗ Export failed: {e}")
                return False
        else:
            print(f"✗ Invalid mission index: {index}")
            return False
