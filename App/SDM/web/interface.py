"""
SDM web interface that connects database with SDM instances.
"""

from App.SDM.database.connection import db
from App.SDM.sdm import SDM
from App.SDM.Configuration.file_management import load, save_to_computer, save_sdm_instance
import os

class SDMWebInterface:
    def __init__(self, sdp_storage_path):
        self.sdp_storage = sdp_storage_path
        self.active_sdm = None  # Currently loaded SDM instance

    def get_all_studies(self):
        """Get all studies from the database"""
        query = """
            SELECT s.study_id, s.created_at, s.last_updated,
                   COUNT(i.id) as instance_count
            FROM studies s
            LEFT JOIN sdm_instances i ON s.study_id = i.study_id
            GROUP BY s.study_id, s.created_at, s.last_updated
            ORDER BY s.created_at DESC
        """
        try:
            results = db.execute_query(query)
            return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting studies: {str(e)}")
            return []

    def load_study(self, study_id):
        """Load a specific study from the database"""
        query = """
            SELECT s.study_id, s.name, s.description,
                   s.created_at, s.last_updated,
                   COUNT(i.id) as instance_count
            FROM studies s
            LEFT JOIN sdm_instances i ON s.study_id = i.study_id
            WHERE s.study_id = %s
            GROUP BY s.study_id, s.name, s.description, s.created_at, s.last_updated
        """
        try:
            result = db.execute_single(query, (study_id,))
            if result:
                return dict(result)
            return None
        except Exception as e:
            print(f"Error loading study: {str(e)}")
            return None

    def get_day_features(self, study_id):
        """Get day features for a study"""
        if not self.active_sdm or self.active_sdm.id != study_id:
            self.load_study(study_id)
            
        if not self.active_sdm:
            return None
            
        # Get day features from the active SDM instance
        day_features = []
        for day_dataset in self.active_sdm.day_datasets:
            # Convert DataFrame to dict for JSON serialization
            features = day_dataset.to_dict(orient='records')
            day_features.extend(features)
            
        return {
            'features': day_features,
            'plots': self.active_sdm.plot_paths,
            'status': self.active_sdm.get_status_report()
        }

    def get_curve_features(self, study_id):
        """Get curve features for a study"""
        if not self.active_sdm or self.active_sdm.id != study_id:
            self.load_study(study_id)
            
        if not self.active_sdm:
            return None
            
        return {
            'features': self.active_sdm.curve_features,
            'plots': self.active_sdm.plot_paths,
            'status': self.active_sdm.status
        }

    def get_event_matches(self, study_id):
        """Get event matches for a study"""
        if not self.active_sdm or self.active_sdm.id != study_id:
            self.load_study(study_id)
            
        if not self.active_sdm:
            return None
            
        return {
            'events': self.active_sdm.events,
            'matches': self.active_sdm.event_curve_matches,
            'quality_metrics': self.active_sdm.ema_region_features
        }

    def create_study(self, name, description, subid, study_id):
        """Create a new study"""
        try:
            # Create SDP file path
            sdp_path = os.path.join(self.sdp_storage, f'{subid}_{study_id}_skyn_data_processed.sdp')
            
            # Create study in database
            result = db.execute_single("""
                INSERT INTO studies 
                (name, description, study_id)
                VALUES (%s, %s, %s)
                RETURNING study_id
            """, (name, description, study_id))
            
            # Create SDM instance
            instance_result = db.execute_single("""
                INSERT INTO sdm_instances 
                (study_id, subid, sdp_file_path)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (study_id, subid, sdp_path))
            
            return {
                'study_id': result['study_id'],
                'instance_id': instance_result['id']
            }
        except Exception as e:
            return {'error': str(e)}

    def process_data(self, study_id, options=None, settings=None):
        """Process data for a study"""
        try:
            # Get study info from DB
            study = db.execute_single("""
                SELECT s.*, i.subid, i.dataset_identifier
                FROM studies s
                JOIN sdm_instances i ON s.id = i.study_id
                WHERE s.id = %s
            """, (study_id,))
            
            if not study:
                return {'error': 'Study not found'}
            
            # Get base directory
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            
            # Initialize SDM instance
            self.active_sdm = SDM(
                base_dir=base_dir,
                data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                processed_data_out=os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED'),
                results_dir=os.path.join(base_dir, 'Results'),
                subid=study['subid'],
                dataset_identifier=study['dataset_identifier']
            )
            
            # Process the data
            self.active_sdm.process_single_subject(
                subid=study['subid'],
                **options or {}
            )
            
            # Only mark as registered if processing completed successfully
            if self.active_sdm.status.get('gaps_and_non_wear') == 'success':
                print(f"Processing successful, updating registration status")  # Debug log
                # Update study registration status
                db.execute_update("""
                    UPDATE studies s
                    SET is_registered = TRUE,
                        last_updated = CURRENT_TIMESTAMP
                    FROM sdm_instances i
                    WHERE s.id = i.study_id
                    AND i.id = %s
                """, (study_id,))
                
                # Save the processed data
                print(f"Saving processed data")  # Debug log
                save_path = save_sdm_instance(
                    self.active_sdm,
                    base_dir,
                    study['subid'],
                    study['dataset_identifier'],
                    status='processed'
                )
            
                # Update instance status to completed
                db.execute_update("""
                    UPDATE sdm_instances 
                    SET processing_status = 'completed',
                        sdp_file_path = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (save_path, study_id))
            else:
                print(f"Processing failed, saving invalid state")  # Debug log
                # If processing failed, save invalid state
                save_path = save_sdm_instance(
                    self.active_sdm,
                    base_dir,
                    study['subid'],
                    study['dataset_identifier'],
                    status='invalid'
                )
            db.execute_update("""
                UPDATE sdm_instances 
                    SET processing_status = 'error', 
                        last_error = 'Processing failed',
                        sdp_file_path = %s,
                        last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
                """, (save_path, study_id))
            
            return {
                'status': self.active_sdm.get_status_report(),
                'settings': self.active_sdm.get_settings()
            }
        except Exception as e:
            print(f"Error in process_data: {str(e)}")  # Debug log
            if self.active_sdm:
                save_path = save_sdm_instance(
                    self.active_sdm,
                    base_dir,
                    study['subid'],
                    study['dataset_identifier'],
                    status='error'
                )
            db.execute_update("""
                UPDATE sdm_instances 
                    SET processing_status = 'error', 
                        last_error = %s,
                        sdp_file_path = %s,
                        last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
                """, (str(e), save_path, study_id))
            return {'error': str(e)}

    def get_study_status(self, study_id):
        """Get processing status for a study"""
        study = db.execute_single("""
            SELECT id, processing_status, last_error, last_updated
            FROM sdm_instances 
            WHERE id = %s
        """, (study_id,))
        
        if not study:
            return None
            
        return {
            'status': study['processing_status'],
            'last_error': study['last_error'],
            'last_updated': study['last_updated']
        } 