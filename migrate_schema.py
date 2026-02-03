from project import app, db
from sqlalchemy import text

def add_column(table_name, column_name, column_type):
    with app.app_context():
        with db.engine.connect() as conn:
            try:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                print(f"Added {column_name} to {table_name}")
            except Exception as e:
                print(f"Column {column_name} in {table_name} might already exist: {e}")

if __name__ == "__main__":
    # Student
    add_column("student", "gender", "VARCHAR(10)")
    add_column("student", "admission_date", "DATE")
    add_column("student", "department", "VARCHAR(100)")
    add_column("student", "guardian_name", "VARCHAR(100)")
    add_column("student", "guardian_phone", "VARCHAR(20)")
    add_column("student", "status", "VARCHAR(20)")
    add_column("student", "guardian_email", "VARCHAR(100)")
    add_column("student", "emergency_contact_name", "VARCHAR(100)")
    add_column("student", "emergency_contact_phone", "VARCHAR(20)")
    add_column("student", "tutor_id", "INTEGER")
    
    # New student demographic and academic fields
    add_column("student", "nationality", "VARCHAR(50)")
    add_column("student", "blood_group", "VARCHAR(5)")
    add_column("student", "religion", "VARCHAR(50)")
    add_column("student", "community", "VARCHAR(50)")
    add_column("student", "sslc_marks", "INTEGER")
    add_column("student", "hsc_marks", "INTEGER")
    add_column("student", "current_year", "INTEGER")
    add_column("student", "current_semester", "INTEGER")
    add_column("student", "section", "VARCHAR(10)")
    add_column("student", "father_name", "VARCHAR(100)")
    add_column("student", "mother_name", "VARCHAR(100)")
    add_column("student", "emergency_contact_name", "VARCHAR(100)")
    add_column("student", "emergency_contact_phone", "VARCHAR(20)")
    add_column("student", "previous_school", "VARCHAR(255)")
    
    # Teacher
    add_column("teacher", "gender", "VARCHAR(10)")
    add_column("teacher", "joining_date", "DATE")
    add_column("teacher", "address", "VARCHAR(200)")
    add_column("teacher", "date_of_birth", "DATE")
    add_column("teacher", "office_hours", "VARCHAR(120)")
    add_column("teacher", "employment_status", "VARCHAR(20)")
    add_column("teacher", "max_weekly_hours", "INTEGER")
    add_column("teacher", "qualifications", "VARCHAR(120)")
    add_column("teacher", "experience_years", "INTEGER")
    add_column("teacher", "tenure_status", "VARCHAR(20)")
    
    # New teacher professional fields
    add_column("teacher", "designation", "VARCHAR(100)")
    add_column("teacher", "specialization", "VARCHAR(100)")
    add_column("teacher", "pan_number", "VARCHAR(20)")
    add_column("teacher", "aadhaar_number", "VARCHAR(20)")
    
    # Course
    add_column("course", "department", "VARCHAR(100)")
    add_column("course", "semester", "VARCHAR(50)")
    add_column("course", "room", "VARCHAR(120)")
    add_column("course", "capacity", "INTEGER")
    add_column("course", "schedule_notes", "TEXT")
    add_column("course", "modality", "VARCHAR(20)")
    
    # New course fields
    add_column("course", "syllabus_url", "VARCHAR(200)")
    add_column("course", "level", "VARCHAR(50)")
    add_column("course", "course_type", "VARCHAR(50)")
    add_column("course", "academic_year", "VARCHAR(20)")
    
    # Attendance
    add_column("attendance", "remarks", "VARCHAR(200)")
    
    # TeacherLeave
    add_column("teacher_leave", "approved_by", "VARCHAR(80)")
    
    # AdmissionApplication
    add_column("admission_application", "gender", "VARCHAR(20)")
    add_column("admission_application", "address", "TEXT")
    add_column("admission_application", "notes", "TEXT")
    add_column("admission_application", "phone", "VARCHAR(20)")
    add_column("admission_application", "date_of_birth", "DATE")
    add_column("admission_application", "processed_by", "VARCHAR(80)")
    add_column("admission_application", "intake_year", "INTEGER")
    add_column("admission_application", "program", "VARCHAR(100)")
    add_column("admission_application", "sslc_marks", "INTEGER")
    add_column("admission_application", "hsc_marks", "INTEGER")
    add_column("admission_application", "community", "VARCHAR(50)")
    add_column("admission_application", "religion", "VARCHAR(50)")
    
    # New demographic fields for application
    add_column("admission_application", "nationality", "VARCHAR(50)")
    add_column("admission_application", "blood_group", "VARCHAR(5)")
    
    add_column("admission_application", "requested_course_id", "INTEGER")
    add_column("admission_application", "photo_path", "VARCHAR(200)")
    add_column("admission_application", "father_name", "VARCHAR(100)")
    add_column("admission_application", "mother_name", "VARCHAR(100)")
    add_column("admission_application", "emergency_contact_name", "VARCHAR(100)")
    add_column("admission_application", "emergency_contact_phone", "VARCHAR(20)")
    add_column("admission_application", "previous_school", "VARCHAR(255)")
    
    # Resource
    add_column("resource", "status", "VARCHAR(20)")
    add_column("resource", "tags", "VARCHAR(200)")
    add_column("resource", "condition", "VARCHAR(20)")
    add_column("resource", "maintenance_due", "DATE")
    
    # Invoice
    add_column("invoice", "currency", "VARCHAR(10)")
    add_column("invoice", "reference", "VARCHAR(120)")
    add_column("invoice", "waiver_amount", "FLOAT")
    add_column("invoice", "discount_percent", "FLOAT")
    add_column("invoice", "tax_percent", "FLOAT")

    # Fee Account
    add_column("fee_account", "currency", "VARCHAR(10)")
    add_column("fee_account", "last_updated", "DATETIME")

    # Fee Payment
    add_column("fee_payment", "currency", "VARCHAR(10)")
    add_column("fee_payment", "status", "VARCHAR(20)")

    # Grade
    add_column("grade", "score", "FLOAT")
    add_column("grade", "letter", "VARCHAR(5)")
    add_column("grade", "points", "FLOAT")
    add_column("grade", "grade_letter", "VARCHAR(5)")
    add_column("grade", "comments", "TEXT")
    add_column("grade", "semester", "INTEGER")
    add_column("grade", "academic_year", "VARCHAR(20)")
    add_column("grade", "remarks", "TEXT")
    add_column("grade", "recorded_by", "VARCHAR(80)")
    
    print("Migration complete.")


