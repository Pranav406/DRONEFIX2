# 🚀 Quick Start Guide

## First Time Setup (5 minutes)

### 1. Install Python
- Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
- ✅ Check "Add Python to PATH" during installation

### 2. Run Setup Script
```bash
# Double-click or run in Command Prompt:
setup.bat
```

This will:
- Create virtual environment
- Install all dependencies
- Check for YOLOv8 model

### 3. Prepare YOLOv8 Model

**Option A**: Use your trained model
- Place `best.pt` in the application folder

**Option B**: Download pre-trained model
```bash
venv\Scripts\activate
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').save('best.pt')"
```

### 4. Launch Application
```bash
# Double-click:
run_app.bat

# Or manually:
venv\Scripts\activate
python main.py
```

---

## First Flight (10 minutes)

### Step 1: Prepare Mission (Mission Planner Tab)

1. **Upload KML File**
   - Click "📁 Browse KML"
   - Select your Google Earth route file
   - Watch waypoints populate

2. **Configure Options**
   - Set altitude: `10 meters`
   - ✅ Check "Add Takeoff"
   - ✅ Check "Add RTL"
   - ✅ Check "Smooth waypoints" (optional)

3. **Preview Mission**
   - View waypoints on map
   - Verify route looks correct

### Step 2: Connect to Drone

1. **Scan Ports**
   - Click "🔍 Scan Ports"
   - Select your drone's COM port

2. **Connect**
   - Click "🔌 Connect"
   - Wait for green "Connected" status

### Step 3: Upload Mission

1. Click "🚀 Upload Mission to Drone"
2. Confirm upload
3. Wait for success message
4. Mission is now on drone!

### Step 4: Start Detection (Live Detection Tab)

1. **Switch to Detection Tab**
   - Click "📹 Live Detection & Telemetry"

2. **Start Detection**
   - Click "▶ Start Detection"
   - Video feed will appear

3. **Monitor Flight**
   - Watch live telemetry update
   - See detected persons in sidebar
   - View live map with drone position

---

## Configuration (Optional)

Edit `config.py` to customize:

```python
# Change RTSP URL
RTSP_STREAM_URL = "rtsp://YOUR_IP:8554/stream"

# Adjust detection confidence
DETECTION_CONFIDENCE = 0.6  # Higher = fewer false positives

# Change camera FOV
CAMERA_FOV_HORIZONTAL = 70.0  # Your camera's FOV
```

---

## Troubleshooting Quick Fixes

### ❌ "Module not found"
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### ❌ "No COM ports"
- Check USB cable
- Install drone USB drivers
- Restart computer

### ❌ "Model not found"
- Ensure `best.pt` is in application folder
- Run: `dir best.pt` to verify

### ❌ "Stream connection failed"
- Verify RTSP URL in `config.py`
- Test in VLC: `vlc rtsp://YOUR_URL`
- Check drone WiFi connection

---

## Keyboard Shortcuts

- `Ctrl+Q` - Exit application
- `Tab` - Switch between tabs

---

## Safety Checklist

Before every flight:

- [ ] Battery fully charged
- [ ] GPS lock acquired (14+ satellites)
- [ ] Geofence configured
- [ ] Clear flight area
- [ ] RC transmitter on and armed
- [ ] Manual override tested
- [ ] Mission waypoints verified on map
- [ ] Video stream working
- [ ] Telemetry data receiving

---

## File Locations

```
DroneSW/
├── best.pt              ← Your YOLOv8 model
├── config.py            ← Settings to edit
├── setup.bat            ← Run first time
├── run_app.bat          ← Launch app
├── main.py              ← Main application
├── requirements.txt     ← Dependencies list
└── README.md            ← Full documentation
```

---

## Support Resources

1. **Hardware Connection Issues**
   - Check ArduPilot documentation
   - Verify MAVLink parameters

2. **Detection Issues**
   - Verify model is trained for person detection
   - Check lighting conditions
   - Adjust confidence threshold

3. **GPS Accuracy**
   - Ensure good GPS lock (14+ satellites)
   - Calibrate compass if needed
   - Check GPS coordinates on map

---

## Next Steps

1. ✅ Complete first test mission
2. ✅ Verify detection accuracy
3. ✅ Test geotagging precision
4. ✅ Configure custom camera FOV
5. ✅ Train custom YOLOv8 model (optional)

---

**Need Help?**

1. Read full [README.md](README.md)
2. Check troubleshooting section
3. Review code comments
4. Test individual components

---

**Version**: 1.0  
**Platform**: Windows 10/11  
**Estimated Setup Time**: 15 minutes  

🚁 **Safe Flying!** 🚁
