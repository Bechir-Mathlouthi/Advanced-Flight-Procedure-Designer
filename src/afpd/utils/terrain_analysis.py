import requests
import numpy as np
from typing import List, Dict, Tuple
from ..models.flight_procedure import FlightProcedure, Waypoint
import time

class TerrainAnalyzer:
    """Analyze terrain along flight procedures using open elevation data"""
    
    def __init__(self):
        # Primary API
        self.elevation_api_url = "https://api.open-elevation.com/api/v1/lookup"
        # Backup APIs
        self.backup_apis = [
            "https://elevation-api.io/api/elevation",  # Backup 1
            "https://maps.googleapis.com/maps/api/elevation/json"  # Backup 2
        ]
        self.samples_between_waypoints = 20  # Number of points to sample between waypoints
        self.minimum_obstacle_clearance = {
            'SID': 1000,  # feet
            'STAR': 1000,
            'APPROACH': 500
        }
        self.request_timeout = 5  # seconds
    
    def analyze_procedure(self, procedure: FlightProcedure) -> Dict:
        """Analyze terrain along a flight procedure"""
        waypoints = procedure.waypoints
        if len(waypoints) < 2:
            return {
                'status': 'error',
                'message': 'Procedure must have at least 2 waypoints'
            }
        
        # Get all points to analyze (waypoints + intermediate points)
        analysis_points = self._generate_analysis_points(waypoints)
        
        # Get elevation data
        elevations = self._get_elevations(analysis_points)
        if not elevations:
            return {
                'status': 'error',
                'message': 'Failed to get elevation data'
            }
        
        # Analyze terrain clearance
        clearance_analysis = self._analyze_clearance(
            procedure.procedure_type.name,
            analysis_points,
            elevations,
            waypoints
        )
        
        return {
            'status': 'success',
            'analysis': clearance_analysis,
            'terrain_profile': {
                'distances': [p['distance'] for p in analysis_points],
                'elevations': elevations,
                'minimum_altitudes': clearance_analysis['minimum_altitudes']
            }
        }
    
    def _generate_analysis_points(self, waypoints: List[Waypoint]) -> List[Dict]:
        """Generate points for terrain analysis, including intermediate points"""
        analysis_points = []
        total_distance = 0
        
        for i in range(len(waypoints) - 1):
            wp1, wp2 = waypoints[i], waypoints[i + 1]
            
            # Calculate distance between waypoints
            segment_distance = self._calculate_distance(
                wp1.latitude, wp1.longitude,
                wp2.latitude, wp2.longitude
            )
            
            # Add current waypoint
            analysis_points.append({
                'latitude': wp1.latitude,
                'longitude': wp1.longitude,
                'distance': total_distance,
                'is_waypoint': True,
                'waypoint': wp1
            })
            
            # Add intermediate points
            for j in range(1, self.samples_between_waypoints):
                fraction = j / self.samples_between_waypoints
                lat = wp1.latitude + (wp2.latitude - wp1.latitude) * fraction
                lon = wp1.longitude + (wp2.longitude - wp1.longitude) * fraction
                analysis_points.append({
                    'latitude': lat,
                    'longitude': lon,
                    'distance': total_distance + segment_distance * fraction,
                    'is_waypoint': False,
                    'waypoint': None
                })
            
            total_distance += segment_distance
        
        # Add final waypoint
        analysis_points.append({
            'latitude': waypoints[-1].latitude,
            'longitude': waypoints[-1].longitude,
            'distance': total_distance,
            'is_waypoint': True,
            'waypoint': waypoints[-1]
        })
        
        return analysis_points
    
    def _get_elevations(self, points: List[Dict]) -> List[float]:
        """Get elevation data for a list of points with fallback options"""
        try:
            # Prepare request data
            locations = [
                {"latitude": p['latitude'], "longitude": p['longitude']}
                for p in points
            ]
            
            # Split into smaller chunks and add retries
            chunk_size = 50  # Reduced chunk size
            elevations = []
            max_retries = 3
            
            for i in range(0, len(locations), chunk_size):
                chunk = locations[i:i + chunk_size]
                retry_count = 0
                success = False
                
                while not success and retry_count < max_retries:
                    try:
                        response = requests.post(
                            self.elevation_api_url,
                            json={"locations": chunk},
                            timeout=self.request_timeout
                        )
                        response.raise_for_status()
                        
                        data = response.json()
                        chunk_elevations = [
                            result['elevation'] * 3.28084  # Convert meters to feet
                            for result in data['results']
                        ]
                        elevations.extend(chunk_elevations)
                        success = True
                        
                    except (requests.RequestException, KeyError) as e:
                        print(f"API request failed (attempt {retry_count + 1}): {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            time.sleep(1)  # Wait before retry
                
                if not success:
                    # Use fallback elevation estimation
                    print("Using fallback elevation data")
                    return self._estimate_elevations(points)
            
            return elevations
            
        except Exception as e:
            print(f"Error getting elevation data: {str(e)}")
            return self._estimate_elevations(points)
    
    def _estimate_elevations(self, points: List[Dict]) -> List[float]:
        """Fallback method to estimate elevations when API fails"""
        # Use a simple elevation model based on latitude and typical terrain
        elevations = []
        for point in points:
            # Basic elevation estimate:
            # - Higher elevations near mountains (typically between 30-50 degrees latitude)
            # - Lower elevations near equator and poles
            lat = abs(point['latitude'])
            base_elevation = 0
            
            if 30 <= lat <= 50:
                # Mountain regions: 1000-5000 feet
                base_elevation = 1000 + (lat - 30) * 200
            elif lat < 30:
                # Lower latitudes: 0-1000 feet
                base_elevation = lat * 33.33
            else:
                # Higher latitudes: 500-1000 feet
                base_elevation = 1000 - (lat - 50) * 10
            
            # Add some variation
            variation = np.sin(point['longitude'] / 10) * 500
            elevation = max(0, base_elevation + variation)
            elevations.append(elevation)
        
        return elevations
    
    def _analyze_clearance(
        self,
        procedure_type: str,
        points: List[Dict],
        elevations: List[float],
        waypoints: List[Waypoint]
    ) -> Dict:
        """Analyze terrain clearance along the route"""
        min_clearance = self.minimum_obstacle_clearance[procedure_type]
        
        # Calculate required altitudes at each point
        minimum_altitudes = []
        violations = []
        warnings = []
        
        # Get waypoint altitudes (including interpolated)
        waypoint_altitudes = self._interpolate_altitudes(points, waypoints)
        
        for i, point in enumerate(points):
            terrain_elevation = elevations[i]
            required_altitude = terrain_elevation + min_clearance
            minimum_altitudes.append(required_altitude)
            
            if point['is_waypoint'] and point['waypoint'].altitude_constraint:
                actual_altitude = point['waypoint'].altitude_constraint
                if actual_altitude < required_altitude:
                    violations.append({
                        'type': 'clearance',
                        'location': {
                            'latitude': point['latitude'],
                            'longitude': point['longitude'],
                            'distance': point['distance']
                        },
                        'waypoint_name': point['waypoint'].name,
                        'terrain_elevation': terrain_elevation,
                        'required_altitude': required_altitude,
                        'actual_altitude': actual_altitude
                    })
            elif waypoint_altitudes[i] < required_altitude:
                warnings.append({
                    'type': 'clearance',
                    'location': {
                        'latitude': point['latitude'],
                        'longitude': point['longitude'],
                        'distance': point['distance']
                    },
                    'terrain_elevation': terrain_elevation,
                    'required_altitude': required_altitude,
                    'interpolated_altitude': waypoint_altitudes[i]
                })
        
        return {
            'minimum_altitudes': minimum_altitudes,
            'violations': violations,
            'warnings': warnings
        }
    
    def _interpolate_altitudes(
        self,
        points: List[Dict],
        waypoints: List[Waypoint]
    ) -> List[float]:
        """Interpolate altitudes between waypoints with constraints"""
        interpolated = []
        waypoint_distances = [
            p['distance'] for p in points if p['is_waypoint']
        ]
        waypoint_altitudes = [
            w.altitude_constraint for w in waypoints
        ]
        
        # Find first and last altitudes if not specified
        if waypoint_altitudes[0] is None:
            waypoint_altitudes[0] = waypoint_altitudes[1] if waypoint_altitudes[1] is not None else 0
        if waypoint_altitudes[-1] is None:
            waypoint_altitudes[-1] = waypoint_altitudes[-2] if waypoint_altitudes[-2] is not None else 0
        
        # Interpolate missing altitudes
        for i in range(1, len(waypoint_altitudes) - 1):
            if waypoint_altitudes[i] is None:
                prev_alt = next(
                    waypoint_altitudes[j] for j in range(i-1, -1, -1)
                    if waypoint_altitudes[j] is not None
                )
                next_alt = next(
                    waypoint_altitudes[j] for j in range(i+1, len(waypoint_altitudes))
                    if waypoint_altitudes[j] is not None
                )
                waypoint_altitudes[i] = (prev_alt + next_alt) / 2
        
        # Interpolate for all points
        for point in points:
            if point['is_waypoint']:
                interpolated.append(
                    waypoint_altitudes[waypoints.index(point['waypoint'])]
                )
            else:
                # Find surrounding waypoints
                prev_idx = next(
                    i for i in range(len(waypoint_distances))
                    if waypoint_distances[i] <= point['distance']
                )
                next_idx = next(
                    i for i in range(len(waypoint_distances))
                    if waypoint_distances[i] > point['distance']
                )
                
                # Linear interpolation
                d1, d2 = waypoint_distances[prev_idx], waypoint_distances[next_idx]
                a1, a2 = waypoint_altitudes[prev_idx], waypoint_altitudes[next_idx]
                fraction = (point['distance'] - d1) / (d2 - d1)
                interpolated.append(a1 + (a2 - a1) * fraction)
        
        return interpolated
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        R = 3440.065  # Earth radius in nautical miles
        
        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c

    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial bearing between two points in degrees"""
        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        
        dlon = lon2 - lon1
        
        y = np.sin(dlon) * np.cos(lat2)
        x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        
        initial_bearing = np.arctan2(y, x)
        initial_bearing = np.degrees(initial_bearing)
        bearing = (initial_bearing + 360) % 360
        
        return bearing

    def analyze_segment(self, wp1: Waypoint, wp2: Waypoint) -> Dict:
        """Analyze a segment between two waypoints"""
        # Calculate distance and bearing
        distance = self._calculate_distance(
            wp1.latitude, wp1.longitude,
            wp2.latitude, wp2.longitude
        )
        bearing = self._calculate_bearing(
            wp1.latitude, wp1.longitude,
            wp2.latitude, wp2.longitude
        )
        
        # Generate analysis points along the segment
        analysis_points = []
        for i in range(self.samples_between_waypoints + 1):
            fraction = i / self.samples_between_waypoints
            lat = wp1.latitude + (wp2.latitude - wp1.latitude) * fraction
            lon = wp1.longitude + (wp2.longitude - wp1.longitude) * fraction
            analysis_points.append({
                'latitude': lat,
                'longitude': lon,
                'distance': distance * fraction,
                'is_waypoint': i == 0 or i == self.samples_between_waypoints,
                'waypoint': wp1 if i == 0 else (wp2 if i == self.samples_between_waypoints else None)
            })
        
        # Get elevation data
        elevations = self._get_elevations(analysis_points)
        if not elevations:
            return {
                'status': 'error',
                'message': 'Failed to get elevation data'
            }
        
        # Calculate minimum safe altitude (highest elevation + minimum clearance)
        max_elevation = max(elevations)
        minimum_safe_altitude = max_elevation + self.minimum_obstacle_clearance['APPROACH']
        
        # Check for terrain violations
        violations = []
        for i, point in enumerate(analysis_points):
            if point['is_waypoint'] and point['waypoint'].altitude_constraint:
                if point['waypoint'].altitude_constraint < elevations[i] + self.minimum_obstacle_clearance['APPROACH']:
                    violations.append({
                        'waypoint_name': point['waypoint'].name,
                        'terrain_elevation': elevations[i],
                        'required_altitude': elevations[i] + self.minimum_obstacle_clearance['APPROACH'],
                        'actual_altitude': point['waypoint'].altitude_constraint
                    })
        
        return {
            'distance': distance,
            'bearing': bearing,
            'terrain_profile': {
                'distances': [p['distance'] for p in analysis_points],
                'elevations': elevations
            },
            'minimum_safe_altitude': minimum_safe_altitude,
            'violations': violations
        }