"""
KML Parser - Extract GPS coordinates from KML files
Converts KML routes to mission waypoints
Supports polygon boundaries for area scan missions
"""

import xml.etree.ElementTree as ET
import math
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union


class KMLParser:
    """Parse KML files and extract GPS coordinates"""
    
    @staticmethod
    def parse_kml(file_path):
        """
        Parse KML file and extract coordinates
        
        Args:
            file_path: Path to KML file
            
        Returns:
            (coordinates, is_polygon) - List of (lat, lon, alt) tuples and polygon flag
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Handle KML namespace
            namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Try to find namespace in root
            if root.tag.startswith('{'):
                ns = root.tag.split('}')[0] + '}'
                namespace = {'kml': ns[1:-1]}
            
            coordinates = []
            
            # Search for coordinate elements and detect if polygon
            is_polygon = False
            
            for elem in root.iter():
                if 'coordinates' in elem.tag:
                    coord_text = elem.text.strip()
                    coords = KMLParser._parse_coordinates(coord_text)
                    coordinates.extend(coords)
                    
                    # Check if parent is a Polygon
                    parent = elem
                    for _ in range(5):  # Check up to 5 levels up
                        parent = list(root.iter())  # This is simplified
                        break
                    
                # Detect polygon elements
                if 'Polygon' in elem.tag or 'polygon' in elem.tag.lower():
                    is_polygon = True
            
            if not coordinates:
                # Try without namespace
                for elem in root.iter('coordinates'):
                    coord_text = elem.text.strip()
                    coords = KMLParser._parse_coordinates(coord_text)
                    coordinates.extend(coords)
            
            # Auto-detect polygon: if first and last coordinates are same
            if len(coordinates) > 3:
                first = coordinates[0]
                last = coordinates[-1]
                if abs(first[0] - last[0]) < 0.00001 and abs(first[1] - last[1]) < 0.00001:
                    is_polygon = True
            
            return coordinates, is_polygon
            
        except Exception as e:
            raise Exception(f"Failed to parse KML: {str(e)}")
    
    @staticmethod
    def _parse_coordinates(coord_text):
        """Parse coordinate string from KML"""
        coordinates = []
        
        # Split by whitespace and newlines
        points = coord_text.replace('\n', ' ').replace('\t', ' ').split()
        
        for point in points:
            point = point.strip()
            if not point:
                continue
                
            # KML format: lon,lat,alt
            parts = point.split(',')
            
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    alt = float(parts[2]) if len(parts) == 3 else 0
                    
                    coordinates.append((lat, lon, alt))
                except ValueError:
                    continue
        
        return coordinates
    
    @staticmethod
    def smooth_waypoints(waypoints, spacing_meters=10):
        """
        Interpolate waypoints to have consistent spacing
        
        Args:
            waypoints: List of (lat, lon, alt) tuples
            spacing_meters: Desired spacing between waypoints
            
        Returns:
            Smoothed waypoint list
        """
        if len(waypoints) < 2:
            return waypoints
        
        smoothed = [waypoints[0]]
        
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i + 1]
            
            distance = KMLParser._haversine_distance(
                p1[0], p1[1], p2[0], p2[1]
            )
            
            # Calculate number of points to interpolate
            num_points = max(1, int(distance / spacing_meters))
            
            # Interpolate points
            for j in range(1, num_points + 1):
                t = j / num_points
                
                lat = p1[0] + (p2[0] - p1[0]) * t
                lon = p1[1] + (p2[1] - p1[1]) * t
                alt = p1[2] + (p2[2] - p1[2]) * t
                
                smoothed.append((lat, lon, alt))
        
        return smoothed
    
    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS points in meters"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def generate_coverage_path(polygon_coords, sweep_spacing=10, angle=0, waypoint_spacing=10):
        """
        Generate dense grid coverage path for polygon area
        
        Args:
            polygon_coords: List of (lat, lon, alt) boundary coordinates
            sweep_spacing: Distance between sweep lines in meters
            angle: Sweep direction in degrees (0=East-West, 90=North-South)
            waypoint_spacing: Distance between waypoints along each sweep line
            
        Returns:
            List of (lat, lon, alt) waypoints covering the area
        """
        if len(polygon_coords) < 3:
            return []
        
        # Create Shapely polygon (lon, lat order for Shapely)
        poly_points = [(lon, lat) for lat, lon, _ in polygon_coords]
        polygon = Polygon(poly_points)
        
        if not polygon.is_valid:
            polygon = polygon.buffer(0)  # Fix invalid polygons
        
        # Get bounding box
        minx, miny, maxx, maxy = polygon.bounds
        
        # Calculate sweep lines
        # Convert spacing from meters to degrees (approximate)
        lat_center = (miny + maxy) / 2
        meters_per_degree_lat = 111320  # meters per degree latitude
        meters_per_degree_lon = 111320 * math.cos(math.radians(lat_center))
        
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Determine sweep direction
        if abs(angle % 180) < 45 or abs(angle % 180) > 135:
            # East-West sweep
            spacing_deg = sweep_spacing / meters_per_degree_lat
            sweep_vertical = True
        else:
            # North-South sweep
            spacing_deg = sweep_spacing / meters_per_degree_lon
            sweep_vertical = False
        
        waypoints = []
        
        if sweep_vertical:
            # Sweep vertically (varying latitude)
            y = miny
            direction = 1
            
            while y <= maxy:
                # Create horizontal line across polygon at this y
                line = LineString([(minx - 0.01, y), (maxx + 0.01, y)])
                
                # Find intersections with polygon
                intersection = polygon.intersection(line)
                
                if intersection.is_empty:
                    y += spacing_deg
                    continue
                
                # Extract intersection points
                if intersection.geom_type == 'LineString':
                    coords = list(intersection.coords)
                elif intersection.geom_type == 'MultiLineString':
                    # Take longest segment
                    longest = max(intersection.geoms, key=lambda x: x.length)
                    coords = list(longest.coords)
                else:
                    y += spacing_deg
                    continue
                
                # Interpolate waypoints along the line
                if len(coords) >= 2:
                    start_lon, start_lat = coords[0]
                    end_lon, end_lat = coords[-1]
                    
                    # Calculate line length
                    line_length_m = KMLParser._haversine_distance(
                        start_lat, start_lon, end_lat, end_lon
                    )
                    
                    # Number of waypoints along this line
                    num_points = max(2, int(line_length_m / waypoint_spacing) + 1)
                    
                    # Generate interpolated waypoints
                    line_waypoints = []
                    for i in range(num_points):
                        t = i / (num_points - 1)
                        lat = start_lat + (end_lat - start_lat) * t
                        lon = start_lon + (end_lon - start_lon) * t
                        line_waypoints.append((lat, lon, polygon_coords[0][2]))
                    
                    # Add in alternating direction (boustrophedon)
                    if direction == 1:
                        waypoints.extend(line_waypoints)
                    else:
                        waypoints.extend(reversed(line_waypoints))
                
                direction *= -1
                y += spacing_deg
        
        else:
            # Sweep horizontally (varying longitude)
            x = minx
            direction = 1
            
            while x <= maxx:
                # Create vertical line across polygon at this x
                line = LineString([(x, miny - 0.01), (x, maxy + 0.01)])
                
                # Find intersections with polygon
                intersection = polygon.intersection(line)
                
                if intersection.is_empty:
                    x += spacing_deg
                    continue
                
                # Extract intersection points
                if intersection.geom_type == 'LineString':
                    coords = list(intersection.coords)
                elif intersection.geom_type == 'MultiLineString':
                    # Take longest segment
                    longest = max(intersection.geoms, key=lambda x: x.length)
                    coords = list(longest.coords)
                else:
                    x += spacing_deg
                    continue
                
                # Interpolate waypoints along the line
                if len(coords) >= 2:
                    start_lon, start_lat = coords[0]
                    end_lon, end_lat = coords[-1]
                    
                    # Calculate line length
                    line_length_m = KMLParser._haversine_distance(
                        start_lat, start_lon, end_lat, end_lon
                    )
                    
                    # Number of waypoints along this line
                    num_points = max(2, int(line_length_m / waypoint_spacing) + 1)
                    
                    # Generate interpolated waypoints
                    line_waypoints = []
                    for i in range(num_points):
                        t = i / (num_points - 1)
                        lat = start_lat + (end_lat - start_lat) * t
                        lon = start_lon + (end_lon - start_lon) * t
                        line_waypoints.append((lat, lon, polygon_coords[0][2]))
                    
                    # Add in alternating direction (boustrophedon)
                    if direction == 1:
                        waypoints.extend(line_waypoints)
                    else:
                        waypoints.extend(reversed(line_waypoints))
                
                direction *= -1
                x += spacing_deg
        
        return waypoints


class WaypointConverter:
    """Convert KML coordinates to mission waypoints"""
    
    @staticmethod
    def convert_to_waypoints(coordinates, fixed_altitude=10):
        """
        Convert KML coordinates to waypoints with fixed altitude
        
        Args:
            coordinates: List of (lat, lon, alt) from KML
            fixed_altitude: Fixed altitude in meters
            
        Returns:
            List of (lat, lon, alt) waypoints
        """
        waypoints = []
        
        for lat, lon, _ in coordinates:
            waypoints.append((lat, lon, fixed_altitude))
        
        return waypoints
    
    @staticmethod
    def get_route_stats(waypoints):
        """Calculate route statistics"""
        if len(waypoints) < 2:
            return {
                'total_distance': 0,
                'waypoint_count': len(waypoints),
                'center_lat': waypoints[0][0] if waypoints else 0,
                'center_lon': waypoints[0][1] if waypoints else 0
            }
        
        total_distance = 0
        
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i + 1]
            
            distance = KMLParser._haversine_distance(
                p1[0], p1[1], p2[0], p2[1]
            )
            total_distance += distance
        
        # Calculate center point
        lats = [wp[0] for wp in waypoints]
        lons = [wp[1] for wp in waypoints]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        return {
            'total_distance': total_distance,
            'waypoint_count': len(waypoints),
            'center_lat': center_lat,
            'center_lon': center_lon
        }
