from project import db
from datetime import datetime

enrollments = db.Table('enrollments',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    roll_number = db.Column(db.String(50), unique=True)
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    admission_date = db.Column(db.Date)
    department = db.Column(db.String(100))
    guardian_name = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))
    guardian_email = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')
    tutor_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    nationality = db.Column(db.String(50))
    blood_group = db.Column(db.String(10))
    religion = db.Column(db.String(50))
    community = db.Column(db.String(50))
    sslc_marks = db.Column(db.Integer)
    hsc_marks = db.Column(db.Integer)
    current_year = db.Column(db.Integer)
    current_semester = db.Column(db.Integer)
    section = db.Column(db.String(10))
    father_name = db.Column(db.String(100))
    mother_name = db.Column(db.String(100))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    previous_school = db.Column(db.String(255))

    # Relationships
    courses = db.relationship('Course', secondary=enrollments, backref='students', lazy=True)
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade="all, delete-orphan")
    grades = db.relationship('Grade', backref='student', lazy=True, cascade="all, delete-orphan")
    fee_accounts = db.relationship('FeeAccount', backref='student', lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship('Invoice', backref='student', lazy=True, cascade="all, delete-orphan")
    payments = db.relationship('FeePayment', backref='student', lazy=True, cascade="all, delete-orphan")
    parent_links = db.relationship('ParentStudentLink', backref='student', lazy=True, cascade="all, delete-orphan")

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(100))
    address = db.Column(db.Text)
    gender = db.Column(db.String(20))
    office_hours = db.Column(db.String(100))
    employment_status = db.Column(db.String(50), default='Full-time')
    designation = db.Column(db.String(100))
    specialization = db.Column(db.String(200))
    max_weekly_hours = db.Column(db.Integer, default=40)
    pan_number = db.Column(db.String(20))
    aadhaar_number = db.Column(db.String(20))
    experience_years = db.Column(db.Integer)
    date_of_birth = db.Column(db.Date)
    joining_date = db.Column(db.Date)
    qualification = db.Column(db.String(200))
    subject_expertise = db.Column(db.String(200))

    courses = db.relationship('Course', backref='teacher', lazy=True)
    tutored_students = db.relationship('Student', backref='tutor', lazy=True)
    leaves = db.relationship('TeacherLeave', backref='teacher', lazy=True, cascade="all, delete-orphan")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    department = db.Column(db.String(100))
    semester = db.Column(db.String(20))
    room = db.Column(db.String(50))
    capacity = db.Column(db.Integer)
    credits = db.Column(db.Integer)
    schedule_notes = db.Column(db.Text)
    level = db.Column(db.String(50))
    syllabus_url = db.Column(db.String(255))
    course_type = db.Column(db.String(50))
    academic_year = db.Column(db.String(20))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    prerequisites = db.Column(db.Text)
    learning_outcomes = db.Column(db.Text)

    sessions = db.relationship('CourseSession', backref='course', lazy=True, cascade="all, delete-orphan")
    grades = db.relationship('Grade', backref='course', lazy=True, cascade="all, delete-orphan")
    materials = db.relationship('CourseMaterial', backref='course', lazy=True, cascade="all, delete-orphan")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')

    def __repr__(self):
        return f"User('{self.username}', role='{self.role}')"

class UserPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('username', name='uix_userphoto_username'),)

    def __repr__(self):
        return f"UserPhoto('{self.username}', path='{self.file_path}')"

class CourseSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    location = db.Column(db.String(100))
    title = db.Column(db.String(120), nullable=True)
    attendances = db.relationship('Attendance', backref='session', lazy=True, cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint('course_id', 'session_date', name='uix_course_session_date'),)

    def __repr__(self):
        return f"CourseSession(course_id={self.course_id}, date='{self.session_date}', title='{self.title}')"

class CourseMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    material_type = db.Column(db.String(50))  # file, link, etc.
    content_url = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"CourseMaterial(title='{self.title}', type='{self.material_type}')"

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('course_session.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False) # present, absent, late, excused
    remarks = db.Column(db.String(200), nullable=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    marked_by = db.Column(db.String(120), nullable=True)
    # student relationship provided by backref in Student
    __table_args__ = (db.UniqueConstraint('session_id', 'student_id', name='uix_attendance_session_student'),)

    def __repr__(self):
        return f"Attendance(session_id={self.session_id}, student_id={self.student_id}, status='{self.status}')"

class TeacherLeave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    approved = db.Column(db.Boolean, default=True)
    approved_by = db.Column(db.String(80), nullable=True)

    def __repr__(self):
        return f"TeacherLeave(teacher_id={self.teacher_id}, {self.start_date}->{self.end_date}, approved={self.approved})"

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float)
    letter = db.Column(db.String(5))
    points = db.Column(db.Float)
    grade_letter = db.Column(db.String(5))
    comments = db.Column(db.Text)
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdmissionApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_by = db.Column(db.String(80))
    intake_year = db.Column(db.Integer)
    program = db.Column(db.String(100))
    notes = db.Column(db.Text)
    sslc_marks = db.Column(db.Integer)
    hsc_marks = db.Column(db.Integer)
    community = db.Column(db.String(50))
    religion = db.Column(db.String(50))
    nationality = db.Column(db.String(50))
    blood_group = db.Column(db.String(10))
    requested_course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    photo_path = db.Column(db.String(255))
    father_name = db.Column(db.String(100))
    mother_name = db.Column(db.String(100))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    previous_school = db.Column(db.String(255))
    guardian_name = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))
    guardian_email = db.Column(db.String(100))

    requested_course = db.relationship('Course', backref='applications', lazy=True)

    def __repr__(self):
        return f"AdmissionApplication('{self.name}', status='{self.status}')"

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    group = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"SystemSetting('{self.key}')"

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)
    actor_username = db.Column(db.String(80), nullable=True)
    actor_role = db.Column(db.String(20), nullable=True)
    target = db.Column(db.String(120), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"AuditLog(action='{self.action}', actor='{self.actor_username}', target='{self.target}')"

# Finance: Fees
class FeeAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), unique=True, nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    # student relationship provided by backref in Student
    currency = db.Column(db.String(10), nullable=False, default='USD')
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"FeeAccount(student_id={self.student_id}, balance={self.balance})"

class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=True)  # cash, card, online
    reference = db.Column(db.String(120), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    status = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f"FeePayment(student_id={self.student_id}, amount={self.amount}, method='{self.method}', paid_at='{self.paid_at}')"

# Finance: Budget
class BudgetCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f"BudgetCategory('{self.name}')"

class BudgetTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('budget_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # income or expense
    note = db.Column(db.String(200), nullable=True)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    category = db.relationship('BudgetCategory', backref=db.backref('transactions', lazy=True), lazy=True)

    def __repr__(self):
        return f"BudgetTransaction(category_id={self.category_id}, type='{self.type}', amount={self.amount})"

# Resources and Booking
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # lab, classroom, equipment
    capacity = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='available')
    tags = db.Column(db.String(200), nullable=True)
    condition = db.Column(db.String(20), nullable=True)
    maintenance_due = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"Resource('{self.name}', type='{self.type}')"

class ResourceBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    booked_by = db.Column(db.String(80), nullable=True)  # username
    resource = db.relationship('Resource', backref=db.backref('bookings', lazy=True), lazy=True)
    __table_args__ = (db.UniqueConstraint('resource_id', 'start_time', 'end_time', name='uix_resource_time_window'),)
    purpose = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')

    @property
    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() // 60)

    def __repr__(self):
        return f"ResourceBooking(resource_id={self.resource_id}, '{self.start_time}'->'{self.end_time}', title='{self.title}')"

# Booking approvals (avoid altering ResourceBooking schema)
class ResourceBookingApproval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('resource_booking.id'), nullable=False)
    approved = db.Column(db.Boolean, nullable=False, default=False)
    decided_by = db.Column(db.String(80), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    note = db.Column(db.String(200), nullable=True)
    booking = db.relationship('ResourceBooking', backref=db.backref('approvals', lazy=True), lazy=True)

    def __repr__(self):
        return f"ResourceBookingApproval(booking_id={self.booking_id}, approved={self.approved})"

# Parent access linking
class ParentStudentLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_username = db.Column(db.String(80), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    # student relationship provided by backref in Student
    __table_args__ = (db.UniqueConstraint('parent_username', 'student_id', name='uix_parent_student'),)

    def __repr__(self):
        return f"ParentStudentLink(parent='{self.parent_username}', student_id={self.student_id})"

# Invoices for student fees
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    issued_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='unpaid')  # unpaid, paid, partial
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    reference = db.Column(db.String(120), nullable=True)
    # student relationship provided by backref in Student
    waiver_amount = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, nullable=True)
    tax_percent = db.Column(db.Float, nullable=True)

    @property
    def is_overdue(self):
        return self.due_date is not None and datetime.utcnow().date() > self.due_date and self.status != 'paid'

    def __repr__(self):
        return f"Invoice(student_id={self.student_id}, amount_due={self.amount_due}, status='{self.status}')"

# Convenience display helpers
def student_display_name(student: Student) -> str:
    if getattr(student, 'roll_number', None):
        return f"{student.name} ({student.roll_number})"
    return student.name




