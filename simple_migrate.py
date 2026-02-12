import sqlite3
import os

db_path = os.path.join('instance', 'site.db')

def migrate():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('ALTER TABLE student ADD COLUMN registration_number VARCHAR(50)')
            print("Added registration_number to student")
        except sqlite3.OperationalError as e:
            print(f"Student table error: {e}")
            
        try:
            cursor.execute('ALTER TABLE admission_application ADD COLUMN registration_number VARCHAR(50)')
            print("Added registration_number to admission_application")
        except sqlite3.OperationalError as e:
            print(f"AdmissionApplication table error: {e}")
            
        conn.commit()
        conn.close()
        print("Migration complete")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == '__main__':
    migrate()
