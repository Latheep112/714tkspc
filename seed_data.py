from project import app, db
from project.models import Student, Teacher, Course, User, CourseSession, Attendance, Grade, AdmissionApplication, FeeAccount, FeePayment, Resource, ResourceBooking, Invoice, BudgetCategory, BudgetTransaction
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date
import random

def seed():
    with app.app_context():
        print("Seeding database...")
        
        # Create Admin User if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password_hash=generate_password_hash('admin'), role='admin')
            db.session.add(admin)
            print("Created admin user.")

        # Create Teachers
        teachers = []
        departments = ['Computer Science', 'Mathematics', 'Physics', 'History', 'Literature']
        for i in range(1, 6):
            name = f"Teacher {i}"
            email = f"teacher{i}@school.com"
            if not Teacher.query.filter_by(email=email).first():
                t = Teacher(
                    name=name,
                    email=email,
                    phone=f"555-010{i}",
                    department=departments[i-1],
                    joining_date=date(2020, 1, 1),
                    gender=random.choice(['Male', 'Female'])
                )
                db.session.add(t)
                teachers.append(t)
        db.session.commit()
        teachers = Teacher.query.all() # Refresh with IDs
        print(f"Created {len(teachers)} teachers.")

        # Create Courses
        courses = []
        for i, t in enumerate(teachers):
            code = f"CS10{i}"
            if not Course.query.filter_by(code=code).first():
                c = Course(
                    name=f"Intro to {t.department}",
                    code=code,
                    credits=3,
                    department=t.department,
                    teacher_id=t.id,
                    semester='Fall 2025'
                )
                db.session.add(c)
                courses.append(c)
        db.session.commit()
        courses = Course.query.all()
        print(f"Created {len(courses)} courses.")

        # Create Students
        students = []
        for i in range(1, 21):
            email = f"student{i}@school.com"
            if not Student.query.filter_by(email=email).first():
                s = Student(
                    name=f"Student {i}",
                    email=email,
                    phone=f"555-020{i}",
                    roll_number=f"2025-{100+i}",
                    admission_date=date(2025, 1, 1),
                    gender=random.choice(['Male', 'Female']),
                    department=random.choice(departments)
                )
                db.session.add(s)
                students.append(s)
        db.session.commit()
        students = Student.query.all()
        print(f"Created {len(students)} students.")

        # Enroll Students
        for s in students:
            # Enroll in 2 random courses
            enrolled = random.sample(courses, 2)
            for c in enrolled:
                if c not in s.courses:
                    s.courses.append(c)
        db.session.commit()
        print("Enrolled students in courses.")

        # Create Sessions & Attendance
        for c in courses:
            for d in range(5): # 5 sessions
                s_date = date.today() - timedelta(days=d*7)
                if not CourseSession.query.filter_by(course_id=c.id, session_date=s_date).first():
                    sess = CourseSession(course_id=c.id, session_date=s_date, title=f"Lecture {d+1}")
                    db.session.add(sess)
                    db.session.commit() # Need ID
                    
                    # Mark attendance
                    course_students = c.students
                    for stud in course_students:
                        status = random.choice(['present', 'present', 'present', 'absent', 'late'])
                        att = Attendance(session_id=sess.id, student_id=stud.id, status=status)
                        db.session.add(att)
        db.session.commit()
        print("Created sessions and attendance.")

        # Create Admissions (Pending)
        for i in range(1, 6):
            email = f"applicant{i}@new.com"
            if not AdmissionApplication.query.filter_by(email=email).first():
                adm_app = AdmissionApplication(
                    name=f"Applicant {i}",
                    email=email,
                    status='pending',
                    applied_at=datetime.utcnow()
                )
                db.session.add(adm_app)
        db.session.commit()
        print("Created pending admission applications.")

        # Create Resources
        if not Resource.query.filter_by(name="Main Hall").first():
            r = Resource(name="Main Hall", type="Hall", capacity=200, location="Building A")
            db.session.add(r)
        if not Resource.query.filter_by(name="Lab 1").first():
            r = Resource(name="Lab 1", type="Lab", capacity=30, location="Building B")
            db.session.add(r)
        db.session.commit()
        
        # Create Invoices
        for s in students[:5]:
            inv = Invoice(
                student_id=s.id,
                amount_due=1500.0,
                description="Tuition Fee",
                issued_at=datetime.utcnow(),
                due_date=date.today() + timedelta(days=30),
                status='unpaid'
            )
            db.session.add(inv)
        db.session.commit()
        print("Created sample invoices.")

        print("Seeding complete.")

if __name__ == "__main__":
    seed()
