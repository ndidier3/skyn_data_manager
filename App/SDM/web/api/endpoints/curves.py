"""
API endpoints for curve features.
"""

from flask import Blueprint, jsonify
from App.SDM.web.interface import SDMWebInterface
import os

# Create blueprint
curves_bp = Blueprint('curves', __name__)

# Initialize SDM web interface
sdm_interface = SDMWebInterface(os.getenv('SDM_SDP_STORAGE', 'App/SDM/Inputs/Skyn_Data_PROCESSED'))

@curves_bp.route('/studies/<int:study_id>/curves', methods=['GET'])
def get_curves(study_id):
    """Get curve features for a study"""
    result = sdm_interface.get_curve_features(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(result)

@curves_bp.route('/studies/<int:study_id>/curves/plots', methods=['GET'])
def get_curve_plots(study_id):
    """Get curve plots for a study"""
    result = sdm_interface.get_curve_features(study_id)
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify({'plots': result['plots']}) 