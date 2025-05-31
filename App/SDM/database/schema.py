"""
Database schema definitions for SDM web interface.
"""

CREATE_TABLES = """
-- Core tables
CREATE TABLE IF NOT EXISTS studies (
    study_id VARCHAR(50) PRIMARY KEY,                -- Unique identifier for the study (e.g., "032")
    name VARCHAR(100) NOT NULL,                      -- Study name
    description TEXT,                                -- Study description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sdm_instances (
    id SERIAL PRIMARY KEY,
    study_id VARCHAR(50) REFERENCES studies(study_id),  -- Reference to the study
    subid VARCHAR(50) NOT NULL,                      -- Subject ID
    sdp_file_path VARCHAR(255) NOT NULL,            -- Path to the SDP file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'not_started',  -- 'not_started', 'in_progress', 'completed', 'error'
    last_error TEXT,
    UNIQUE(study_id, subid)                          -- One instance per subject per study
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_study_access (
    user_id INTEGER REFERENCES users(id),
    study_id VARCHAR(50) REFERENCES studies(study_id),
    access_level VARCHAR(20) NOT NULL,  -- 'read', 'write', 'admin'
    PRIMARY KEY (user_id, study_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sdm_instances_study_id ON sdm_instances(study_id);
CREATE INDEX IF NOT EXISTS idx_sdm_instances_subid ON sdm_instances(subid);
CREATE INDEX IF NOT EXISTS idx_sdm_instances_status ON sdm_instances(processing_status);
CREATE INDEX IF NOT EXISTS idx_user_study_access_user ON user_study_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_study_access_study ON user_study_access(study_id);
""" 