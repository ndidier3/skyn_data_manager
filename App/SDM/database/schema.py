"""
Database schema definitions for SDM web interface.
"""

CREATE_TABLES = """
-- Core tables
CREATE TABLE IF NOT EXISTS sdm_instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- Study/collection name
    description TEXT,                     -- Optional description of the study
    subid VARCHAR(50) NOT NULL,          -- Subject ID
    dataset_identifier VARCHAR(50) NOT NULL,
    sdp_file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'not_started',  -- 'not_started', 'in_progress', 'completed', 'error'
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sdm_access (
    user_id INTEGER REFERENCES users(id),
    sdm_instance_id INTEGER REFERENCES sdm_instances(id),
    access_level VARCHAR(20) NOT NULL,  -- 'read', 'write', 'admin'
    PRIMARY KEY (user_id, sdm_instance_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sdm_instances_subid ON sdm_instances(subid);
CREATE INDEX IF NOT EXISTS idx_sdm_instances_status ON sdm_instances(processing_status);
CREATE INDEX IF NOT EXISTS idx_user_sdm_access_user ON user_sdm_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sdm_access_sdm ON user_sdm_access(sdm_instance_id);
""" 