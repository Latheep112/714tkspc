import os
import sys
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from project import app, db

def update_database_v4():
    with app.app_context():
        conn = db.engine.connect()
        
        # Student table
        try:
            conn.execute(db.text('ALTER TABLE student ADD COLUMN registration_number VARCHAR(50)'))
            print("Added registration_number to student table")
        except Exception as e:
            print(f"Error adding registration_number to student: {e}")

        # AdmissionApplication table
        try:
            conn.execute(db.text('ALTER TABLE admission_application ADD COLUMN registration_number VARCHAR(50)'))
            print("Added registration_number to admission_application table")
        except Exception as e:
            print(f"Error adding registration_number to admission_application: {e}")

        db.session.commit()
        print("Database schema migration v4 completed.")

if __name__ == '__main__':
    update_database_v4()
