# 🚁 Dual Drone System - Implementation Guide

## Overview

The system now supports **dual drone operations** with automatic coordination between a surveillance drone and a rescue drone:

- **Drone 1 (Surveillance)**: Flies predefined waypoints, detects humans, analyzes their condition
- **Drone 2 (Rescue)**: Automatically receives rescue waypoints based on detected person locations and priorities

---

## ✨ New Features

### 🆕 Rescue Drone Tab

The new "Rescue Drone" tab provides complete control over the second drone:

1. **Independent Connection**
   - Separate COM port selection for Drone 2
   - Independent MAVLink connection management
   - Real-time connection status monitoring

2. **Automatic Waypoint Generation**
   - Generates rescue waypoints from Priority List
   - Sorted by urgency (Critical → Warning → Normal)
   - Each waypoint includes:
     - GPS coordinates from detection
     - Priority score
     - Condition description  
     - Person ID reference

3. **Mission Configuration**
   - Adjustable mission altitude (5-120m)
   - Optional takeoff waypoint insertion
   - Optional RTL (Return-to-Launch) at mission end

4. **Dual Drone Telemetry**
   - Live telemetry display for Drone 2:
     - Position (Lat/Lon/Alt)
     - Attitude (Pitch/Roll/Yaw)
     - Battery level
     - Flight mode
     - Armed status

5. **Live Map Visualization**
   - Shows both drones simultaneously:
     - 🔴 **Red Marker**: Drone 1 (Surveillance)
     - 🟢 **Green Marker**: Drone 2 (Rescue)
     - 🟠 **Orange Markers**: Detected persons / Rescue waypoints
   - Route line showing rescue path
   - Auto-updates every 2 seconds

6. **Mission Upload**
   - Upload rescue mission to Drone 2
   - Standard MAVLink protocol (QGC-compatible)
   - Upload confirmation and status logging

---

## 🔧 System Architecture

### Workflow Diagram

```
┌─────────────────┐
│   Drone 1       │
│ (Surveillance)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  YOLOv8 Human Detection         │
│  + MediaPipe Posture Analysis   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Priority List Generation       │
│  (Sorted by Urgency)            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Rescue Waypoint Generator      │
│  (Extract GPS Coordinates)      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Drone 2       │
│   (Rescue)      │
└─────────────────┘
```

### Data Flow

1. **Detection Phase** (Drone 1)
   ```
   Video Stream → YOLOv8 Detection → Person Bounding Box → 
   MediaPipe Posture Analysis → Condition Assessment → 
   GPS Calculation → Priority Item Created
   ```

2. **Priority Generation**
   ```
   Priority Items → Sorted by Score → 
   Display in Priority Tab
   ```

3. **Rescue Mission Creation**
   ```
   Priority List → Filter GPS Coordinates → 
   Sort by Urgency → Generate Waypoints → 
   Add Takeoff/RTL → Upload to Drone 2
   ```

4. **Execution Phase** (Drone 2)
   ```
   Receive Mission → Arm → Takeoff → 
   Visit Each Waypoint (Highest Priority First) → 
   RTL (if enabled)
   ```

---

## 📋 Tab Structure

### Updated Tab Layout:

1. **🗺️ Mission** - Drone 1 waypoint planning and upload
2. **📋 Priority** - Auto-generated priority list from detections
3. **🚁 Rescue Drone** - **NEW** Drone 2 control and rescue missions
4. **📹 Detection** - Live video, detection, posture analysis
5. **📊 Telemetry** - Detailed telemetry for Drone 1

---

## 🎯 How to Use

### Step 1: Setup First Drone (Surveillance)

1. Navigate to **Mission** tab
2. Load KML route for surveillance pattern
3. Connect Drone 1 via COM port
4. Upload surveillance mission

### Step 2: Start Detection

1. Navigate to **Detection** tab
2. Ensure Drone 1 is connected
3. Click "▶ Start Detection"
4. Video feed will show detections with posture analysis

### Step 3: Monitor Priority List

1. Navigate to **Priority** tab
2. Detected persons appear automatically
3. Items sorted by urgency (Critical first)
4. View details: condition, posture, GPS, priority score

### Step 4: Setup Second Drone (Rescue)

1. Navigate to **🚁 Rescue Drone** tab
2. Click "🔍 Scan" to find available COM ports
3. Select Drone 2's COM port
4. Click "🔌 Connect Drone 2"
5. Verify connection status turns green

### Step 5: Generate Rescue Waypoints

1. Set mission altitude (default: 30m)
2. Enable/disable Takeoff and RTL options
3. Click "🎯 Generate from Priority List"
4. System automatically:
   - Extracts GPS from priority items
   - Sorts by priority score (highest first)
   - Creates numbered waypoint list
5. Review waypoints in list (color-coded by urgency)

### Step 6: Upload Rescue Mission

1. Verify waypoint list is correct
2. Click "🚀 Upload to Drone 2"
3. Confirm upload in dialog
4. Wait for success confirmation
5. Mission is now loaded on Drone 2

### Step 7: Execute Rescue Mission

1. Arm Drone 2 (via RC transmitter or GCS)
2. Switch to AUTO mode
3. Drone 2 will:
   - Takeoff (if enabled)
   - Visit each rescue waypoint in priority order
   - Hover at each location for inspection
   - Return to launch (if enabled)

### Step 8: Monitor Both Drones

1. Watch **Live Map** in Rescue Drone tab
2. Track both drones simultaneously:
   - Red marker = Surveillance drone
   - Green marker = Rescue drone
   - Orange markers = Rescue locations
3. Monitor telemetry for Drone 2
4. Check mission status logs

---

## 🛠️ Configuration Options

### Rescue Waypoint Settings

Located in **Rescue Drone** tab:

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Mission Altitude | 30m | 5-120m | Flight altitude for all rescue waypoints |
| Add Takeoff | ✅ Enabled | - | Insert automatic takeoff command |
| Add RTL | ✅ Enabled | - | Add Return-to-Launch at mission end |

### Priority Filtering

Currently, **all priority items with GPS** are included. To filter:

Edit `ui_second_drone_tab.py`, method `generate_waypoints_from_priority()`:

```python
# Only include Critical and Warning items
for item in priority_items:
    if item.gps_coords and item.condition in ['Critical', 'Warning']:
        # Add waypoint
```

### Waypoint Visit Duration

Default: Drone hovers briefly at each waypoint. To adjust:

Edit mission parameters in MAVLink:
- `WPNAV_RADIUS` - Waypoint acceptance radius
- Modify waypoint upload to include delay commands

---

## 🔌 Hardware Setup

### Required Equipment

**For Dual Drone Operation:**

1. **Computer**
   - USB ports: Minimum 2 (one per drone)
   - Windows 10/11
   - Python 3.8+

2. **Drone 1 (Surveillance)**
   - ArduPilot-compatible autopilot
   - MAVLink telemetry (USB/Serial)
   - Camera with RTSP streaming capability
   - GPS module

3. **Drone 2 (**Rescue)**
   - ArduPilot-compatible autopilot  
   - MAVLink telemetry (USB/Serial)
   - GPS module
   - (Optional) Payload release mechanism

### Connection Diagram

```
┌──────────────────┐
│   Computer       │
│   (GCS Software) │
└─────┬──────┬─────┘
      │      │
  USB1│      │USB2
      │      │
┌─────▼──┐ ┌─▼──────┐
│ Drone 1│ │ Drone 2│
│ (Surv) │ │ (Resc) │
└────────┘ └────────┘
```

### COM Port Assignment

- **Drone 1**: Connected via Mission tab
- **Drone 2**: Connected via Rescue Drone tab
- Each drone needs separate COM port
- Use USB hub if needed (ensure sufficient power)

---

## 📊 Example Operation Scenario

### Search and Rescue Mission

**Objective**: Survey disaster area and dispatch rescue drone to victims

**Timeline:**

1. **00:00** - Launch Drone 1, start surveillance pattern
2. **02:30** - Detection system activated, video streaming
3. **05:00** - First person detected: Standing (Normal priority)
4. **07:15** - Second person detected: Waving (Warning priority, score: 70)
5. **10:00** - Third person detected: Lying down (Critical priority, score: 90)
6. **12:00** - Priority list has 3 items, sorted by urgency
7. **13:00** - Switch to Rescue Drone tab
8. **13:30** - Connect Drone 2, generate rescue waypoints
9. **14:00** - Review 3-waypoint mission (Critical person first)
10. **14:30** - Upload mission to Drone 2
11. **15:00** - Arm and launch Drone 2 in AUTO mode
12. **16:00** - Drone 2 reaches first waypoint (Critical person)
13. **20:00** - Drone 2 reaches second waypoint (Warning person)
14. **24:00** - Drone 2 reaches third waypoint (Normal person)
15. **28:00** - Drone 2 returns to launch

**Priority Queue (at 12:00):**
```
[90] Critical - Person #3 Lying @ 37.12345, -122.45678 (10:00:15)
[70] Warning - Person #2 Waving @ 37.12340, -122.45670 (07:15:30)
[20] Normal - Person #1 Standing @ 37.12350, -122.45685 (05:00:45)
```

**Rescue Mission (uploaded at 14:30):**
```
WP0: TAKEOFF @ 37.12345, -122.45678, Alt: 30m
WP1: Person #3 - Critical (Lying) @ 37.12345, -122.45678, Alt: 30m
WP2: Person #2 - Warning (Waving) @ 37.12340, -122.45670, Alt: 30m
WP3: Person #1 - Normal (Standing) @ 37.12350, -122.45685, Alt: 30m
WP4: RTL
```

---

## 🐛 Troubleshooting

### Drone 2 Won't Connect

**Symptoms**: Connection fails, red status indicator

**Solutions**:
1. Check USB cable is properly connected
2. Verify correct COM port selected (use Scan button)
3. Check no other software using the port (close Mission Planner, QGC, etc.)
4. Ensure Drone 2 is powered on
5. Try different USB port
6. Restart application

### No Waypoints Generated

**Symptoms**: "No GPS coordinates available" message

**Causes & Solutions**:

1. **No detections yet**
   - Start Detection tab first
   - Wait for persons to be detected
   - Check Priority tab has items

2. **GPS not available**
   - Ensure Drone 1 has GPS lock
   - Check telemetry shows valid coordinates
   - Verify camera geotagging is working

3. **Priority list empty**
   - Navigate to Detection tab
   - Click "Start Detection"
   - Point camera at people

### Waypoints Not Uploading

**Symptoms**: Upload fails or times out

**Solutions**:
1. Verify Drone 2 connection is active (green status)
2. Check drone is in a compatible flight mode
3. Ensure drone is armed or ready to accept mission
4. Check COM port isn't disconnected
5. Try uploading again (transient issue)
6. Reconnect Drone 2

### Map Not Updating

**Symptoms**: Static map, markers don't move

**Solutions**:
1. Check telemetry is updating (watch values)
2. Verify GPS lock on both drones
3. Refresh map (navigate away and back)
4. Check map timer is running (every 2 seconds)

### Both Drones Show Same Location

**Symptoms**: Red and green markers overlap

**Cause**: Both drones connected to same COM port or duplicate connection

**Solution**:
1. Disconnect both drones
2. Reconnect Drone 1 via Mission tab
3. Reconnect Drone 2 via Rescue Drone tab (different port)
4. Verify each has unique telemetry

---

## 🔒 Safety Considerations

### Mission Planning

✅ **DO:**
- Test missions in simulation first (SITL)
- Verify waypoint coordinates before upload
- Maintain visual line of sight with both drones
- Have RC transmitter ready for manual override
- Check battery levels frequently
- Set appropriate altitude separation if needed

❌ **DON'T:**
- Upload untested missions to real hardware
- Fly both drones too close together
- Rely solely on automatic systems
- Ignore low battery warnings
- Exceed visual line of sight
- Fly in restricted airspace

### Emergency Procedures

**If Drone Gets Stuck:**
1. Switch to LOITER mode via RC
2. Take manual control
3. Land safely
4. Don't rely on automated return

**If Connection Lost:**
1. Drone should follow failsafe (RTL)
2. Use RC transmitter as backup
3. Monitor last known position on map
4. Wait for drone to return to home

**If Wrong Waypoint:**
1. Don't panic
2. Switch to LOITER or STABILIZE mode
3. Take manual control
4. Land or RTL
5. Review and fix mission before reupload

---

## 📈 Advanced Features

### Custom Waypoint Actions

Add custom actions at rescue waypoints:

Edit `ui_second_drone_tab.py`, method `upload_mission()`:

```python
# Add waypoint with delay
mission_waypoints.append({
    'command': 'WAYPOINT',
    'lat': wp['lat'],
    'lon': wp['lon'],
    'alt': wp['alt'],
    'param1': 10  # Hold time in seconds
})

# Add camera trigger
mission_waypoints.append({
    'command': 'DO_DIGICAM_CONTROL',
    'param5': 1  # Take photo
})
```

### Payload Release

For rescue supply drops:

```python
# Add servo command at waypoint
mission_waypoints.append({
    'command': 'DO_SET_SERVO',
    'param1': 9,  # Servo channel
    'param2': 1900  # PWM value (release)
})
```

### Multi-Pass Rescue

Visit each location multiple times:

```python
# Duplicate waypoints for multiple passes
for pass_num in range(3):  # 3 passes
    for wp in self.rescue_waypoints:
        mission_waypoints.append({...})
```

---

## 🎓 Best Practices

### Efficient Operations

1. **Surveillance Pattern**
   - Use lawn-mower or grid pattern for complete coverage
   - Adjust altitude for optimal detection (20-50m)
   - Maintain consistent speed (5-10 m/s)

2. **Priority Management**
   - Review priority list before generating waypoints
   - Remove false positives if needed
   - Manually adjust priorities if necessary

3. **Rescue Timing**
   - Don't wait for entire surveillance to complete
   - Generate intermediate rescue missions
   - Launch Drone 2 as soon as critical detections occur

4. **Battery Management**
   - Monitor both drones' battery levels
   - Calculate mission duration before launch
   - Plan for sufficient reserve (20%+)
   - Have spare batteries ready

5. **Communication**
   - Use radio/phone for ground coordination
   - Mark rescue locations for ground teams
   - Document each rescue waypoint visit

---

## 📝 Future Enhancements

Possible additions:

1. **Automatic Launch Sequencing**
   - Auto-arm and launch Drone 2 when critical detection occurs

2. **Dynamic Re-routing**
   - Update Drone 2 mission mid-flight with new detections

3. **Swarm Coordination**
   - Support 3+ drones
   - Load balancing for multiple rescue targets

4. **Ground Station Integration**
   - Send waypoints to ground rescue teams
   - Export KML files for external systems

5. **Video Recording**
   - Save detection video clips
   - Store rescue operation footage

6. **Return-to-Rescue**
   - Drone 2 returns to person location after supply drop
   - Verify rescue completion

---

## ✅ System Status

### Completed Features

✅ Independent dual drone connections  
✅ Automatic waypoint generation from detections  
✅ Priority-based waypoint sorting  
✅ Live map with both drones  
✅ Separate telemetry for Drone 2  
✅ Mission upload to second drone  
✅ Configurable mission parameters  
✅ Real-time status logging  

### Ready to Deploy

The dual drone system is **fully implemented and ready for testing**!

**Next Steps:**
1. Install dependencies: `pip install -r requirements.txt`
2. Run application: `python main.py`
3. Connect both drones
4. Start surveillance mission (Drone 1)
5. Generate and upload rescue mission (Drone 2)
6. Execute coordinated operations

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review PRIORITY_TAB_IMPLEMENTATION.md
3. Check console logs for errors
4. Verify hardware connections

**System developed by**: Harigovind  
**Version**: 2.0 - Dual Drone System  
**Date**: February 2026
