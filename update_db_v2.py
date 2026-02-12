import os
import sys
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from project import app, db
from project.models import AdmissionApplication, Course, Student, Exam, Notification

def update_database():
    with app.app_context():
        # Check if columns exist and add them if not
        conn = db.engine.connect()
        
        # Course table updates
        try:
            conn.execute(db.text('ALTER TABLE course ADD COLUMN syllabus_progress INTEGER DEFAULT 0'))
            print("Added syllabus_progress to course table")
        except Exception:
            print("syllabus_progress already exists or error adding it")
            
        try:
            conn.execute(db.text('ALTER TABLE course ADD COLUMN section_name VARCHAR(50)'))
            print("Added section_name to course table")
        except Exception:
            print("section_name already exists or error adding it")
            
        # AdmissionApplication table updates
        try:
            conn.execute(db.text('ALTER TABLE admission_application ADD COLUMN merit_score FLOAT'))
            print("Added merit_score to admission_application table")
        except Exception:
            print("merit_score already exists or error adding it")
            
        try:
            conn.execute(db.text('ALTER TABLE admission_application ADD COLUMN seat_allotted BOOLEAN DEFAULT 0'))
            print("Added seat_allotted to admission_application table")
        except Exception:
            print("seat_allotted already exists or error adding it")

        try:
            conn.execute(db.text('ALTER TABLE admission_application ADD COLUMN documents_verified BOOLEAN DEFAULT 0'))
            print("Added documents_verified to admission_application table")
        except Exception:
            print("documents_verified already exists or error adding it")

        # Grade table updates
        try:
            conn.execute(db.text('ALTER TABLE grade ADD COLUMN exam_id INTEGER REFERENCES exam(id)'))
            print("Added exam_id to grade table")
        except Exception:
            print("exam_id already exists or error adding it")

        # Create Exam table
        db.create_all()
        print("Database tables updated.")

if __name__ == '__main__':
    update_database()
