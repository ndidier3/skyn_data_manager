CREATE_TABLES = """
    CREATE TABLE IF NOT EXISTS studies (
        id SERIAL PRIMARY KEY,
        study_id VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sdm_instances (
        id SERIAL PRIMARY KEY,
        study_id VARCHAR(255) NOT NULL REFERENCES studies(study_id),
        subid VARCHAR(255) NOT NULL,
        sdp_file_path VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processing_status VARCHAR(50) DEFAULT 'not_started',
        UNIQUE(study_id, subid)
    );
""" 