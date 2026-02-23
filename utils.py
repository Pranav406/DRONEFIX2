"""
Utility Functions - Helper functions for validation, conversion, and common operations
"""

import math
import glob
import os
import time
from typing import Tuple, List, Dict
import config


def is_valid_gps(lat: float, lon: float) -> bool:
    """
    Validate GPS coordinates
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        
    Returns:
        True if valid, False otherwise
    """
    return (-90 <= lat <= 90) and (-180 <= lon <= 180)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def check_battery_sufficient(telemetry: dict, min_battery: int = None) -> Tuple[bool, str]:
    """
    Check if battery is sufficient for mission
    
    Args:
        telemetry: Telemetry dict with battery percentage
        min_battery: Minimum battery percentage (default from config)
        
    Returns:
        (is_sufficient, message)
    """
    if min_battery is None:
        min_battery = config.MIN_BATTERY_PERCENT
    
    battery = telemetry.get('battery', 0)
    
    if battery < min_battery:
        return False, f"Battery too low: {battery}% (minimum: {min_battery}%)"
    
    return True, f"Battery OK: {battery}%"


def validate_altitude(altitude: float, min_alt: float = None, max_alt: float = None) -> Tuple[bool, str]:
    """
    Validate altitude is within safe limits
    
    Args:
        altitude: Altitude in meters
        min_alt: Minimum altitude (default from config)
        max_alt: Maximum altitude (default from config)
        
    Returns:
        (is_valid, message)
    """
    if min_alt is None:
        min_alt = config.MIN_ALTITUDE_M
    if max_alt is None:
        max_alt = config.MAX_ALTITUDE_M
    
    if altitude < min_alt:
        return False, f"Altitude too low: {altitude}m (minimum: {min_alt}m)"
    
    if altitude > max_alt:
        return False, f"Altitude exceeds limit: {altitude}m (maximum: {max_alt}m)"
    
    return True, "Altitude OK"


def cleanup_old_snapshots(snapshot_dir: str, max_age_days: int = None, max_count: int = None):
    """
    Remove old snapshots to prevent disk filling
    
    Args:
        snapshot_dir: Directory containing snapshots
        max_age_days: Maximum age in days (default from config)
        max_count: Maximum number of snapshots to keep (default from config)
    """
    if not os.path.exists(snapshot_dir):
        return
    
    if max_age_days is None:
        max_age_days = config.MAX_SNAPSHOT_AGE_DAYS
    if max_count is None:
        max_count = config.MAX_SNAPSHOTS
    
    pattern = os.path.join(snapshot_dir, "*.jpg")
    files = glob.glob(pattern)
    
    # Remove by age
    current_time = time.time()
    removed_by_age = 0
    for file in files:
        try:
            if (current_time - os.path.getmtime(file)) > (max_age_days * 86400):
                os.remove(file)
                removed_by_age += 1
        except Exception as e:
            print(f"Failed to remove {file}: {e}")
    
    # Remove by count
    files = glob.glob(pattern)  # Refresh list
    files = sorted(files, key=os.path.getmtime)
    removed_by_count = 0
    if len(files) > max_count:
        for file in files[:-max_count]:
            try:
                os.remove(file)
                removed_by_count += 1
            except Exception as e:
                print(f"Failed to remove {file}: {e}")
    
    if removed_by_age > 0 or removed_by_count > 0:
        print(f"Cleaned up snapshots: {removed_by_age} by age, {removed_by_count} by count")


class Geofence:
    """Geofence for validating waypoints are within allowed area"""
    
    def __init__(self, center_lat: float, center_lon: float, radius_meters: float):
        """
        Initialize geofence
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_meters: Radius in meters
        """
        self.center = (center_lat, center_lon)
        self.radius = radius_meters
    
    def is_within(self, lat: float, lon: float) -> bool:
        """
        Check if point is within geofence
        
        Args:
            lat: Point latitude
            lon: Point longitude
            
        Returns:
            True if within geofence, False otherwise
        """
        distance = haversine_distance(
            self.center[0], self.center[1], lat, lon
        )
        return distance <= self.radius
    
    def validate_waypoints(self, waypoints: List[Dict]) -> Tuple[bool, str]:
        """
        Check all waypoints are within geofence
        
        Args:
            waypoints: List of waypoint dicts with 'lat' and 'lon' keys
            
        Returns:
            (all_valid, message)
        """
        for i, wp in enumerate(waypoints):
            lat = wp.get('lat', 0)
            lon = wp.get('lon', 0)
            
            if not self.is_within(lat, lon):
                return False, f"Waypoint {i+1} outside geofence: ({lat:.6f}, {lon:.6f})"
        
        return True, "All waypoints within geofence"


def preflight_check(mavlink_manager, waypoints: List = None) -> Tuple[bool, List[Tuple[str, bool, str]]]:
    """
    Run comprehensive preflight checks
    
    Args:
        mavlink_manager: MAVLink manager instance
        waypoints: Optional list of waypoints to validate
        
    Returns:
        (all_pass, checks_list)
        checks_list: List of (check_name, passed, details)
    """
    checks = []
    
    try:
        telemetry = mavlink_manager.get_telemetry()
        
        # Battery check
        battery_ok, battery_msg = check_battery_sufficient(telemetry)
        battery = telemetry.get('battery', 0)
        checks.append(("Battery", battery_ok, battery_msg))
        
        # GPS lock check
        lat = telemetry.get('lat', 0)
        lon = telemetry.get('lon', 0)
        gps_ok = is_valid_gps(lat, lon) and lat != 0
        gps_msg = "GPS Lock OK" if gps_ok else "No GPS Fix"
        checks.append(("GPS Lock", gps_ok, gps_msg))
        
        # Connection check
        connected = mavlink_manager.connected
        conn_msg = "Connected" if connected else "Not Connected"
        checks.append(("Connection", connected, conn_msg))
        
        # Waypoint validation
        if waypoints:
            waypoint_count_ok = 1 <= len(waypoints) <= 100
            wp_msg = f"{len(waypoints)} waypoints" if waypoint_count_ok else f"Invalid count: {len(waypoints)}"
            checks.append(("Waypoints", waypoint_count_ok, wp_msg))
            
            # Altitude check
            if waypoints:
                max_alt = max(wp.get('alt', 0) for wp in waypoints)
                alt_ok, alt_msg = validate_altitude(max_alt)
                checks.append(("Max Altitude", alt_ok, f"{max_alt}m - {alt_msg}"))
        
        # Armed status check (should be disarmed before mission upload)
        armed = telemetry.get('armed', False)
        disarmed_ok = not armed
        armed_msg = "Disarmed (ready)" if disarmed_ok else "Armed (warning)"
        checks.append(("Armed State", disarmed_ok, armed_msg))
        
    except Exception as e:
        checks.append(("Preflight Check", False, f"Error: {str(e)}"))
        return False, checks
    
    # Check if all passed
    all_pass = all(check[1] for check in checks)
    
    return all_pass, checks


class PerformanceMonitor:
    """Monitor performance metrics like FPS and processing time"""
    
    def __init__(self, window_size: int = 30):
        """
        Initialize performance monitor
        
        Args:
            window_size: Number of samples to average over
        """
        self.timings = []
        self.window_size = window_size
        self.start_time = None
    
    def start(self):
        """Start timing"""
        self.start_time = time.time()
    
    def end(self):
        """End timing and record"""
        if self.start_time is None:
            return
        
        elapsed = time.time() - self.start_time
        self.timings.append(elapsed)
        
        # Keep only recent timings
        if len(self.timings) > self.window_size:
            self.timings = self.timings[-self.window_size:]
        
        self.start_time = None
    
    def get_fps(self) -> float:
        """Get average FPS"""
        if not self.timings:
            return 0.0
        avg_time = sum(self.timings) / len(self.timings)
        return 1.0 / avg_time if avg_time > 0 else 0.0
    
    def get_avg_time(self) -> float:
        """Get average processing time in seconds"""
        if not self.timings:
            return 0.0
        return sum(self.timings) / len(self.timings)
    
    def get_stats(self) -> Dict[str, float]:
        """Get all statistics"""
        return {
            'fps': self.get_fps(),
            'avg_time_ms': self.get_avg_time() * 1000,
            'min_time_ms': min(self.timings) * 1000 if self.timings else 0,
            'max_time_ms': max(self.timings) * 1000 if self.timings else 0
        }
