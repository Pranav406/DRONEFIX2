# Priority Tab with Posture Recognition - Implementation Summary

## ✅ Completed Implementation

### 1. **PostureAnalyzer Module** (`posture_analyzer.py`)
Created a comprehensive posture analysis system using MediaPipe Pose:

**Features:**
- Detects human pose landmarks in snapshots using MediaPipe
- Classifies postures into 6 types:
  - **Fallen** (head below hips) → Critical Priority (95/100)
  - **Lying** (horizontal orientation) → Critical Priority (90/100)
  - **Waving** (arms raised) → Warning Priority (70/100)
  - **Sitting** (knees bent) → Warning Priority (40/100)
  - **Standing** (upright) → Normal Priority (20/100)
  - **Unknown** (unclear pose) → Normal Priority (30/100)

- Calculates priority scores (1-100) based on urgency
- Saves analyzed snapshots with visual overlays
- Provides detailed condition descriptions

### 2. **Enhanced Priority Tab UI** (`ui_priority_tab.py`)
Complete priority management interface:

**Features:**
- Auto-add detected persons with posture analysis
- Sorted priority queue (highest urgency first)
- Color-coded items:
  - 🔴 Critical (red)
  - 🟠 Warning (orange)
  - 🟢 Normal (green)
  - 🔵 Manual (blue)
- Detailed information panel showing:
  - Condition and priority score
  - Person ID and posture type
  - GPS coordinates
  - Detection timestamp
  - Associated image path
- Manual item entry capability
- Controls: Remove, Clear All, Export to text file
- Statistics display (total, critical, warning, normal counts)
- Critical condition alerts (popup notifications)
- Toggle auto-add on/off

### 3. **Detection Integration** (`ui_live_detection_tab.py`)
Connected detection system with priority analysis:

**Features:**
- PostureAnalyzer initialization on startup
- Automatic snapshot analysis for each detected person
- Saves analyzed images to `detected_persons/` directory
- Creates PriorityItem objects with full metadata
- Sends priority items to Priority Tab automatically
- Prevents duplicate analysis (tracks analyzed IDs)
- Console logging of analysis results

### 4. **Main Window Integration** (`ui_main_window.py`)
Updated tab structure:

**Tab Order:**
1. 🗺️ Mission Planner
2. 📋 **Priority List** (NEW)
3. 📹 Live Detection
4. 📊 Telemetry

Priority tab is now created and passed to Detection tab for integration.

### 5. **Dependencies** (`requirements.txt`)
Added MediaPipe to project requirements:
```
mediapipe>=0.10.0
```

---

## 📋 Installation Steps

### Step 1: Install MediaPipe
**Important:** Close any running Python processes first to avoid file locks.

```powershell
cd DroneSW
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install mediapipe
```

**Alternative if conflicts occur:**
```powershell
# Install without dependencies first
venv\Scripts\python.exe -m pip install mediapipe --no-deps

# Then install missing dependencies individually
venv\Scripts\python.exe -m pip install absl-py flatbuffers sounddevice
```

### Step 2: Run the Application
```powershell
cd DroneSW
venv\Scripts\python.exe main.py
```

Or use the batch file:
```powershell
cd DroneSW
run_app.bat
```

---

## 🎯 How It Works

### Workflow:
1. **Detection Tab** runs YOLOv8 to detect humans in RTSP video stream
2. **Tracker** creates unique IDs and extracts snapshots for each person
3. **PostureAnalyzer** analyzes each snapshot using MediaPipe:
   - Extracts 33 body landmarks
   - Calculates body angles and orientations
   - Classifies posture type
   - Assigns urgency score
4. **Priority Tab** receives automatic priority items:
   - Displays sorted by urgency (highest first)
   - Shows GPS location if available
   - Saves analyzed images with overlays
   - Alerts on critical conditions

### Example Priority Items:
```
[95] Critical - Person #3 Fallen @ 37.12345, -122.45678 (14:23:45)
[70] Warning - Person #1 Waving @ 37.12340, -122.45670 (14:23:42)
[40] Warning - Person #2 Sitting @ 37.12350, -122.45685 (14:23:44)
[20] Normal - Person #4 Standing (14:23:46)
```

---

## 🎨 UI Features

### Priority Tab Components:

1. **Header Section:**
   - Title with icon
   - Description of automatic assessment
   - Auto-add toggle checkbox

2. **Priority Queue List:**
   - Scrollable list of all priority items
   - Color-coded by condition severity
   - Click item to view detailed info

3. **Details Panel:**
   - Shows full information for selected item
   - Displays GPS coordinates
   - Shows image file path

4. **Manual Entry:**
   - Input field for custom priority items
   - Add button for manual entries

5. **Control Buttons:**
   - 🗑️ Remove Selected
   - 🧹 Clear All
   - 📄 Export List

6. **Statistics Bar:**
   - Total item count
   - Critical/Warning/Normal breakdown

---

## 🔧 Configuration

### Adjust Priority Scoring
Edit `posture_analyzer.py`, method `_calculate_priority()`:

```python
priority_mapping = {
    "Fallen": ("Critical", 95, "description..."),
    "Lying": ("Critical", 90, "description..."),
    # Adjust scores here
}
```

### Snapshot Save Location
Edit `ui_live_detection_tab.py`, line 33:

```python
self.snapshot_dir = "detected_persons"  # Change directory
```

### Posture Classification Thresholds
Edit `posture_analyzer.py`, method `_classify_posture()`:

```python
# Example: Adjust waving detection
if wrist_avg_y < shoulder_y - 0.15:  # Change threshold value
    return ("Waving", avg_visibility)
```

---

## 🚀 Testing the System

### Test Procedure:
1. Start the application
2. Navigate to **Priority Tab** - verify UI loads correctly
3. Navigate to **Detection Tab**
4. Connect to drone via Mission Planner tab (or use mock telemetry)
5. Click "▶ Start Detection"
6. Point camera at people in various postures:
   - Standing person → Normal priority
   - Sitting person → Warning priority
   - Person waving arms → Warning priority (high)
   - Person lying down → Critical priority
7. Switch to **Priority Tab** to view auto-generated items
8. Verify:
   - Items appear automatically
   - Sorted by priority score
   - Color coded correctly
   - Details show when clicked
   - GPS coordinates display (if available)
   - Export function works

---

## 📁 New Files Created

1. **`posture_analyzer.py`** - MediaPipe pose analysis engine
2. **`ui_priority_tab.py`** - Priority list UI component
3. **`detected_persons/`** - Directory for saved snapshots (created at runtime)

## 📝 Modified Files

1. **`ui_live_detection_tab.py`** - Added posture analysis integration
2. **`ui_main_window.py`** - Added Priority tab to main window
3. **`requirements.txt`** - Added mediapipe dependency

---

## 🐛 Troubleshooting

### Issue: MediaPipe won't install
**Solution:** Close all Python processes and VS Code, then retry installation.

```powershell
# Check for running Python processes
tasklist | findstr python

# Kill if needed
taskkill /F /IM python.exe

# Retry installation
cd DroneSW
venv\Scripts\python.exe -m pip install mediapipe
```

### Issue: "Posture analyzer unavailable" message
**Cause:** MediaPipe not installed or import failed.
**Solution:** Check installation and restart application.

### Issue: Priority items not appearing
**Check:**
1. Auto-add checkbox is enabled in Priority Tab
2. Detection is running (video feed active)
3. Snapshots are being captured (check detection cards)
4. Console for any error messages

### Issue: Inaccurate posture detection
**Solutions:**
- Ensure good lighting in video feed
- Person should be fully visible in frame
- Adjust confidence thresholds in posture_analyzer.py
- Fine-tune classification logic in `_classify_posture()`

---

## 🎓 MediaPipe Pose Details

### Landmark Detection:
MediaPipe detects 33 body landmarks including:
- Face (nose, eyes, ears, mouth)
- Torso (shoulders, hips)
- Arms (elbows, wrists)
- Legs (knees, ankles)

### Posture Classification Logic:
```
Standing: Head > Hips, Torso vertical
Sitting: Knees near hip level
Lying: Torso horizontal (minimal vertical distance)
Fallen: Head below hips (inverted)
Waving: Wrists above shoulders
```

### Confidence Calculation:
Average visibility score of key landmarks (shoulders, hips, nose).

---

## 📊 Priority Scoring System

| Posture | Condition | Score | Use Case |
|---------|-----------|-------|----------|
| Fallen | Critical | 95 | Accident, medical emergency |
| Lying | Critical | 90 | Possible injury, unconscious |
| Waving | Warning | 70 | Signaling for help |
| Sitting | Warning | 40 | May need assistance |
| Standing | Normal | 20 | Person appears stable |
| Unknown | Normal | 30 | Unclear pose |

---

## 💡 Future Enhancements

Possible additions:
1. **Multi-person tracking over time** - Track condition changes
2. **Distance estimation** - Prioritize closer persons
3. **Gesture recognition** - Detect specific distress signals
4. **Audio alerts** - Sound notifications for critical conditions
5. **Mission waypoint creation** - Auto-generate rescue waypoints
6. **Photo gallery view** - Visual grid of all detections
7. **ML model training** - Custom posture classification
8. **Integration with emergency services** - Auto-dispatch alerts

---

## ✅ Ready to Use

The Priority Tab with automatic posture recognition is now fully integrated! Once MediaPipe is installed, the system will:

✓ Automatically detect human postures
✓ Assess urgency and classify conditions  
✓ Generate priority items with GPS locations
✓ Save analyzed snapshots
✓ Alert on critical conditions
✓ Maintain sortable priority queue

**Start the application and test with real or simulated video to see the automatic priority system in action!**
