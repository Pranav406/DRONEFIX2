"""
System Verification Script
Run this to verify all components are properly installed
"""

import sys
import importlib

def check_module(module_name, package_name=None):
    """Check if a Python module is installed"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name or module_name} - OK")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} - NOT FOUND")
        return False

def check_file(file_path, description):
    """Check if a file exists"""
    import os
    if os.path.exists(file_path):
        print(f"✓ {description} - OK")
        return True
    else:
        print(f"✗ {description} - NOT FOUND")
        return False

def main():
    print("=" * 60)
    print("Drone GCS - System Verification")
    print("=" * 60)
    print()
    
    # Check Python version
    print("[1] Python Version")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} - OK")
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} - REQUIRES 3.8+")
    print()
    
    # Check required modules
    print("[2] Required Python Packages")
    modules = [
        ("PyQt5", "PyQt5"),
        ("PyQt5.QtWebEngineWidgets", "PyQtWebEngine"),
        ("pymavlink", "pymavlink"),
        ("cv2", "opencv-python"),
        ("ultralytics", "ultralytics"),
        ("torch", "torch"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("serial", "pyserial"),
        ("folium", "folium"),
    ]
    
    all_ok = True
    for module, package in modules:
        if not check_module(module, package):
            all_ok = False
    print()
    
    # Check application files
    print("[3] Application Files")
    files = [
        ("main.py", "Main entry point"),
        ("ui_main_window.py", "Main window"),
        ("ui_mission_planner_tab.py", "Mission planner tab"),
        ("ui_live_detection_tab.py", "Live detection tab"),
        ("mavlink_manager.py", "MAVLink manager"),
        ("mission_upload.py", "Mission uploader"),
        ("kml_parser.py", "KML parser"),
        ("detection.py", "Detection engine"),
        ("tracker.py", "Object tracker"),
        ("config.py", "Configuration file"),
        ("requirements.txt", "Requirements file"),
    ]
    
    for file_path, description in files:
        if not check_file(file_path, description):
            all_ok = False
    print()
    
    # Check YOLOv8 model
    print("[4] YOLOv8 Model")
    if check_file("best.pt", "YOLOv8 model"):
        # Try to load model
        try:
            from ultralytics import YOLO
            model = YOLO("best.pt")
            print(f"  Model info: {len(model.names)} classes")
            
            # Check for person class
            person_found = False
            for class_id, name in model.names.items():
                if name.lower() == 'person':
                    person_found = True
                    print(f"  ✓ Person class found (ID: {class_id})")
                    break
            
            if not person_found:
                print(f"  ⚠ Warning: 'person' class not found in model")
                
        except Exception as e:
            print(f"  ✗ Model load error: {e}")
            all_ok = False
    else:
        print("  ⚠ Warning: Model not found. Detection will not work.")
        print("  Download model: python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt').save('best.pt')\"")
    print()
    
    # Check serial ports
    print("[5] Serial Port Detection")
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        if ports:
            print(f"✓ Found {len(ports)} COM port(s):")
            for port in ports:
                print(f"  - {port.device}: {port.description}")
        else:
            print("⚠ No COM ports detected")
            print("  Connect drone via USB to detect ports")
    except Exception as e:
        print(f"✗ Serial port check failed: {e}")
    print()
    
    # Summary
    print("=" * 60)
    if all_ok:
        print("✓ System verification PASSED")
        print("  You can run the application: python main.py")
    else:
        print("✗ System verification FAILED")
        print("  Please install missing dependencies:")
        print("  pip install -r requirements.txt")
    print("=" * 60)

if __name__ == "__main__":
    main()
