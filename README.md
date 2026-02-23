# 🚁 Drone Human Detection & Mission Planner Ground Station

A professional Windows desktop Ground Control Station (GCS) built with PyQt5 for ArduPilot drones. Features KML-based mission planning, QGroundControl-compatible waypoint upload, and real-time YOLOv8 human detection with GPS geotagging.

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15-orange)

---

## ✨ Features

### 🗺️ Mission Planner Tab

- **KML Route Import**: Upload Google Earth KML files and extract GPS waypoints
- **Intelligent Waypoint Conversion**: Convert KML coordinates to mission waypoints with configurable altitude
- **Mission Options**:
  - ☑ Automatic takeoff waypoint insertion
  - ☑ Return-to-Launch (RTL) at mission end
  - ☑ Waypoint smoothing with configurable spacing
- **Serial Port Detection**: Automatic COM port scanning and drone connection
- **Interactive Map Preview**: Folium-based map showing waypoints, route lines, and home marker
- **QGC-Compatible Upload**: Standard MAVLink mission protocol for reliable waypoint upload

### 📹 Live Detection & Telemetry Tab

- **RTSP Video Feed**: Real-time video stream display from drone camera
- **YOLOv8 Human Detection**: AI-powered person detection with bounding boxes
- **GPS Geotagging**: Automatic GPS coordinate calculation for detected humans using:
  - Drone position (lat/lon/alt)
  - Camera pitch angle
  - Camera field of view (FOV)
  - Pixel-to-GPS conversion
- **Object Tracking**: Multi-object tracking with unique IDs across frames
- **Detection Sidebar**: Visual cards showing:
  - Person snapshot thumbnails
  - Tracker IDs
  - GPS coordinates
  - Timestamps
  - Frame count
- **Live Telemetry Panel**: Real-time drone data display:
  - Latitude/Longitude
  - Altitude
  - Pitch/Roll/Yaw
  - Battery percentage
  - Flight mode
  - Armed status
- **Live Map**: Interactive map with moving drone marker and detected person pins

---

## 🛠️ Installation

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.8 or higher**
- **ArduPilot-compatible drone** with MAVLink support
- **YOLOv8 model file** (`best.pt`) - trained on person detection

### Step 1: Clone or Download

```bash
cd c:\Users\prana\Downloads\DroneSW
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install PyTorch (GPU - Optional but Recommended)

For CUDA 11.8:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

For CPU only:
```bash
pip install torch torchvision
```

### Step 5: Prepare YOLOv8 Model

Place your trained YOLOv8 model file (`best.pt`) in the application directory:

```
DroneSW/
├── best.pt          ← Your YOLOv8 model here
├── main.py
├── ...
```

If you don't have a model, you can use a pre-trained COCO model:

```python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # Download nano model
model.save('best.pt')
```

---

## 🚀 Usage

### Launch Application

```bash
python main.py
```

---

## 📖 User Guide

### Tab 1: Mission Planner

#### 1. Upload KML Route

1. Click **"📁 Browse KML"**
2. Select your Google Earth `.kml` route file
3. Waypoints are automatically extracted and displayed

#### 2. Configure Mission Options

- **Waypoint Altitude**: Set fixed altitude (5-120 meters)
- **Add Takeoff**: Automatically insert takeoff command at mission start
- **Add RTL**: Automatically add Return-to-Launch at mission end
- **Smooth Waypoints**: Enable interpolation with configurable spacing (5-50 meters)

#### 3. Connect to Drone

1. Click **"🔍 Scan Ports"** to detect available COM ports
2. Select your drone's COM port from dropdown
3. Click **"🔌 Connect"**
4. Wait for connection confirmation (green status indicator)

#### 4. Upload Mission

1. Review waypoints on map preview
2. Click **"🚀 Upload Mission to Drone"**
3. Confirm upload in dialog
4. Monitor progress in status log
5. Wait for success confirmation

**Mission Protocol**: Uses standard MAVLink mission upload sequence:
- Clear existing mission (`MISSION_CLEAR_ALL`)
- Send mission count (`MISSION_COUNT`)
- Send each waypoint item (`MISSION_ITEM`)
- Verify upload (`MISSION_ACK`)

---

### Tab 2: Live Detection & Telemetry

#### 1. Start Detection

1. Ensure drone is connected (via Mission Planner tab)
2. Click **"▶ Start Detection"**
3. Video feed will appear with real-time detection

#### 2. View Live Telemetry

- **Telemetry Panel**: Shows real-time drone data updated from MAVLink
- All values update automatically during flight

#### 3. Monitor Detections

- **Video Feed**: Shows live RTSP stream with bounding boxes around detected persons
- **Detection Sidebar**: Displays cards for each tracked person with:
  - Cropped snapshot
  - Unique tracker ID
  - GPS coordinates (if available)
  - Detection timestamp
  - Frames tracked

#### 4. View Live Map

- **Drone Marker**: Red plane icon showing current drone position
- **Person Markers**: Orange person icons at detected human GPS locations
- Map auto-updates every second

#### 5. Stop Detection

Click **"⏹ Stop"** to halt video processing and detection

---

## ⚙️ Configuration

### RTSP Stream URL

Edit `ui_live_detection_tab.py` to change video source:

```python
self.rtsp_url = "rtsp://192.168.144.25:8554/main.264"  # Change this
```

### Camera FOV Settings

Edit `detection.py` to match your camera:

```python
self.camera_fov_h = 62.2  # Horizontal FOV (degrees)
self.camera_fov_v = 48.8  # Vertical FOV (degrees)
```

### Detection Confidence Threshold

Edit detection threshold in `ui_live_detection_tab.py`:

```python
detections = self.detection_engine.detect(frame, confidence_threshold=0.5)  # 0.0-1.0
```

### Serial Connection Baudrate

Default: 57600. To change, edit `mavlink_manager.py`:

```python
self.connection = mavutil.mavlink_connection(port, baud=57600)  # Change baudrate
```

---

## 📁 Project Structure

```
DroneSW/
├── main.py                      # Application entry point
├── ui_main_window.py            # Main window with tab container
├── ui_mission_planner_tab.py    # Mission planning tab UI
├── ui_live_detection_tab.py     # Live detection tab UI
├── mavlink_manager.py           # MAVLink connection & telemetry
├── mission_upload.py            # QGC-style waypoint upload
├── kml_parser.py                # KML parsing & waypoint conversion
├── detection.py                 # YOLOv8 detection & geotagging
├── tracker.py                   # Multi-object tracking
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── best.pt                      # YOLOv8 model (user-provided)
```

---

## 🔧 Troubleshooting

### Issue: "Failed to load model"

**Solution**: Ensure `best.pt` exists in the application directory and is a valid YOLOv8 model.

```bash
# Check if file exists
dir best.pt

# Test model loading
python -c "from ultralytics import YOLO; YOLO('best.pt')"
```

### Issue: "No COM ports detected"

**Solutions**:
1. Check USB cable connection to drone
2. Install drone USB drivers (e.g., FTDI, CP210x)
3. Check Device Manager for COM port recognition
4. Try different USB ports

### Issue: "Connection failed: timeout"

**Solutions**:
1. Verify drone is powered on
2. Check baudrate matches drone settings (default: 57600)
3. Ensure no other GCS software is using the COM port
4. Try restarting the drone

### Issue: "Stream connection failed"

**Solutions**:
1. Verify RTSP URL is correct
2. Check network connectivity to drone's IP
3. Test stream in VLC: `vlc rtsp://192.168.144.25:8554/main.264`
4. Ensure drone's video streaming is enabled

### Issue: "Mission upload failed"

**Solutions**:
1. Ensure stable MAVLink connection
2. Check drone is in a compatible flight mode
3. Verify waypoints are within valid GPS range
4. Try uploading again (transient communication issue)

### Issue: GPU/CUDA errors

**Solution**: Install CPU-only PyTorch:

```bash
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

---

## 🎯 Technical Details

### MAVLink Mission Protocol

Implements the standard MAVLink mission protocol used by QGroundControl:

1. **MISSION_CLEAR_ALL**: Clear existing waypoints
2. **MISSION_COUNT**: Send total waypoint count
3. **MISSION_ITEM**: Send each waypoint with:
   - Command (TAKEOFF, WAYPOINT, RTL)
   - Frame (GLOBAL_RELATIVE_ALT)
   - Parameters (lat, lon, alt, acceptance radius)
4. **MISSION_ACK**: Receive acknowledgment
5. **MISSION_REQUEST_LIST**: Verify uploaded mission

### GPS Geotagging Algorithm

Converts pixel coordinates to GPS using:

1. **Normalized Coordinates**: Convert pixel to -0.5 to 0.5 range
2. **Angle Calculation**: Apply camera FOV to get viewing angles
3. **Ground Distance**: Calculate using altitude and pitch angle
4. **GPS Offset**: Use haversine formula and bearing to compute new coordinates

Formula:
```
ground_distance = altitude / tan(pitch_angle)
new_lat = asin(sin(lat) * cos(d/R) + cos(lat) * sin(d/R) * cos(bearing))
new_lon = lon + atan2(sin(bearing) * sin(d/R) * cos(lat), cos(d/R) - sin(lat) * sin(new_lat))
```

### Tracking Algorithm

Uses **centroid-based tracking** with distance matching:

1. Calculate centroid of each detection
2. Compute distance matrix between old and new centroids
3. Match detections within distance threshold
4. Update existing trackers or create new ones
5. Remove trackers after max_disappeared frames

---

## 📝 Dependencies

- **PyQt5**: GUI framework
- **pymavlink**: MAVLink protocol implementation
- **ultralytics**: YOLOv8 detection framework
- **OpenCV**: Video processing
- **folium**: Interactive mapping
- **scipy**: Spatial distance calculations
- **numpy**: Numerical computations

---

## 🤝 Contributing

This is a professional mission-critical application. When contributing:

1. Follow PEP 8 style guidelines
2. Add docstrings to all functions
3. Test thoroughly with real hardware
4. Document any configuration changes

---

## ⚠️ Safety Notice

**IMPORTANT**: This software controls drone flight operations. Always:

- ✅ Test missions in simulation first
- ✅ Maintain visual line of sight with drone
- ✅ Follow local aviation regulations
- ✅ Have manual override ready (RC transmitter)
- ✅ Verify waypoints before upload
- ✅ Monitor battery levels continuously
- ❌ Never rely solely on software for safety

---

## 📄 License

This project is provided as-is for educational and professional use.

---

## 🐛 Known Limitations

1. **GPS Accuracy**: Geotagging accuracy depends on:
   - Drone GPS precision
   - Altitude measurement accuracy
   - Camera calibration
   - Pitch angle sensor accuracy

2. **Video Latency**: RTSP streams have inherent latency (typically 1-3 seconds)

3. **Detection Performance**: YOLOv8 performance depends on:
   - Model quality and training data
   - Hardware capabilities (CPU vs GPU)
   - Lighting conditions
   - Camera resolution

---

## 📞 Support

For issues or questions:

1. Check troubleshooting section
2. Review code comments and docstrings
3. Test components individually
4. Verify hardware connections

---

## 🎓 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           MainWindow (ui_main_window.py)        │
├─────────────────┬───────────────────────────────┤
│  Mission        │  Live Detection               │
│  Planner Tab    │  & Telemetry Tab              │
│                 │                               │
│  • KML Upload   │  • RTSP Video Stream          │
│  • Map Preview  │  • YOLOv8 Detection           │
│  • Connection   │  • Object Tracking            │
│  • Upload       │  • GPS Geotagging             │
└────────┬────────┴──────────┬────────────────────┘
         │                   │
         └───────┬───────────┘
                 │
         ┌───────▼────────┐
         │  MAVLink       │
         │  Manager       │
         │                │
         │  • Connection  │
         │  • Telemetry   │
         │  • Streaming   │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │   ArduPilot    │
         │     Drone      │
         └────────────────┘
```

---

**Version**: 1.0  
**Last Updated**: February 2026  
**Platform**: Windows 10/11  
**Python**: 3.8+

---

🚁 Happy Flying! Stay Safe! 🚁
