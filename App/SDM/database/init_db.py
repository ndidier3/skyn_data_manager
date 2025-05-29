from connection import db
from schema import CREATE_TABLES

def init_database():
    db.execute_update(CREATE_TABLES)
    print("Database schema initialized successfully!")

if __name__ == "__main__":
    init_database() 