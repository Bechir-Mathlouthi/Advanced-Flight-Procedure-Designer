from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .. import db

class ProcedureType(enum.Enum):
    SID = "Standard Instrument Departure"
    STAR = "Standard Terminal Arrival Route"
    APPROACH = "Approach Procedure"

class NavigationType(enum.Enum):
    RNAV = "Area Navigation"
    RNP = "Required Navigation Performance"
    ILS = "Instrument Landing System"
    VOR = "VHF Omnidirectional Range"
    NDB = "Non-Directional Beacon"

class FlightProcedure(db.Model):
    __tablename__ = 'flight_procedures'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    airport_icao = Column(String(4), nullable=False)
    procedure_type = Column(Enum(ProcedureType), nullable=False)
    navigation_type = Column(Enum(NavigationType), nullable=False)
    minimum_altitude = Column(Float)  # In feet
    maximum_altitude = Column(Float)  # In feet
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    waypoints = relationship("Waypoint", back_populates="procedure", order_by="Waypoint.sequence")
    
    def __repr__(self):
        return f"<FlightProcedure {self.name} ({self.airport_icao})>"

class Waypoint(db.Model):
    __tablename__ = 'waypoints'
    
    id = Column(Integer, primary_key=True)
    procedure_id = Column(Integer, ForeignKey('flight_procedures.id'), nullable=False)
    name = Column(String(10), nullable=False)  # ICAO waypoint identifier
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)  # Order in the procedure
    altitude_constraint = Column(Float)  # In feet, nullable for no constraint
    speed_constraint = Column(Float)  # In knots, nullable for no constraint
    
    # Relationships
    procedure = relationship("FlightProcedure", back_populates="waypoints")
    
    def __repr__(self):
        return f"<Waypoint {self.name} ({self.latitude}, {self.longitude})>"

class ObstacleAssessment(db.Model):
    __tablename__ = 'obstacle_assessments'
    
    id = Column(Integer, primary_key=True)
    procedure_id = Column(Integer, ForeignKey('flight_procedures.id'), nullable=False)
    obstacle_name = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    height = Column(Float, nullable=False)  # In feet
    clearance = Column(Float, nullable=False)  # Minimum clearance in feet
    assessment_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    procedure = relationship("FlightProcedure")
    
    def __repr__(self):
        return f"<ObstacleAssessment {self.obstacle_name} - {self.clearance}ft clearance>" 