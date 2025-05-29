"""
API endpoints for event matches.
"""

from flask import Blueprint, jsonify
from App.SDM.web.interface import SDMWebInterface
import os

# Create blueprint
events_bp = Blueprint('events', __name__)

# Initialize SDM web interface
sdm_interface = SDMWebInterface(os.getenv('SDM_SDP_STORAGE', 'App/SDM/Inputs/Skyn_Data_PROCESSED'))

@events_bp.route('/studies/<int:study_id>/events', methods=['GET'])
def get_events(study_id):
    """Get event matches for a study"""
    result = sdm_interface.get_event_matches(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(result)

@events_bp.route('/studies/<int:study_id>/events/quality', methods=['GET'])
def get_event_quality(study_id):
    """Get event quality metrics for a study"""
    result = sdm_interface.get_event_matches(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify({'quality_metrics': result['quality_metrics']}) 