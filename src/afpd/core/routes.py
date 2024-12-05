from flask import Blueprint, render_template, redirect, url_for, flash, request, json
from flask_login import login_required, current_user
from ..models.flight_procedure import FlightProcedure, ProcedureType, NavigationType, Waypoint
from .. import db

bp = Blueprint('core', __name__)

@bp.app_template_filter('format_procedure_type')
def format_procedure_type(value):
    """Format procedure type for display"""
    return value.replace('_', ' ').title()

@bp.route('/')
def index():
    """Home page with list of procedures"""
    procedures = FlightProcedure.query.all()
    return render_template('index.html', procedures=procedures)

@bp.route('/procedures/new', methods=['GET', 'POST'])
@login_required
def new_procedure():
    """Create a new procedure"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            airport_icao = request.form['airport_icao']
            procedure_type = ProcedureType[request.form['procedure_type']]
            navigation_type = NavigationType[request.form['navigation_type']]
            minimum_altitude = request.form.get('minimum_altitude')
            maximum_altitude = request.form.get('maximum_altitude')
            waypoints_json = request.form.get('waypoints_json')

            # Create new procedure
            procedure = FlightProcedure(
                name=name,
                airport_icao=airport_icao,
                procedure_type=procedure_type,
                navigation_type=navigation_type,
                minimum_altitude=minimum_altitude if minimum_altitude else None,
                maximum_altitude=maximum_altitude if maximum_altitude else None
            )

            # Add waypoints if provided
            if waypoints_json:
                waypoints_data = json.loads(waypoints_json)
                for wp_data in waypoints_data:
                    waypoint = Waypoint(
                        name=wp_data['name'],
                        latitude=wp_data['latitude'],
                        longitude=wp_data['longitude'],
                        sequence=wp_data['sequence'],
                        altitude_constraint=wp_data.get('altitude_constraint'),
                        speed_constraint=wp_data.get('speed_constraint')
                    )
                    procedure.waypoints.append(waypoint)

            # Save to database
            db.session.add(procedure)
            db.session.commit()

            flash('Procedure created successfully!', 'success')
            return redirect(url_for('core.view_procedure', id=procedure.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating procedure: {str(e)}', 'danger')
            return render_template('procedure_form.html',
                                procedure_types=ProcedureType,
                                navigation_types=NavigationType,
                                procedure=None)

    return render_template('procedure_form.html', 
                         procedure_types=ProcedureType,
                         navigation_types=NavigationType,
                         procedure=None)

@bp.route('/procedures/<int:id>')
@login_required
def view_procedure(id):
    """View a specific procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    return render_template('procedure_view.html', procedure=procedure)

@bp.route('/procedures/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_procedure(id):
    """Edit an existing procedure"""
    procedure = FlightProcedure.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Get form data
            procedure.name = request.form['name']
            procedure.airport_icao = request.form['airport_icao']
            procedure.procedure_type = ProcedureType[request.form['procedure_type']]
            procedure.navigation_type = NavigationType[request.form['navigation_type']]
            procedure.minimum_altitude = request.form.get('minimum_altitude')
            procedure.maximum_altitude = request.form.get('maximum_altitude')
            waypoints_json = request.form.get('waypoints_json')

            # Update waypoints
            if waypoints_json:
                # Remove existing waypoints
                for waypoint in procedure.waypoints:
                    db.session.delete(waypoint)
                
                # Add new waypoints
                waypoints_data = json.loads(waypoints_json)
                for wp_data in waypoints_data:
                    waypoint = Waypoint(
                        name=wp_data['name'],
                        latitude=wp_data['latitude'],
                        longitude=wp_data['longitude'],
                        sequence=wp_data['sequence'],
                        altitude_constraint=wp_data.get('altitude_constraint'),
                        speed_constraint=wp_data.get('speed_constraint')
                    )
                    procedure.waypoints.append(waypoint)

            # Save changes
            db.session.commit()
            flash('Procedure updated successfully!', 'success')
            return redirect(url_for('core.view_procedure', id=procedure.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating procedure: {str(e)}', 'danger')

    return render_template('procedure_form.html',
                         procedure_types=ProcedureType,
                         navigation_types=NavigationType,
                         procedure=procedure) 