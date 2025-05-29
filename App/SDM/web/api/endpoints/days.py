"""
API endpoints for day features.
"""

from flask import Blueprint, jsonify
from App.SDM.web.interface import SDMWebInterface
import os

# Create blueprint
days_bp = Blueprint('days', __name__)

# Initialize SDM web interface
sdm_interface = SDMWebInterface(os.getenv('SDM_SDP_STORAGE', 'App/SDM/Inputs/Skyn_Data_PROCESSED'))

@days_bp.route('/studies/<int:study_id>/days', methods=['GET'])
def get_days(study_id):
    """Get day features for a study"""
    result = sdm_interface.get_day_features(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(result)

@days_bp.route('/studies/<int:study_id>/days/plots', methods=['GET'])
def get_day_plots(study_id):
    """Get day plots for a study"""
    result = sdm_interface.get_day_features(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify({'plots': result['plots']}) 