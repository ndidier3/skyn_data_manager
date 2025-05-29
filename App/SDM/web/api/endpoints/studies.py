"""
API endpoints for study management.
"""

from flask import Blueprint, jsonify, request
from interface import SDMWebInterface
from App.SDM.database.connection import db
from App.SDM.database.schema import CREATE_TABLES
import os
import psycopg2

# Create blueprint
studies_bp = Blueprint('studies', __name__)

# Initialize SDM web interface
sdm_interface = SDMWebInterface(os.getenv('SDM_SDP_STORAGE', 'App/SDM/Inputs/Skyn_Data_PROCESSED'))

def init_db():
    """Initialize the database schema"""
    try:
        # Execute the CREATE TABLE statements
        with db.get_cursor() as cursor:
            cursor.execute(CREATE_TABLES)
        print("Database schema initialized successfully")
    except Exception as e:
        print(f"Error initializing database schema: {str(e)}")
        raise

# Initialize database when the blueprint is created
init_db()

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
    try:
        data = request.json
        print("Received data:", data)  # Debug log
        
        required_fields = ['name', 'description', 'subid', 'study_id']
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # First check if study already exists
        check_query = """
            SELECT s.id, s.is_registered, i.id as instance_id
            FROM studies s
            LEFT JOIN sdm_instances i ON s.id = i.study_id AND i.subid = %s
            WHERE s.study_id = %s
        """
        try:
            existing_study = db.execute_single(check_query, (data['subid'], data['study_id']))
            if existing_study:
                if existing_study['is_registered']:
                    return jsonify({
                        'error': f'Study with ID {data["study_id"]} already exists and is registered'
                    }), 400
                # If study exists but isn't registered, we'll update it
                study_id = existing_study['id']
                instance_id = existing_study['instance_id']
        except Exception as e:
            print(f"Error checking existing study: {str(e)}")  # Debug log
            return jsonify({
                'error': 'Database error while checking existing study',
                'details': str(e)
            }), 500
        
        # Create or update the study
        if 'study_id' in locals():
            # Update existing study
            update_query = """
                UPDATE studies 
                SET name = %s, description = %s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
            """
            try:
                result = db.execute_single(update_query, (
                    data['name'],
                    data['description'],
                    study_id
                ))
            except Exception as e:
                print(f"Error updating study: {str(e)}")  # Debug log
                return jsonify({
                    'error': 'Database error while updating study',
                    'details': str(e)
                }), 500
        else:
            # Create new study
            create_query = """
                INSERT INTO studies (name, description, study_id)
                VALUES (%s, %s, %s)
                RETURNING id
            """
            try:
                result = db.execute_single(create_query, (
                    data['name'],
                    data['description'],
                    data['study_id']
                ))
            except Exception as e:
                print(f"Error creating study: {str(e)}")  # Debug log
                return jsonify({
                    'error': 'Database error while creating study',
                    'details': str(e)
                }), 500
        
        if not result:
            return jsonify({
                'error': 'Failed to create/update study'
            }), 500
        
        # Create or update the SDM instance
        if 'instance_id' in locals() and instance_id:
            # Update existing instance
            instance_query = """
                UPDATE sdm_instances 
                SET sdp_file_path = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
            """
            try:
                instance_result = db.execute_single(instance_query, (
                    f"studies/{data['study_id']}/{data['subid']}.sdp",
                    instance_id
                ))
            except Exception as e:
                print(f"Error updating SDM instance: {str(e)}")  # Debug log
                return jsonify({
                    'error': 'Database error while updating SDM instance',
                    'details': str(e)
                }), 500
        else:
            # Create new instance
            instance_query = """
                INSERT INTO sdm_instances (study_id, subid, sdp_file_path)
                VALUES (%s, %s, %s)
                RETURNING id
            """
            try:
                instance_result = db.execute_single(instance_query, (
                    result['id'],
                    data['subid'],
                    f"studies/{data['study_id']}/{data['subid']}.sdp"
                ))
            except Exception as e:
                print(f"Error creating SDM instance: {str(e)}")  # Debug log
                return jsonify({
                    'error': 'Database error while creating SDM instance',
                    'details': str(e)
                }), 500
        
        if not instance_result:
            return jsonify({
                'error': 'Failed to create/update SDM instance'
            }), 500
        
        return jsonify({
            'message': 'Study created/updated successfully',
            'study_id': data['study_id'],
            'instance_id': instance_result['id']
        }), 201
        
    except Exception as e:
        print(f"Unexpected error in create_study: {str(e)}")  # Debug log
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@studies_bp.route('/studies/<study_id>/process', methods=['POST'])
def process_study(study_id):
    """Process data for a study"""
    try:
        data = request.json
        options = data.get('options', {})
        settings = data.get('settings', {})
        
        print(f"Processing study with ID: {study_id}")  # Debug log
        
        # Get the study and instance using either string study_id or numeric id
        study_query = """
            SELECT s.id, s.study_id, s.is_registered, i.id as instance_id, i.processing_status
            FROM studies s
            JOIN sdm_instances i ON s.id = i.study_id
            WHERE s.id = %s OR s.study_id = %s
        """
        try:
            study_info = db.execute_single(study_query, (study_id, study_id))
            if not study_info:
                print(f"No study found for ID: {study_id}")  # Debug log
                return jsonify({'error': 'Study not found'}), 404
            print(f"Found study: {study_info}")  # Debug log
        except Exception as e:
            print(f"Error getting study info: {str(e)}")  # Debug log
            return jsonify({
                'error': 'Database error while getting study info',
                'details': str(e)
            }), 500
        
        # Process the study with the provided settings
        print(f"Processing study with numeric ID: {study_info['id']}")  # Debug log
        result = sdm_interface.process_data(
            study_info['id'],  # Use the numeric ID from the database
            options=options,
            settings=settings
        )
        
        if not result:
            print(f"No result returned for study ID: {study_info['id']}")  # Debug log
            return jsonify({'error': 'Study not found'}), 404
        if 'error' in result:
            print(f"Error in processing result: {result['error']}")  # Debug log
            return jsonify(result), 400
            
        # If processing was successful, update the study registration status
        if result.get('status', {}).get('gaps_and_non_wear') == 'success':
            print(f"Updating registration status for study ID: {study_info['id']}")  # Debug log
            update_query = """
                UPDATE studies 
                SET is_registered = TRUE,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            try:
                db.execute_update(update_query, (study_info['id'],))
            except Exception as e:
                print(f"Error updating study registration: {str(e)}")  # Debug log
                # Don't return error here, as the processing was successful
                
        return jsonify(result)
        
    except Exception as e:
        print(f"Unexpected error in process_study: {str(e)}")  # Debug log
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@studies_bp.route('/studies/<int:study_id>/status', methods=['GET'])
def get_study_status(study_id):
    """Get processing status for a study"""
    status = sdm_interface.get_study_status(study_id)
    if not status:
        return jsonify({'error': 'Study not found'}), 404
    return jsonify(status)

@studies_bp.route('/studies/check-prior/<study_id>', methods=['GET'])
def check_prior_analysis(study_id):
    """Check if there is a prior analysis for the given study ID"""
    try:
        # Query the database for studies with matching study ID
        query = """
            SELECT id, name, description, study_id, 
                   created_at, last_updated, is_registered
            FROM studies 
            WHERE study_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        try:
            result = db.execute_single(query, (study_id,))
        except psycopg2.OperationalError as e:
            # Database connection error
            return jsonify({
                'error': 'Database connection failed. Please check your database configuration.',
                'details': str(e)
            }), 503
        except Exception as e:
            # Other database errors
            return jsonify({
                'error': 'Database error occurred',
                'details': str(e)
            }), 500
        
        if result:
            return jsonify({
                'exists': True,
                'study': dict(result)  # Convert RealDictRow to dict
            })
        
        return jsonify({
            'exists': False,
            'study': None
        })
        
    except Exception as e:
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@studies_bp.route('/studies/check-subject/<study_id>/<subid>', methods=['GET'])
def check_subject_analysis(study_id, subid):
    """Check if there is a prior analysis for the given study ID and subject ID"""
    try:
        # First get the study ID from the studies table
        study_query = """
            SELECT id FROM studies 
            WHERE study_id = %s AND is_registered = TRUE
        """
        try:
            study_result = db.execute_single(study_query, (study_id,))
            if not study_result:
                return jsonify({
                    'exists': False,
                    'instance': None
                })
            
            # Then check for the subject in sdm_instances
            instance_query = """
                SELECT i.id, i.study_id, i.subid, i.sdp_file_path, 
                       i.created_at, i.last_updated, i.processing_status,
                       s.is_registered
                FROM sdm_instances i
                JOIN studies s ON i.study_id = s.id
                WHERE i.study_id = %s AND i.subid = %s
                ORDER BY i.created_at DESC
                LIMIT 1
            """
            instance_result = db.execute_single(instance_query, (study_result['id'], subid))
            
            if instance_result:
                return jsonify({
                    'exists': True,
                    'instance': dict(instance_result)
                })
            
            return jsonify({
                'exists': False,
                'instance': None
            })
            
        except psycopg2.OperationalError as e:
            return jsonify({
                'error': 'Database connection failed. Please check your database configuration.',
                'details': str(e)
            }), 503
        except Exception as e:
            return jsonify({
                'error': 'Database error occurred',
                'details': str(e)
            }), 500
        
    except Exception as e:
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500 