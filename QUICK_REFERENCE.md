# 🚀 Quick Reference - New Features & Utilities

## Essential Imports

```python
# Core utilities
from utils import (
    is_valid_gps,
    check_battery_sufficient, 
    validate_altitude,
    cleanup_old_snapshots,
    Geofence,
    preflight_check,
    PerformanceMonitor,
    haversine_distance
)

# Flight recording
from flight_recorder import FlightRecorder, MissionHistory

# Configuration  
import config
```

---

## Configuration Constants (config.py)

```python
# Model and streams
config.YOLO_MODEL_PATH          # Now uses relative path
config.RTSP_STREAM_URL          # Video stream URL

# Limits
config.MAX_ALTITUDE_M           # 120m (regulatory limit)
config.MIN_ALTITUDE_M           # 5m (minimum safe)
config.MIN_DETECTION_ALTITUDE_M # 10m (effective detection)
config.MIN_BATTERY_PERCENT      # 30% (mission minimum)

# Storage
config.MAX_SNAPSHOTS            # 1000 max stored
config.MAX_SNAPSHOT_AGE_DAYS    # 7 days max age
```

---

## Validation Functions

### GPS Validation
```python
if is_valid_gps(lat, lon):
    print("✓ GPS coordinates valid")
else:
    print("✗ Invalid GPS")
```

### Battery Check
```python
ok, msg = check_battery_sufficient(telemetry)
if not ok:
    QMessageBox.warning(self, "Low Battery", msg)
```

### Altitude Validation
```python
ok, msg = validate_altitude(altitude)
if not ok:
    QMessageBox.warning(self, "Altitude Error", msg)
```

---

## Geofence

```python
# Create geofence (center lat/lon, radius in meters)
geofence = Geofence(37.7749, -122.4194, 5000)  # 5km radius

# Check single point
if geofence.is_within(lat, lon):
    print("✓ Within geofence")

# Validate all waypoints
ok, msg = geofence.validate_waypoints(waypoint_list)
if not ok:
    print(f"Geofence violation: {msg}")
```

---

## Preflight Checks

```python
# Run comprehensive preflight checks
all_pass, checks = preflight_check(mavlink_manager, waypoints)

# Display results
for name, passed, details in checks:
    status = "✓" if passed else "✗"
    print(f"{status} {name}: {details}")

if all_pass:
    print("✓ All preflight checks passed")
else:
    print("✗ Preflight check failed - do not fly")
```

---

## Performance Monitoring

```python
# Create monitor
perf = PerformanceMonitor(window_size=30)

# In processing loop
perf.start()
# ... do processing ...
perf.end()

# Get statistics
fps = perf.get_fps()
avg_time = perf.get_avg_time()
stats = perf.get_stats()  # Returns dict with all stats

print(f"FPS: {fps:.1f}, Avg Time: {avg_time*1000:.1f}ms")
```

---

## Flight Data Recording

```python
# Initialize recorder
recorder = FlightRecorder()
recorder.start_mission("Search and Rescue Alpha")

# In flight loop (record every frame or every N frames)
recorder.record(telemetry, detections, trackers)

# End mission
recorder.end_mission()
recorder.save()  # Saves to flight_data_YYYYMMDD_HHMMSS.json

# Load previous recording
recorder.load("flight_data_20260217_143022.json")
```

---

## Mission History

```python
# Initialize history tracker
history = MissionHistory()  # Uses mission_history.json

# Add completed mission
history.add_mission(
    mission_name="SAR Operation 2026-02-17",
    waypoints=waypoint_list,
    detection_count=5,
    notes="Found 5 people, all rescued successfully"
)

# Get recent missions
recent = history.get_recent(count=10)
for mission in recent:
    print(f"{mission['mission_name']}: {mission['detection_count']} detections")

# Export specific mission
history.export_mission(index=0, output_file="mission_export.json")

# Clear all history
history.clear_history()
```

---

## Snapshot Cleanup

```python
# Clean up old snapshots automatically
cleanup_old_snapshots(
    snapshot_dir="detected_persons",
    max_age_days=7,      # Remove older than 7 days
    max_count=1000       # Keep maximum 1000 files
)

# Can be called periodically or on app startup
```

---

## Tracker ID Management

```python
# Reset tracker IDs at start of new mission
from tracker import PersonTracker
PersonTracker.reset_id_counter()  # Resets _next_id to 1
```

---

## Thread-Safe Operations

### MAVLink Telemetry
```python
# Always use thread-safe getter
telemetry = mavlink_manager.get_telemetry()  # Returns copy with lock

# Internal telemetry updates use lock automatically
```

### Second Drone Waypoints
```python
# Waypoints list is now thread-safe
with self.waypoints_lock:
    self.rescue_waypoints.clear()
    self.rescue_waypoints.extend(new_waypoints)
```

---

## Error Handling Patterns

### Detection Processing
```python
try:
    detections = detection_engine.detect(frame)
    # ... process detections ...
except Exception as e:
    print(f"Detection error: {e}")
    # Continue gracefully, don't crash
```

### Posture Analysis
```python
try:
    analysis = posture_analyzer.analyze_snapshot(snapshot)
    if analysis is None:
        print("⚠️ Analysis failed")
        continue
    # ... use analysis ...
except Exception as e:
    print(f"❌ Analysis error: {e}")
    # Continue with next tracker
```

### File Operations
```python
try:
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(data)
    QMessageBox.information(self, "Success", "File saved")
except PermissionError:
    QMessageBox.critical(self, "Error", "Permission denied")
except Exception as e:
    QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
```

---

## Distance Calculation

```python
# Calculate distance between two GPS points
distance_m = haversine_distance(
    lat1=37.7749, lon1=-122.4194,
    lat2=37.7849, lon2=-122.4094
)
print(f"Distance: {distance_m:.1f} meters")
```

---

## Retry Logic for Connections

```python
# MAVLink connections now retry automatically
success, msg = mavlink_manager.connect(
    port="COM3",
    baudrate=57600,
    retries=3  # Will try 3 times with 2s delay
)

if success:
    print("✓ Connected")
else:
    print(f"✗ Connection failed: {msg}")
```

---

## Memory Management

```python
# Video frames are now automatically cleaned up
# In VideoProcessingThread:
try:
    ret, frame = stream.read_frame()
    # ... process frame ...
    annotated_frame = draw_detections(frame)
    # ... emit frame ...
    
    # Automatic cleanup
    del frame
    del annotated_frame
    
finally:
    if stream:
        stream.release()
```

---

## Integration Examples

### Complete Mission Workflow

```python
# 1. Preflight check
all_pass, checks = preflight_check(mavlink_manager, waypoints)
if not all_pass:
    show_preflight_dialog(checks)
    return

# 2. Start recording
recorder = FlightRecorder()
recorder.start_mission("Mission Alpha")

# 3. Execute mission
# ... fly, detect, track ...

# 4. Record data periodically
recorder.record(telemetry, detections, trackers)

# 5. End mission
recorder.end_mission()
recorder.save()

# 6. Add to history
history = MissionHistory()
history.add_mission(
    mission_name="Mission Alpha",
    waypoints=waypoints,
    detection_count=len(detections)
)

# 7. Cleanup
cleanup_old_snapshots("detected_persons")
```

### Performance-Monitored Processing

```python
# Initialize monitor
perf = PerformanceMonitor()

while running:
    perf.start()
    
    # Process frame
    ret, frame = stream.read_frame()
    detections = engine.detect(frame)
    # ... rest of processing ...
    
    perf.end()
    
    # Show stats every 30 frames
    if frame_count % 30 == 0:
        stats = perf.get_stats()
        print(f"FPS: {stats['fps']:.1f}, "
              f"Avg: {stats['avg_time_ms']:.1f}ms, "
              f"Min: {stats['min_time_ms']:.1f}ms, "
              f"Max: {stats['max_time_ms']:.1f}ms")
```

### Geofence-Protected Mission

```python
# Define operation area
geofence = Geofence(
    center_lat=mission_center_lat,
    center_lon=mission_center_lon,
    radius_meters=5000  # 5km radius
)

# Validate waypoints before upload
ok, msg = geofence.validate_waypoints(waypoints)
if not ok:
    QMessageBox.critical(self, "Geofence Violation", msg)
    return

# Upload mission
upload_mission_to_drone(mavlink_manager, waypoints)
```

---

## Debugging & Logging

```python
# Enable detailed logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("Mission started")
logger.warning("Low battery detected")
logger.error("Connection failed")
```

---

## Tips & Best Practices

1. **Always validate inputs**: Use validation functions before operations
2. **Check battery before missions**: Use preflight_check()
3. **Clean up snapshots regularly**: Call cleanup_old_snapshots() periodically
4. **Monitor performance**: Use PerformanceMonitor in production
5. **Record missions**: Enable FlightRecorder for important operations
6. **Use geofencing**: Define safe operation areas
7. **Handle errors gracefully**: Use try/except, never crash
8. **Reset tracker IDs**: Call reset_id_counter() between missions
9. **Thread safety**: Always use locks for shared data
10. **Save history**: Track missions with MissionHistory

---

## 🆘 Troubleshooting

### Import Errors
```python
# If utils not found, check:
import sys
print(sys.path)  # Should include DroneSW directory
```

### Memory Issues
```python
# Clean up periodically
cleanup_old_snapshots("detected_persons")

# Check performance
perf = PerformanceMonitor()
stats = perf.get_stats()
print(f"Processing time: {stats['avg_time_ms']:.1f}ms")
```

### Connection Failures
```python
# Check retry settings
success, msg = mavlink_manager.connect(
    port="COM3",
    retries=5  # Increase retries
)
```

---

**Quick Reference Version**: 2.0  
**Last Updated**: February 17, 2026  
**Status**: ✅ Production Ready
