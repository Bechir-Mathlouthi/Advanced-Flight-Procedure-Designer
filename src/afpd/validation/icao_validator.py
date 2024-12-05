from typing import List, Dict, Optional
from ..models.flight_procedure import FlightProcedure, Waypoint, ProcedureType, NavigationType

class ICAOValidator:
    """ICAO PANS-OPS validator for flight procedures"""
    
    def __init__(self):
        # Minimum obstacle clearance requirements (in feet)
        self.minimum_clearance = {
            ProcedureType.SID: 1000,
            ProcedureType.STAR: 1000,
            ProcedureType.APPROACH: {
                NavigationType.RNAV: 750,
                NavigationType.RNP: 750,
                NavigationType.ILS: 500,
                NavigationType.VOR: 1000,
                NavigationType.NDB: 1000
            }
        }
        
        # Maximum turn angle between waypoints (in degrees)
        self.max_turn_angle = {
            ProcedureType.SID: 120,
            ProcedureType.STAR: 90,
            ProcedureType.APPROACH: 90
        }
    
    def validate_procedure(self, procedure: FlightProcedure) -> Dict[str, List[str]]:
        """
        Validate a flight procedure against ICAO PANS-OPS criteria
        Returns a dictionary of validation results with any violations
        """
        violations = {
            "critical": [],
            "warnings": []
        }
        
        # Check minimum waypoint count
        if len(procedure.waypoints) < 2:
            violations["critical"].append("Procedure must have at least 2 waypoints")
            return violations
        
        # Validate waypoint sequence
        self._validate_waypoint_sequence(procedure, violations)
        
        # Validate turn angles
        self._validate_turn_angles(procedure, violations)
        
        # Validate altitude constraints
        self._validate_altitude_constraints(procedure, violations)
        
        return violations
    
    def _validate_waypoint_sequence(self, procedure: FlightProcedure, violations: Dict[str, List[str]]):
        """Validate the sequence and spacing of waypoints"""
        waypoints = procedure.waypoints
        
        for i in range(len(waypoints) - 1):
            current = waypoints[i]
            next_wp = waypoints[i + 1]
            
            # Check sequence numbers
            if current.sequence >= next_wp.sequence:
                violations["critical"].append(
                    f"Invalid waypoint sequence between {current.name} and {next_wp.name}"
                )
            
            # Check minimum distance between waypoints (2 NM for most procedures)
            distance = self._calculate_distance(current, next_wp)
            if distance < 2:
                violations["warnings"].append(
                    f"Waypoints {current.name} and {next_wp.name} are too close ({distance:.1f} NM)"
                )
    
    def _validate_turn_angles(self, procedure: FlightProcedure, violations: Dict[str, List[str]]):
        """Validate turn angles between waypoints"""
        waypoints = procedure.waypoints
        max_angle = self.max_turn_angle[procedure.procedure_type]
        
        for i in range(len(waypoints) - 2):
            angle = self._calculate_turn_angle(
                waypoints[i],
                waypoints[i + 1],
                waypoints[i + 2]
            )
            
            if angle > max_angle:
                violations["critical"].append(
                    f"Turn angle between {waypoints[i+1].name} exceeds maximum "
                    f"({angle:.1f}° > {max_angle}°)"
                )
    
    def _validate_altitude_constraints(self, procedure: FlightProcedure, violations: Dict[str, List[str]]):
        """Validate altitude constraints and profiles"""
        waypoints = procedure.waypoints
        
        for i in range(len(waypoints) - 1):
            current = waypoints[i]
            next_wp = waypoints[i + 1]
            
            if current.altitude_constraint and next_wp.altitude_constraint:
                # Check maximum climb/descent gradients (based on ICAO criteria)
                if procedure.procedure_type == ProcedureType.SID:
                    max_gradient = 8.3  # % for SID (CAT A/B aircraft)
                elif procedure.procedure_type == ProcedureType.APPROACH:
                    max_gradient = 5.2  # % for approach
                else:
                    max_gradient = 6.1  # % for STAR
                
                distance = self._calculate_distance(current, next_wp)
                altitude_change = abs(next_wp.altitude_constraint - current.altitude_constraint)
                gradient = (altitude_change / (distance * 6076)) * 100  # Convert NM to feet
                
                if gradient > max_gradient:
                    violations["critical"].append(
                        f"Gradient between {current.name} and {next_wp.name} "
                        f"exceeds maximum ({gradient:.1f}% > {max_gradient}%)"
                    )
    
    @staticmethod
    def _calculate_distance(wp1: Waypoint, wp2: Waypoint) -> float:
        """Calculate distance between waypoints in nautical miles"""
        # Simplified distance calculation - replace with proper geodesic calculation
        from math import cos, radians, sqrt
        
        lat1, lon1 = radians(wp1.latitude), radians(wp1.longitude)
        lat2, lon2 = radians(wp2.latitude), radians(wp2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return 3440 * c  # Earth radius in NM * central angle
    
    @staticmethod
    def _calculate_turn_angle(wp1: Waypoint, wp2: Waypoint, wp3: Waypoint) -> float:
        """Calculate turn angle at wp2 in degrees"""
        # Simplified angle calculation - replace with proper geodesic calculation
        from math import atan2, degrees
        
        # Convert to radians
        lat1, lon1 = radians(wp1.latitude), radians(wp1.longitude)
        lat2, lon2 = radians(wp2.latitude), radians(wp2.longitude)
        lat3, lon3 = radians(wp3.latitude), radians(wp3.longitude)
        
        # Calculate bearings
        bearing1 = atan2(
            sin(lon2-lon1) * cos(lat2),
            cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lon2-lon1)
        )
        bearing2 = atan2(
            sin(lon3-lon2) * cos(lat3),
            cos(lat2) * sin(lat3) - sin(lat2) * cos(lat3) * cos(lon3-lon2)
        )
        
        # Calculate turn angle
        angle = degrees(abs(bearing2 - bearing1))
        return min(angle, 360 - angle) 