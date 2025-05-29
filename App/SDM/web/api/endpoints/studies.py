"""
API endpoints for study management.
"""

from flask import Blueprint, jsonify, request
from interface import SDMWebInterface
import os

# Create blueprint
studies_bp = Blueprint('studies', __name__)

# Initialize SDM web interface
sdm_interface = SDMWebInterface(os.getenv('SDM_SDP_STORAGE', 'App/SDM/Inputs/Skyn_Data_PROCESSED'))

@studies_bp.route('/studies', methods=['GET'])
def get_studies():
    """Get list of all studies"""
    studies = sdm_interface.get_all_studies()
    return jsonify(studies)

@studies_bp.route('/studies/<int:study_id>', methods=['GET'])
def get_study(study_id):
    """Get details for a specific study"""
    study = sdm_interface.load_study(study_id)
    if not study:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(study)

@studies_bp.route('/studies', methods=['POST'])
def create_study():
    """Create a new study"""
    data = request.json
    required_fields = ['name', 'description', 'subid', 'dataset_identifier']
    
    # Validate required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            'error': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    result = sdm_interface.create_study(
        name=data['name'],
        description=data['description'],
        subid=data['subid'],
        dataset_identifier=data['dataset_identifier']
    )
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201

@studies_bp.route('/studies/<int:study_id>/process', methods=['POST'])
def process_study(study_id):
    """Process data for a study"""
    data = request.json
    options = data.get('options', {})
    
    # Get processing settings
    settings = data.get('settings', {})
    
    # Process the study with the provided settings
    result = sdm_interface.process_data(
        study_id,
        options=options,
        settings=settings
    )
    
    if not result:
        return jsonify({'error': 'Study not found'}), 404
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@studies_bp.route('/studies/<int:study_id>/status', methods=['GET'])
def get_study_status(study_id):
    """Get processing status for a study"""
    status = sdm_interface.get_study_status(study_id)
    if not status:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(status) 