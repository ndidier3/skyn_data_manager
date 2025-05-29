"""
SDM web interface that connects database with SDM instances.
"""

from App.SDM.database.connection import db
from App.SDM.sdm import SDM
from App.SDM.Configuration.file_management import load
import os

class SDMWebInterface:
    def __init__(self, sdp_storage_path):
        self.sdp_storage = sdp_storage_path
        self.active_sdm = None  # Currently loaded SDM instance

    def get_all_studies(self):
        """Get all studies from the database"""
        return db.execute_query("""
            SELECT id, name, description, subid, dataset_identifier, 
                   processing_status, created_at, last_updated
            FROM sdm_instances
            ORDER BY created_at DESC
        """)

    def load_study(self, study_id):
        """Load a study's SDM instance"""
        # Get study info from DB
        study = db.execute_single("""
            SELECT * FROM sdm_instances 
            WHERE id = %s
        """, (study_id,))
        
        if not study:
            return None
            
        # Load the SDM instance
        try:
            self.active_sdm = load(study['sdp_file_path'])
            return {
                'study_info': study,
                'status': self.active_sdm.get_status_report(),
                'settings': self.active_sdm.get_settings()
            }
        except Exception as e:
            db.execute_update("""
                UPDATE sdm_instances 
                SET last_error = %s, processing_status = 'error'
                WHERE id = %s
            """, (str(e), study_id))
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

    def create_study(self, name, description, subid, dataset_identifier):
        """Create a new study"""
        try:
            # Create SDP file path
            sdp_path = os.path.join(self.sdp_storage, f'{subid}_{dataset_identifier}_skyn_data_processed.sdp')
            
            # Create study in database
            result = db.execute_single("""
                INSERT INTO sdm_instances 
                (name, description, subid, dataset_identifier, sdp_file_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (name, description, subid, dataset_identifier, sdp_path))
            
            return {'study_id': result['id']}
        except Exception as e:
            return {'error': str(e)}

    def process_data(self, study_id, options=None, settings=None):
        """Process data for a study"""
        if not self.active_sdm or self.active_sdm.id != study_id:
            self.load_study(study_id)
            
        if not self.active_sdm:
            return None
            
        try:
            # Update status to in_progress
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'in_progress'
                WHERE id = %s
            """, (study_id,))
            
            # Load settings if provided
            if settings:
                self.active_sdm.load_settings(settings)
            
            # Process data
            self.active_sdm.process_single_subject(
                subid=self.active_sdm.subid,
                **options or {}
            )
            self.active_sdm.save_self(valid=True)
            
            # Update status to completed
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'completed', last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (study_id,))
            
            return {
                'status': self.active_sdm.get_status_report(),
                'settings': self.active_sdm.get_settings()
            }
        except Exception as e:
            self.active_sdm.save_self(valid=False)
            db.execute_update("""
                UPDATE sdm_instances 
                SET processing_status = 'error', last_error = %s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (str(e), study_id))
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