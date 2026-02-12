import sqlite3
import os

db_path = os.path.join('instance', 'site.db')

def migrate():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting comprehensive migration...")

        # 1. Create New Tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS department (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                code VARCHAR(20) UNIQUE,
                description TEXT,
                head_of_department_id INTEGER,
                FOREIGN KEY(head_of_department_id) REFERENCES teacher(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS semester (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                academic_year VARCHAR(20) NOT NULL,
                start_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS subject (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20) NOT NULL UNIQUE,
                description TEXT,
                department_id INTEGER,
                credits INTEGER DEFAULT 3,
                FOREIGN KEY(department_id) REFERENCES department(id)
            )
            """
        ]
        
        for table_sql in tables:
            try:
                cursor.execute(table_sql)
                print(f"Ensured table exists.")
            except Exception as e:
                print(f"Error creating table: {e}")

        # 2. Add Missing Columns to Existing Tables
        migrations = [
            ("student", "registration_number", "VARCHAR(50)"),
            ("student", "department_id", "INTEGER"),
            ("student", "semester_id", "INTEGER"),
            ("teacher", "department_id", "INTEGER"),
            ("course", "department_id", "INTEGER"),
            ("course", "semester_id", "INTEGER"),
            ("course", "subject_id", "INTEGER"),
            ("admission_application", "registration_number", "VARCHAR(50)")
        ]

        for table, column, col_type in migrations:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"Added {column} to {table}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"Column {column} already exists in {table}")
                else:
                    print(f"Error adding {column} to {table}: {e}")

        conn.commit()
        conn.close()
        print("Migration complete successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == '__main__':
    migrate()
