"""
Create Test KML Files for Area Scan Testing

Generates sample polygon KML files for testing lawnmower coverage paths
"""

def create_rectangular_polygon_kml(filename="test_area_scan.kml", center_lat=37.7749, center_lon=-122.4194, width_m=100, height_m=80):
    """
    Create a rectangular polygon KML file
    
    Args:
        filename: Output KML filename
        center_lat: Center latitude
        center_lon: Center longitude
        width_m: Width in meters
        height_m: Height in meters
    """
    # Convert meters to approximate degrees
    lat_per_meter = 1 / 111320
    lon_per_meter = 1 / (111320 * 0.87)  # Approximate for mid-latitudes
    
    half_width = (width_m / 2) * lon_per_meter
    half_height = (height_m / 2) * lat_per_meter
    
    # Calculate corner coordinates
    corners = [
        (center_lat + half_height, center_lon - half_width),  # NW
        (center_lat + half_height, center_lon + half_width),  # NE
        (center_lat - half_height, center_lon + half_width),  # SE
        (center_lat - half_height, center_lon - half_width),  # SW
        (center_lat + half_height, center_lon - half_width),  # Close polygon
    ]
    
    # Create KML content
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Area Scan - Rectangular</name>
    <description>Test polygon for lawnmower coverage path ({width_m}m x {height_m}m)</description>
    <Placemark>
      <name>Scan Area</name>
      <description>Rectangular scan area</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
"""
    
    # Add coordinates
    for lat, lon in corners:
        kml_content += f"              {lon},{lat},0\n"
    
    kml_content += """            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    
    # Write to file
    with open(filename, 'w') as f:
        f.write(kml_content)
    
    print(f"✓ Created: {filename}")
    print(f"  Center: {center_lat}, {center_lon}")
    print(f"  Size: {width_m}m x {height_m}m")
    print(f"  Area: {(width_m * height_m) / 10000:.2f} hectares")


def create_l_shaped_polygon_kml(filename="test_area_l_shape.kml", center_lat=37.7749, center_lon=-122.4194):
    """
    Create an L-shaped polygon KML file for testing complex shapes
    
    Args:
        filename: Output KML filename
        center_lat: Center latitude
        center_lon: Center longitude
    """
    lat_per_meter = 1 / 111320
    lon_per_meter = 1 / (111320 * 0.87)
    
    # L-shape vertices (in meters, relative to center)
    vertices_m = [
        (0, 0),
        (0, 60),
        (40, 60),
        (40, 30),
        (80, 30),
        (80, 0),
        (0, 0),  # Close
    ]
    
    # Convert to lat/lon
    corners = [
        (center_lat + (y * lat_per_meter), center_lon + (x * lon_per_meter))
        for x, y in vertices_m
    ]
    
    # Create KML content
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Area Scan - L-Shape</name>
    <description>L-shaped polygon for testing complex area coverage</description>
    <Placemark>
      <name>L-Shaped Scan Area</name>
      <description>Complex shape test</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
"""
    
    for lat, lon in corners:
        kml_content += f"              {lon},{lat},0\n"
    
    kml_content += """            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    
    with open(filename, 'w') as f:
        f.write(kml_content)
    
    print(f"✓ Created: {filename}")
    print(f"  Center: {center_lat}, {center_lon}")
    print(f"  Shape: L-shaped (80m x 60m)")


def create_route_kml(filename="test_route.kml", center_lat=37.7749, center_lon=-122.4194):
    """
    Create a simple route KML file for testing route mode
    
    Args:
        filename: Output KML filename
        center_lat: Center latitude
        center_lon: Center longitude
    """
    lat_per_meter = 1 / 111320
    lon_per_meter = 1 / (111320 * 0.87)
    
    # Simple path waypoints (meters relative to center)
    waypoints_m = [
        (0, 0),
        (30, 0),
        (30, 30),
        (60, 30),
        (60, 60),
        (30, 60),
        (0, 60),
    ]
    
    # Convert to lat/lon
    waypoints = [
        (center_lat + (y * lat_per_meter), center_lon + (x * lon_per_meter))
        for x, y in waypoints_m
    ]
    
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Route</name>
    <description>Simple route for testing route mode</description>
    <Placemark>
      <name>Test Path</name>
      <LineString>
        <coordinates>
"""
    
    for lat, lon in waypoints:
        kml_content += f"          {lon},{lat},0\n"
    
    kml_content += """        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""
    
    with open(filename, 'w') as f:
        f.write(kml_content)
    
    print(f"✓ Created: {filename}")
    print(f"  Waypoints: {len(waypoints)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Creating Test KML Files for Drone GCS")
    print("=" * 60)
    print()
    
    # You can change these coordinates to your test location
    test_lat = 37.7749  # San Francisco example
    test_lon = -122.4194
    
    print("Creating test files at location:")
    print(f"  Latitude: {test_lat}")
    print(f"  Longitude: {test_lon}")
    print()
    
    # Create test files
    create_rectangular_polygon_kml("test_area_scan.kml", test_lat, test_lon, 100, 80)
    print()
    
    create_l_shaped_polygon_kml("test_area_l_shape.kml", test_lat, test_lon)
    print()
    
    create_route_kml("test_route.kml", test_lat, test_lon)
    print()
    
    print("=" * 60)
    print("Test files created successfully!")
    print("=" * 60)
    print()
    print("To test Area Scan mode:")
    print("1. Launch the GCS application")
    print("2. Go to Mission Planner tab")
    print("3. Upload test_area_scan.kml or test_area_l_shape.kml")
    print("4. Select 'Area Scan' mode")
    print("5. Adjust sweep spacing (default 10m)")
    print("6. Preview the lawnmower coverage path on the map")
    print()
    print("To test Route mode:")
    print("1. Upload test_route.kml")
    print("2. Route mode will be auto-selected")
    print("3. Preview the waypoint path")
