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
            SELECT s.study_id, s.name, s.description, s.created_at, s.last_updated,
                   i.id as instance_id, i.subid, i.sdp_file_path, i.processing_status,
                   i.created_at as instance_created_at, i.last_updated as instance_last_updated
            FROM studies s
            LEFT JOIN sdm_instances i ON s.study_id = i.study_id
            ORDER BY s.created_at DESC, i.created_at DESC
        """
        try:
            results = db.execute_query(query)
            return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting studies: {str(e)}")
            return []

    def load_study(self, study_id):
        """Load a specific study from the database with all related information"""
        try:
            # Get basic study info
            study_query = """
                SELECT s.study_id, s.name, s.description,
                       s.created_at, s.last_updated,
                       COUNT(i.id) as instance_count
                FROM studies s
                LEFT JOIN sdm_instances i ON s.study_id = i.study_id
                WHERE s.study_id = %s::text
                GROUP BY s.study_id, s.name, s.description, s.created_at, s.last_updated
            """
            study = db.execute_single(study_query, (str(study_id),))
            if not study:
                return None

            # Get instance info with status
            instance_query = """
                SELECT i.id, i.subid, i.processing_status, i.last_error,
                       i.created_at as instance_created_at,
                       i.last_updated as instance_last_updated,
                       i.sdp_file_path
                FROM sdm_instances i
                WHERE i.study_id = %s::text
                ORDER BY i.created_at DESC
                LIMIT 1
            """
            instance = db.execute_single(instance_query, (str(study_id),))

            # Try to load SDM instance to get settings and detailed status
            sdm_instance = None
            if instance and instance['sdp_file_path']:
                try:
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                    sdm_instance = SDM(
                        project_root=base_dir,
                        data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                        output_folder_name=study_id
                    )
                    sdm_instance = load(os.path.basename(instance['sdp_file_path']), 
                                     os.path.dirname(instance['sdp_file_path']))
                except Exception as e:
                    print(f"Error loading SDM instance: {str(e)}")

            # Combine all information
            result = dict(study)
            if instance:
                result.update({
                    'instance_id': instance['id'],
                    'subid': instance['subid'],
                    'processing_status': instance['processing_status'],
                    'last_error': instance['last_error'],
                    'instance_created_at': instance['instance_created_at'],
                    'instance_last_updated': instance['instance_last_updated']
                })

            # Add SDM information if available
            if sdm_instance:
                result.update({
                    'settings': sdm_instance.get_settings(),
                    'status': sdm_instance.get_status_report()['status'],
                    'errors': sdm_instance.get_status_report()['errors']
                })
            else:
                # Provide default values if SDM instance not available
                result.update({
                    'settings': {
                        'day': {'enabled': False},
                        'curve': {'enabled': False}
                    },
                    'status': {
                        'gaps_and_non_wear': 'not_attempted',
                        'smooth_and_impute': 'not_attempted',
                        'identify_curves': 'not_attempted',
                        'analyze_days': 'not_attempted',
                        'match_events': 'not_attempted',
                        'analyze_curves': 'not_attempted',
                        'export_results': 'not_attempted'
                    },
                    'errors': {}
                })

            return result
        except Exception as e:
            print(f"Error loading study: {str(e)}")
            return None

    def get_day_features(self, study_id):
        """Get day features for a study"""
        try:
            # Try to load the study first
            study = self.load_study(study_id)
            if not study:
                return {'error': 'Study not found'}

            # Try to load the SDM instance
            if not self.active_sdm or self.active_sdm.id != study_id:
                # Initialize SDM instance
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                self.active_sdm = SDM(
                    project_root=base_dir,
                    data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                    output_folder_name=study_id
                )
                
                # Try to load the processed data
                try:
                    processed_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
                    sdp_files = [f for f in os.listdir(processed_dir) if f.endswith('.sdp') and study_id in f]
                    if sdp_files:
                        self.active_sdm = load(sdp_files[0], processed_dir)
                except Exception as e:
                    print(f"Error loading SDM instance: {str(e)}")
                    return {'error': 'Analysis not run'}

            if not self.active_sdm:
                return {'error': 'Analysis not run'}
                
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
        except Exception as e:
            print(f"Error getting day features: {str(e)}")
            return {'error': str(e)}

    def get_curve_features(self, study_id):
        """Get curve features for a study"""
        try:
            # Try to load the study first
            study = self.load_study(study_id)
            if not study:
                return {'error': 'Study not found'}

            # Try to load the SDM instance
            if not self.active_sdm or self.active_sdm.id != study_id:
                # Initialize SDM instance
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                self.active_sdm = SDM(
                    project_root=base_dir,
                    data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                    output_folder_name=study_id
                )
                
                # Try to load the processed data
                try:
                    processed_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
                    sdp_files = [f for f in os.listdir(processed_dir) if f.endswith('.sdp') and study_id in f]
                    if sdp_files:
                        self.active_sdm = load(sdp_files[0], processed_dir)
                except Exception as e:
                    print(f"Error loading SDM instance: {str(e)}")
                    return {'error': 'Analysis not run'}

            if not self.active_sdm:
                return {'error': 'Analysis not run'}
                
            return {
                'features': self.active_sdm.curve_features,
                'plots': self.active_sdm.plot_paths,
                'status': self.active_sdm.status
            }
        except Exception as e:
            print(f"Error getting curve features: {str(e)}")
            return {'error': str(e)}

    def get_event_matches(self, study_id):
        """Get event matches for a study"""
        try:
            # Try to load the study first
            study = self.load_study(study_id)
            if not study:
                return {'error': 'Study not found'}

            # Try to load the SDM instance
            if not self.active_sdm or self.active_sdm.id != study_id:
                # Initialize SDM instance
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                self.active_sdm = SDM(
                    project_root=base_dir,
                    data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                    output_folder_name=study_id
                )
                
                # Try to load the processed data
                try:
                    processed_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
                    sdp_files = [f for f in os.listdir(processed_dir) if f.endswith('.sdp') and study_id in f]
                    if sdp_files:
                        self.active_sdm = load(sdp_files[0], processed_dir)
                except Exception as e:
                    print(f"Error loading SDM instance: {str(e)}")
                    return {'error': 'Analysis not run'}

            if not self.active_sdm:
                return {'error': 'Analysis not run'}
                
            return {
                'events': self.active_sdm.events,
                'matches': self.active_sdm.event_curve_matches,
                'quality_metrics': self.active_sdm.ema_region_features
            }
        except Exception as e:
            print(f"Error getting event matches: {str(e)}")
            return {'error': str(e)}

    def create_study(self, name, description, subid, study_id):
        """Create a new study"""
        try:
            # Create SDP file path
            sdp_path = os.path.join(self.sdp_storage, f'{subid}_{study_id}_skyn_data_processed.sdp')
            
            # Create study in database
            result = db.execute_single("""
                INSERT INTO studies 
                (name, description, study_id)
                VALUES (%s, %s, %s::text)
                RETURNING study_id
            """, (name, description, str(study_id)))
            
            # Create SDM instance
            instance_result = db.execute_single("""
                INSERT INTO sdm_instances 
                (study_id, subid, sdp_file_path)
                VALUES (%s::text, %s, %s)
                RETURNING id
            """, (str(study_id), subid, sdp_path))
            
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
                WHERE s.study_id = %s::text
            """, (str(study_id),))
            
            if not study:
                return {'error': 'Study not found'}
            
            print(f"Processing study {study_id} with options:", options)
            print(f"Processing study {study_id} with settings:", settings)
            
            # Update database to show processing
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'processing',
                    last_updated = CURRENT_TIMESTAMP
                WHERE study_id = %s::text AND subid = %s
            """, (str(study_id), study['subid']))
            
            # Get base directory
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            
            # Initialize SDM instance
            self.active_sdm = SDM(
                project_root=base_dir,
                data_input_folder=os.path.join(base_dir, 'Inputs', 'Skyn_Data_RAW'),
                output_folder_name=study['study_id']
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
            
            # Get status report before saving
            status_report = self.active_sdm.get_status_report()
            print(f"Status report after processing:", status_report)
            
            # Save the processed data
            save_dir = os.path.join(base_dir, 'Inputs', 'Skyn_Data_PROCESSED')
            os.makedirs(save_dir, exist_ok=True)
            filename = f"{study['subid']}_{study['study_id']}_skyn_data_processed.sdp"
            save_path = os.path.join(save_dir, filename)
            save_to_computer(self.active_sdm, filename, save_dir)
            
            # Update database with completion status
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'completed',
                    sdp_file_path = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE study_id = %s::text AND subid = %s
            """, (save_path, str(study_id), study['subid']))
            
            # Get final settings and status
            final_settings = self.active_sdm.get_settings()
            final_status = status_report['status']
            
            print("Final settings:", final_settings)
            print("Final status:", final_status)
            
            return {
                'status': final_status,
                'settings': final_settings,
                'errors': status_report['errors']
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
                    WHERE study_id = %s::text AND subid = %s
                """, (str(e), save_path, str(study_id), study['subid']))
            except Exception as save_error:
                print(f"Error saving error state: {str(save_error)}")
            
            return {'error': str(e)}

    def get_study_settings(self, study_id):
        """Get current settings for a study"""
        try:
            study = self.load_study(study_id)
            if not study:
                return None
            return study.get('settings', {
                'day': {'enabled': False},
                'curve': {'enabled': False}
            })
        except Exception as e:
            print(f"Error getting study settings: {str(e)}")
            return None

    def get_study_status(self, study_id):
        """Get detailed processing status for a study"""
        try:
            study = self.load_study(study_id)
            if not study:
                return None
            return {
                'status': study.get('status', {}),
                'errors': study.get('errors', {}),
                'processing_status': study.get('processing_status'),
                'last_error': study.get('last_error'),
                'last_updated': study.get('instance_last_updated')
            }
        except Exception as e:
            print(f"Error getting study status: {str(e)}")
            return None 