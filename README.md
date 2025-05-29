# Skyn Data Manager (SDM) Web Interface

A web interface for managing and processing Skyn data using the SDM system. This interface provides a RESTful API for interacting with SDM instances, managing studies, and accessing curve features and event matches.

## Project Structure

```
App/SDM/
├── database/
│   ├── __init__.py
│   ├── schema.py        # Database schema definitions
│   ├── connection.py    # Database connection management
│   └── models.py        # Database models/ORM
└── web/
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   ├── routes.py    # API route definitions
    │   └── endpoints/   # Individual endpoint modules
    │       ├── __init__.py
    │       ├── studies.py
    │       ├── curves.py
    │       └── events.py
    └── interface.py     # SDM web interface
```

## Database Schema

The system uses PostgreSQL with the following tables:

- `sdm_instances`: Stores information about SDM instances
  - `id`: Primary key
  - `name`: Study/collection name
  - `description`: Optional study description
  - `subid`: Subject ID
  - `dataset_identifier`: Dataset identifier
  - `sdp_file_path`: Path to the SDP file
  - `processing_status`: Current processing status
  - `created_at`: Creation timestamp
  - `last_updated`: Last update timestamp

- `users`: User management
  - `id`: Primary key
  - `username`: Unique username
  - `email`: Unique email address
  - `created_at`: Account creation timestamp

- `user_sdm_access`: User access control
  - `user_id`: Foreign key to users
  - `sdm_instance_id`: Foreign key to sdm_instances
  - `access_level`: Access level ('read', 'write', 'admin')

## API Endpoints

### Studies
- `GET /api/studies`: List all studies
- `GET /api/studies/<study_id>`: Get study details
- `POST /api/studies`: Create new study
- `POST /api/studies/<study_id>/process`: Process study data

### Curves
- `GET /api/studies/<study_id>/curves`: Get curve features
- `GET /api/studies/<study_id>/curves/plots`: Get curve plots

### Events
- `GET /api/studies/<study_id>/events`: Get event matches
- `GET /api/studies/<study_id>/events/quality`: Get event quality metrics

## Setup

1. Set up environment variables:
```bash
export SDM_DB_NAME=sdm_db
export SDM_DB_USER=sdm_user
export SDM_DB_PASSWORD=your_password
export SDM_DB_HOST=localhost
export SDM_DB_PORT=5432
export SDM_SDP_STORAGE=App/SDM/Inputs/Skyn_Data_PROCESSED
```

2. Install dependencies:
```bash
pip install flask psycopg2-binary
```

3. Initialize the database:
```python
from App.SDM.database.schema import CREATE_TABLES
from App.SDM.database.connection import db

# Create tables
with db.get_cursor() as cursor:
    cursor.execute(CREATE_TABLES)
```

4. Run the application:
```python
from App.SDM.web.api.routes import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

## Usage

The web interface provides a RESTful API for managing SDM instances. Here are some example requests:

### Create a new study
```bash
curl -X POST http://localhost:5000/api/studies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Study",
    "description": "A test study",
    "subid": "SUB001",
    "dataset_identifier": "DS001"
  }'
```

### Process study data
```bash
curl -X POST http://localhost:5000/api/studies/1/process \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "process_curves": true,
      "process_events": true
    }
  }'
```

### Get curve features
```bash
curl http://localhost:5000/api/studies/1/curves
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:
- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON object with an `error` field containing the error message.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 