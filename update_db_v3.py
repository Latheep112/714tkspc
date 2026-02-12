import os
import sys
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from project import app, db

def update_database_v3():
    with app.app_context():
        # First create all new tables (Department, Semester, Subject)
        db.create_all()
        print("Created new tables (Department, Semester, Subject)")
        
        conn = db.engine.connect()
        
        # Add foreign key columns to existing tables
        
        # Student table
        try:
            conn.execute(db.text('ALTER TABLE student ADD COLUMN department_id INTEGER REFERENCES department(id)'))
            print("Added department_id to student table")
        except Exception as e:
            print(f"Error adding department_id to student: {e}")

        try:
            conn.execute(db.text('ALTER TABLE student ADD COLUMN semester_id INTEGER REFERENCES semester(id)'))
            print("Added semester_id to student table")
        except Exception as e:
            print(f"Error adding semester_id to student: {e}")

        # Teacher table
        try:
            conn.execute(db.text('ALTER TABLE teacher ADD COLUMN department_id INTEGER REFERENCES department(id)'))
            print("Added department_id to teacher table")
        except Exception as e:
            print(f"Error adding department_id to teacher: {e}")

        # Course table
        try:
            conn.execute(db.text('ALTER TABLE course ADD COLUMN department_id INTEGER REFERENCES department(id)'))
            print("Added department_id to course table")
        except Exception as e:
            print(f"Error adding department_id to course: {e}")

        try:
            conn.execute(db.text('ALTER TABLE course ADD COLUMN semester_id INTEGER REFERENCES semester(id)'))
            print("Added semester_id to course table")
        except Exception as e:
            print(f"Error adding semester_id to course: {e}")

        try:
            conn.execute(db.text('ALTER TABLE course ADD COLUMN subject_id INTEGER REFERENCES subject(id)'))
            print("Added subject_id to course table")
        except Exception as e:
            print(f"Error adding subject_id to course: {e}")

        db.session.commit()
        print("Database schema migration v3 completed.")

if __name__ == '__main__':
    update_database_v3()
