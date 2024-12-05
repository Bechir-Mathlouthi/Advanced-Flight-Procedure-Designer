from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..models.flight_procedure import FlightProcedure, Waypoint, ProcedureType, NavigationType
from ..validation.icao_validator import ICAOValidator
from ..utils.terrain_analysis import TerrainAnalyzer
from .. import db
import json

bp = Blueprint('api', __name__)
validator = ICAOValidator()
terrain_analyzer = TerrainAnalyzer()

@bp.route('/procedures', methods=['GET'])
@login_required
def get_procedures():
    """Get all flight procedures"""
    procedures = FlightProcedure.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'airport_icao': p.airport_icao,
        'procedure_type': p.procedure_type.value,
        'navigation_type': p.navigation_type.value,
        'waypoint_count': len(p.waypoints)
    } for p in procedures])

@bp.route('/procedures/<int:id>', methods=['GET'])
@login_required
def get_procedure(id):
    """Get a specific flight procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    return jsonify({
        'id': procedure.id,
        'name': procedure.name,
        'airport_icao': procedure.airport_icao,
        'procedure_type': procedure.procedure_type.value,
        'navigation_type': procedure.navigation_type.value,
        'minimum_altitude': procedure.minimum_altitude,
        'maximum_altitude': procedure.maximum_altitude,
        'waypoints': [{
            'id': w.id,
            'name': w.name,
            'latitude': w.latitude,
            'longitude': w.longitude,
            'sequence': w.sequence,
            'altitude_constraint': w.altitude_constraint,
            'speed_constraint': w.speed_constraint
        } for w in procedure.waypoints]
    })

@bp.route('/procedures', methods=['POST'])
@login_required
def create_procedure():
    """Create a new flight procedure"""
    data = request.get_json()
    
    # Create new procedure
    procedure = FlightProcedure(
        name=data['name'],
        airport_icao=data['airport_icao'],
        procedure_type=ProcedureType[data['procedure_type']],
        navigation_type=NavigationType[data['navigation_type']],
        minimum_altitude=data.get('minimum_altitude'),
        maximum_altitude=data.get('maximum_altitude')
    )
    
    # Add waypoints
    for wp_data in data['waypoints']:
        waypoint = Waypoint(
            name=wp_data['name'],
            latitude=wp_data['latitude'],
            longitude=wp_data['longitude'],
            sequence=wp_data['sequence'],
            altitude_constraint=wp_data.get('altitude_constraint'),
            speed_constraint=wp_data.get('speed_constraint')
        )
        procedure.waypoints.append(waypoint)
    
    # Validate procedure
    violations = validator.validate_procedure(procedure)
    if violations['critical']:
        return jsonify({
            'error': 'Validation failed',
            'violations': violations
        }), 400
    
    # Save to database
    db.session.add(procedure)
    db.session.commit()
    
    return jsonify({
        'id': procedure.id,
        'message': 'Procedure created successfully',
        'warnings': violations['warnings']
    }), 201

@bp.route('/procedures/<int:id>', methods=['PUT'])
@login_required
def update_procedure(id):
    """Update an existing flight procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    data = request.get_json()
    
    # Update procedure fields
    procedure.name = data.get('name', procedure.name)
    procedure.airport_icao = data.get('airport_icao', procedure.airport_icao)
    if 'procedure_type' in data:
        procedure.procedure_type = ProcedureType[data['procedure_type']]
    if 'navigation_type' in data:
        procedure.navigation_type = NavigationType[data['navigation_type']]
    procedure.minimum_altitude = data.get('minimum_altitude', procedure.minimum_altitude)
    procedure.maximum_altitude = data.get('maximum_altitude', procedure.maximum_altitude)
    
    # Update waypoints if provided
    if 'waypoints' in data:
        # Remove existing waypoints
        for waypoint in procedure.waypoints:
            db.session.delete(waypoint)
        
        # Add new waypoints
        for wp_data in data['waypoints']:
            waypoint = Waypoint(
                name=wp_data['name'],
                latitude=wp_data['latitude'],
                longitude=wp_data['longitude'],
                sequence=wp_data['sequence'],
                altitude_constraint=wp_data.get('altitude_constraint'),
                speed_constraint=wp_data.get('speed_constraint')
            )
            procedure.waypoints.append(waypoint)
    
    # Validate procedure
    violations = validator.validate_procedure(procedure)
    if violations['critical']:
        return jsonify({
            'error': 'Validation failed',
            'violations': violations
        }), 400
    
    # Save changes
    db.session.commit()
    
    return jsonify({
        'message': 'Procedure updated successfully',
        'warnings': violations['warnings']
    })

@bp.route('/procedures/<int:id>', methods=['DELETE'])
@login_required
def delete_procedure(id):
    """Delete a flight procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    
    # Delete associated waypoints
    for waypoint in procedure.waypoints:
        db.session.delete(waypoint)
    
    # Delete procedure
    db.session.delete(procedure)
    db.session.commit()
    
    return jsonify({'message': 'Procedure deleted successfully'})

@bp.route('/procedures/<int:id>/validate', methods=['GET'])
@login_required
def validate_procedure(id):
    """Validate an existing flight procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    violations = validator.validate_procedure(procedure)
    
    return jsonify({
        'procedure_id': id,
        'violations': violations
    })

@bp.route('/procedures/<int:id>/terrain', methods=['GET'])
@login_required
def analyze_terrain(id):
    """Analyze terrain for a specific procedure"""
    try:
        procedure = FlightProcedure.query.get_or_404(id)
        
        # Validate procedure has waypoints
        if len(procedure.waypoints) < 2:
            return jsonify({
                'error': 'Procedure must have at least 2 waypoints'
            }), 400
        
        # Perform terrain analysis
        analysis = terrain_analyzer.analyze_procedure(procedure)
        
        if analysis['status'] == 'error':
            return jsonify({
                'error': analysis['message']
            }), 400
        
        # Add estimated flag if using fallback data
        analysis['using_estimated_data'] = analysis.get('using_estimated_data', False)
        
        return jsonify(analysis)
    
    except Exception as e:
        return jsonify({
            'error': f'Error analyzing terrain: {str(e)}'
        }), 500

@bp.route('/chain', methods=['GET'])
@login_required
def chain_waypoints():
    """Chain waypoints and analyze terrain for a procedure"""
    try:
        procedure_id = request.args.get('procedure_id')
        if not procedure_id:
            return jsonify({
                'error': 'Missing procedure_id parameter'
            }), 400
        
        procedure = FlightProcedure.query.get_or_404(int(procedure_id))
        
        # Validate procedure has waypoints
        if not procedure.waypoints:
            return jsonify({
                'error': 'Procedure has no waypoints'
            }), 400
            
        if len(procedure.waypoints) < 2:
            return jsonify({
                'error': 'Procedure must have at least 2 waypoints'
            }), 400
        
        # Sort waypoints by sequence
        waypoints = sorted(procedure.waypoints, key=lambda w: w.sequence)
        
        # Calculate distances and bearings between waypoints
        segments = []
        total_distance = 0
        
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            
            try:
                # Calculate distance using terrain analyzer
                segment_analysis = terrain_analyzer.analyze_segment(wp1, wp2)
                
                if isinstance(segment_analysis, dict) and segment_analysis.get('status') == 'error':
                    return jsonify({
                        'error': segment_analysis.get('message', 'Error analyzing segment')
                    }), 400
                
                segments.append({
                    'start_waypoint': {
                        'name': wp1.name,
                        'latitude': wp1.latitude,
                        'longitude': wp1.longitude,
                        'altitude_constraint': wp1.altitude_constraint,
                        'speed_constraint': wp1.speed_constraint
                    },
                    'end_waypoint': {
                        'name': wp2.name,
                        'latitude': wp2.latitude,
                        'longitude': wp2.longitude,
                        'altitude_constraint': wp2.altitude_constraint,
                        'speed_constraint': wp2.speed_constraint
                    },
                    'distance': segment_analysis.get('distance', 0),
                    'bearing': segment_analysis.get('bearing', 0),
                    'terrain_profile': segment_analysis.get('terrain_profile', {
                        'distances': [],
                        'elevations': []
                    }),
                    'minimum_safe_altitude': segment_analysis.get('minimum_safe_altitude', 0),
                    'terrain_violations': segment_analysis.get('violations', [])
                })
                total_distance += segment_analysis.get('distance', 0)
                
            except Exception as e:
                print(f"Error analyzing segment {i}: {str(e)}")
                return jsonify({
                    'error': f'Error analyzing segment between {wp1.name} and {wp2.name}: {str(e)}'
                }), 500
        
        # Validate the entire procedure
        try:
            violations = validator.validate_procedure(procedure)
        except Exception as e:
            print(f"Error validating procedure: {str(e)}")
            violations = {'critical': [], 'warnings': []}
        
        return jsonify({
            'procedure_id': procedure.id,
            'total_distance': total_distance,
            'segments': segments,
            'violations': violations,
            'using_estimated_data': any(s.get('using_estimated_data', False) for s in segments)
        })
        
    except Exception as e:
        print(f"Error in chain_waypoints: {str(e)}")
        return jsonify({
            'error': f'Error analyzing chain: {str(e)}'
        }), 500 