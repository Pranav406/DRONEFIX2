"""
Mission Uploader - QGroundControl-style waypoint upload protocol
Implements standard MAVLink mission protocol for ArduPilot compatibility
"""

import time
from pymavlink import mavutil


class MissionUploader:
    """Handles mission waypoint upload using QGC protocol"""
    
    def __init__(self, mavlink_manager):
        self.manager = mavlink_manager
        self.connection = None
        
    def upload_mission(self, waypoints, add_takeoff=True, add_rtl=True):
        """
        Upload mission to drone using QGroundControl protocol
        
        Args:
            waypoints: List of (lat, lon, alt) tuples
            add_takeoff: Add takeoff command at start
            add_rtl: Add return-to-launch at end
            
        Returns:
            (success: bool, message: str)
        """
        if not self.manager.connected:
            return False, "Not connected to drone"
        
        self.connection = self.manager.connection
        
        try:
            # Build mission items
            mission_items = self._build_mission_items(waypoints, add_takeoff, add_rtl)
            
            self.manager.mission_upload_progress.emit("Clearing existing mission...")
            
            # Step 1: Clear existing mission
            if not self._clear_mission():
                return False, "Failed to clear existing mission"
            
            time.sleep(0.5)
            
            # Step 2: Send mission count
            self.manager.mission_upload_progress.emit(f"Sending mission count: {len(mission_items)} items")
            
            if not self._send_mission_count(len(mission_items)):
                return False, "Failed to send mission count"
            
            # Step 3: Send each waypoint
            for seq, item in enumerate(mission_items):
                self.manager.mission_upload_progress.emit(f"Uploading waypoint {seq + 1}/{len(mission_items)}")
                
                if not self._send_mission_item(seq, item, len(mission_items)):
                    return False, f"Failed to upload waypoint {seq}"
                
            # Step 4: Verify mission
            self.manager.mission_upload_progress.emit("Verifying mission...")
            
            time.sleep(0.5)
            
            if not self._verify_mission(len(mission_items)):
                return False, "Mission verification failed"
            
            self.manager.mission_upload_progress.emit("Mission uploaded successfully!")
            return True, f"Successfully uploaded {len(mission_items)} waypoints"
            
        except Exception as e:
            return False, f"Upload error: {str(e)}"
    
    def _build_mission_items(self, waypoints, add_takeoff, add_rtl):
        """Build mission item list from waypoints"""
        items = []
        
        # Add takeoff if requested
        if add_takeoff:
            items.append({
                'command': mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                'param1': 0,  # Pitch
                'param2': 0,  # Empty
                'param3': 0,  # Empty
                'param4': 0,  # Yaw
                'x': 0,       # Lat (0 = current position)
                'y': 0,       # Lon (0 = current position)
                'z': 10,      # Takeoff altitude
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
            })
        
        # Add waypoints
        for lat, lon, alt in waypoints:
            items.append({
                'command': mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                'param1': 0,  # Hold time
                'param2': 2,  # Acceptance radius (meters)
                'param3': 0,  # Pass through (0 = fly through)
                'param4': 0,  # Yaw
                'x': lat,
                'y': lon,
                'z': alt,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
            })
        
        # Add RTL if requested
        if add_rtl:
            items.append({
                'command': mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                'param1': 0,
                'param2': 0,
                'param3': 0,
                'param4': 0,
                'x': 0,
                'y': 0,
                'z': 0,
                'frame': mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
            })
        
        return items
    
    def _clear_mission(self):
        """Clear existing mission on drone"""
        try:
            self.connection.mav.mission_clear_all_send(
                self.connection.target_system,
                self.connection.target_component
            )
            
            # Wait for ACK
            msg = self.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            
            if msg and msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                return True
            
            return False
            
        except Exception as e:
            print(f"Clear mission error: {e}")
            return False
    
    def _send_mission_count(self, count):
        """Send mission item count to drone"""
        try:
            self.connection.mav.mission_count_send(
                self.connection.target_system,
                self.connection.target_component,
                count
            )
            
            # Wait for REQUEST
            msg = self.connection.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)
            
            return msg is not None
            
        except Exception as e:
            print(f"Send count error: {e}")
            return False
    
    def _send_mission_item(self, seq, item, total_items):
        """Send individual mission item"""
        try:
            # Determine if this is the current waypoint (first one)
            current = 1 if seq == 0 else 0
            
            self.connection.mav.mission_item_send(
                self.connection.target_system,
                self.connection.target_component,
                seq,
                item['frame'],
                item['command'],
                current,
                1,  # autocontinue
                item['param1'],
                item['param2'],
                item['param3'],
                item['param4'],
                item['x'],
                item['y'],
                item['z']
            )
            
            # Wait for next REQUEST or ACK
            if seq < total_items - 1:
                msg = self.connection.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)
            else:
                msg = self.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            
            return msg is not None
            
        except Exception as e:
            print(f"Send item error: {e}")
            return False
    
    def _verify_mission(self, expected_count):
        """Verify mission was uploaded correctly"""
        try:
            # Request mission count
            self.connection.mav.mission_request_list_send(
                self.connection.target_system,
                self.connection.target_component
            )
            
            msg = self.connection.recv_match(type='MISSION_COUNT', blocking=True, timeout=5)
            
            if msg and msg.count == expected_count:
                return True
            
            return False
            
        except Exception as e:
            print(f"Verify error: {e}")
            return False


def upload_mission_to_drone(mavlink_manager, waypoints):
    """
    Helper function to upload mission waypoints to drone
    
    Args:
        mavlink_manager: MavlinkManager instance
        waypoints: List of waypoint dictionaries with format:
                  [{'command': 'WAYPOINT'/'TAKEOFF'/'RTL', 'lat': float, 'lon': float, 'alt': float}, ...]
    
    Returns:
        bool: True if upload successful, False otherwise
    """
    if not mavlink_manager or not waypoints:
        return False
    
    # Extract waypoint coordinates and commands
    mission_waypoints = []
    add_takeoff = False
    add_rtl = False
    
    for wp in waypoints:
        cmd = wp.get('command', 'WAYPOINT')
        
        if cmd == 'TAKEOFF':
            add_takeoff = True
        elif cmd == 'RTL':
            add_rtl = True
        elif cmd == 'WAYPOINT':
            lat = wp.get('lat', 0)
            lon = wp.get('lon', 0) 
            alt = wp.get('alt', 30)
            mission_waypoints.append((lat, lon, alt))
    
    # Upload using MissionUploader
    uploader = MissionUploader(mavlink_manager)
    success, message = uploader.upload_mission(mission_waypoints, add_takeoff, add_rtl)
    
    if not success:
        print(f"Mission upload failed: {message}")
    
    return success
