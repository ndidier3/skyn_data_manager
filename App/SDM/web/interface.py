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
                SELECT s.*, i.subid, i.sdp_file_path
                FROM studies s
                JOIN sdm_instances i ON s.study_id = i.study_id
                WHERE s.study_id = %s
            """, (study_id,))
            
            if not study:
                return {'error': 'Study not found'}
            
            # Get base directory
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            
            # Initialize SDM instance
            self.active_sdm = SDM(
                project_root=base_dir,
                data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                output_folder_name=study['study_id']  # Use study_id as output folder name
            )
            
            # Process the data
            self.active_sdm.process_single_subject(
                subid=study['subid'],
                use_prior_save=options.get('use_prior_save', False),
                smooth_and_impute=options.get('smooth_and_impute', True),
                adjust_for_gaps_and_non_wear=options.get('adjust_for_gaps_and_non_wear', True),
                analyze_days=options.get('analyze_days', False),
                identify_curves=options.get('identify_curves', False),
                gaps_and_non_wear_attrs=settings.get('gaps_and_non_wear', {}),
                smooth_and_impute_attrs=settings.get('smooth_and_impute', {}),
                curve_attrs=settings.get('curve', {}),
                day_attrs=settings.get('day', {})
            )
            
            # Save the processed data to a consistent location
            save_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
            os.makedirs(save_dir, exist_ok=True)
            
            # Create a consistent filename based on study and subject
            filename = f"{study['subid']}_{study['study_id']}_skyn_data_processed.sdp"
            save_path = os.path.join(save_dir, filename)
            
            # Save the SDM instance
            save_to_computer(self.active_sdm, filename, save_dir)
            
            # Update the database with the new file path
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'completed',
                    sdp_file_path = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE study_id = %s AND subid = %s
            """, (save_path, study_id, study['subid']))
            
            return {
                'status': self.active_sdm.get_status_report(),
                'settings': self.active_sdm.get_settings()
            }
            
        except Exception as e:
            print(f"Error in process_data: {str(e)}")
            # Save error state
            try:
                save_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
                os.makedirs(save_dir, exist_ok=True)
                filename = f"{study['subid']}_{study['study_id']}_skyn_data_error.sdp"
                save_path = os.path.join(save_dir, filename)
                save_to_computer(self.active_sdm, filename, save_dir)
                
                # Update database with error state
                db.execute_update("""
                    UPDATE sdm_instances 
                    SET processing_status = 'error',
                        last_error = %s,
                        sdp_file_path = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE study_id = %s AND subid = %s
                """, (str(e), save_path, study_id, study['subid']))
            except Exception as save_error:
                print(f"Error saving error state: {str(save_error)}")
            
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