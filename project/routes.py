from flask import render_template, url_for, flash, redirect, request, jsonify, session, Response
from project import app, db
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from project.models import Student, Teacher, Course, User, CourseSession, Attendance, Grade, AdmissionApplication, AuditLog, FeeAccount, FeePayment, BudgetCategory, BudgetTransaction, Resource, ResourceBooking, ResourceBookingApproval, Invoice, ParentStudentLink, UserPhoto, Department, Semester, Subject, Exam, Notice
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func, extract
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from functools import wraps
import os
import uuid
import re
from datetime import datetime, timedelta
from io import StringIO
import csv

@app.route("/")
def index():
    return redirect(url_for('dashboard'))

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.path))
            role = session.get('role')
            if role not in roles:
                flash('You are not authorized to perform this action.', 'danger')
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --- Role-based CRUD policy ---
CRUD_PERMISSIONS = {
    'student': {
        'create': ['admin', 'staff'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'staff'],
        'delete': ['admin'],
    },
    'teacher': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'course': {
        'create': ['admin', 'staff', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'staff', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'course_session': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'grade': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'attendance': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'admission': {
        'create': ['admin', 'staff'],
        'read':   ['admin', 'staff'],
        'update': ['admin', 'staff'],
        'delete': ['admin'],
    },
    'department': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'semester': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'subject': {
        'create': ['admin', 'staff'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student'],
        'update': ['admin', 'staff'],
        'delete': ['admin'],
    },
    'fee': {
        'create': ['admin', 'staff'],
        'read':   ['admin', 'staff', 'student', 'parent'],
        'update': ['admin', 'staff'],
        'delete': ['admin'],
    },
    'timetable': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'audit': {
        'create': ['admin'],
        'read':   ['admin'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'user': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'delete': ['admin'],
    },
    'analytics': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'bulk_upload': {
        'create': ['admin'],
        'read':   ['admin'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'course_plan': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'workload': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'leave': {
        'create': ['admin', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher'],
        'update': ['admin', 'faculty', 'teacher'],
        'delete': ['admin'],
    },
    'parent_link': {
        'create': ['admin'],
        'read':   ['admin', 'staff'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'resource': {
        'create': ['admin'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin'],
        'delete': ['admin'],
    },
    'exam': {
        'create': ['admin', 'staff', 'faculty', 'teacher'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'staff', 'faculty', 'teacher'],
        'delete': ['admin', 'staff'],
    },
    'notice': {
        'create': ['admin', 'staff'],
        'read':   ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent'],
        'update': ['admin', 'staff'],
        'delete': ['admin', 'staff'],
    },
}

def crud_required(resource: str, action: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.path))
            role = session.get('role')
            allowed = CRUD_PERMISSIONS.get(resource, {}).get(action, [])
            if role not in allowed:
                flash('You are not authorized to perform this action.', 'danger')
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --- Helper Functions ---
def assign_tutor(student):
    """
    Auto-assigns a tutor to a student.
    Logic: 
    1. Find teachers in the same department as the student.
    2. Among those, find the one with the fewest tutees.
    3. If no teacher in the department, find the teacher with the fewest tutees overall.
    """
    teacher = None
    if student.department:
        # 1 & 2: Same department, fewest tutees
        teachers_in_dept = Teacher.query.filter_by(department=student.department).all()
        if teachers_in_dept:
            teacher = min(teachers_in_dept, key=lambda t: len(t.tutees))
    
    if not teacher:
        # 3: Fewest tutees overall
        all_teachers = Teacher.query.all()
        if all_teachers:
            teacher = min(all_teachers, key=lambda t: len(t.tutees))
    
    if teacher:
        student.tutor_id = teacher.id
        db.session.commit()
        return teacher
    return None

def get_recent_notices(role, user_email, limit=3):
    today = datetime.utcnow()
    query = Notice.query.filter((Notice.expires_at == None) | (Notice.expires_at > today))
    
    if role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        dept_id = student.department_id if student else None
        query = query.filter(
            (Notice.target_role.in_(['all', 'student'])) & 
            ((Notice.department_id == None) | (Notice.department_id == dept_id))
        )
    elif role in ['teacher', 'faculty']:
        teacher = Teacher.query.filter_by(email=user_email).first()
        dept_id = teacher.department_id if teacher else None
        query = query.filter(
            (Notice.target_role.in_(['all', 'teacher'])) & 
            ((Notice.department_id == None) | (Notice.department_id == dept_id))
        )
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        dept_ids = [s.department_id for s in students if s.department_id]
        query = query.filter(
            (Notice.target_role.in_(['all', 'parent'])) & 
            ((Notice.department_id == None) | (Notice.department_id.in_(dept_ids)))
        )
    
    return query.order_by(Notice.created_at.desc()).limit(limit).all()

# --- Dashboard ---
@app.route('/dashboard')
@crud_required('analytics', 'read')
def dashboard():
    # Student View
    if session.get('role') == 'student':
        student = Student.query.filter_by(email=session.get('user')).first()
        if student:
            # Fetch user photo
            photo = UserPhoto.query.filter_by(username=student.email).first()
            photo_url = url_for('static', filename=photo.file_path.lstrip('/')) if photo else None
            
            # 1. GPA
            grades = Grade.query.filter_by(student_id=student.id).all()
            total_pts = 0.0
            total_cr = 0
            for g in grades:
                # helper grade_points must be available in scope
                pts = g.points if g.points is not None else grade_points(g.letter)
                course = Course.query.get(g.course_id)
                cr = course.credits or 1
                total_pts += pts * cr
                total_cr += cr
            gpa = (total_pts / total_cr) if total_cr > 0 else None
            
            # 2. Attendance
            # Get all sessions for enrolled courses
            sessions_all = []
            for c in student.courses:
                sessions_all.extend(c.sessions)
            session_ids = [s.id for s in sessions_all]
            attendance_rate = 0.0
            attendance_counts = {'present': 0, 'absent': 0, 'late': 0, 'excused': 0}
            if session_ids:
                recs = Attendance.query.filter(Attendance.session_id.in_(session_ids), Attendance.student_id == student.id).all()
                if recs:
                    for r in recs:
                        if r.status in attendance_counts:
                            attendance_counts[r.status] += 1
                    present_late = attendance_counts['present'] + attendance_counts['late']
                    attendance_rate = (present_late / len(recs)) * 100.0
            
            # 3. Fees
            invoices = Invoice.query.filter_by(student_id=student.id).all()
            payments = FeePayment.query.filter_by(student_id=student.id).all()
            total_due = sum(inv.amount_due for inv in invoices)
            total_paid = sum(p.amount for p in payments)
            outstanding = max(total_due - total_paid, 0.0)
            
            # 4. Upcoming Sessions
            today = datetime.today().date()
            upcoming_sessions = []
            for c in student.courses:
                sess = CourseSession.query.filter_by(course_id=c.id).filter(CourseSession.session_date >= today).order_by(CourseSession.session_date.asc()).all()
                upcoming_sessions.extend(sess)
            upcoming_sessions.sort(key=lambda x: x.session_date)
            upcoming_sessions = upcoming_sessions[:5]

            recent_notices = get_recent_notices('student', session.get('user'))

            return render_template('student_dashboard.html', 
                                   title='Student Dashboard',
                                   student=student,
                                   gpa=gpa,
                                   attendance_rate=attendance_rate,
                                   attendance_counts=attendance_counts,
                                   outstanding=outstanding,
                                   upcoming_sessions=upcoming_sessions,
                                   photo_url=photo_url,
                                   recent_notices=recent_notices)

    # Faculty View
    if session.get('role') in ['faculty', 'teacher']:
        teacher = Teacher.query.filter_by(email=session.get('user')).first()
        if teacher:
            # Fetch user photo
            photo = UserPhoto.query.filter_by(username=teacher.email).first()
            photo_url = url_for('static', filename=photo.file_path.lstrip('/')) if photo else None
            
            # 1. Active Courses
            my_courses = Course.query.filter_by(teacher_id=teacher.id).all()
            active_courses_count = len(my_courses)
            
            # 2. Weekly Hours
            today = datetime.today().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            sessions_week = CourseSession.query.join(Course).filter(
                Course.teacher_id == teacher.id,
                CourseSession.session_date >= week_start,
                CourseSession.session_date <= week_end
            ).all()
            
            default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
            weekly_hours = len(sessions_week) * default_hours
            max_weekly_hours = int(app.config.get('TEACHER_MAX_HOURS_PER_WEEK', 30))
            
            # 3. Pending Leaves
            from project.models import TeacherLeave
            pending_leaves_count = TeacherLeave.query.filter_by(teacher_id=teacher.id, approved=False).count()
            
            # 4. Upcoming Sessions
            upcoming_sessions = CourseSession.query.join(Course).filter(
                Course.teacher_id == teacher.id,
                CourseSession.session_date >= today
            ).order_by(CourseSession.session_date.asc()).limit(5).all()
            
            # 5. Recent Sessions (for attendance)
            week_ago = today - timedelta(days=7)
            recent_sessions_objs = CourseSession.query.join(Course).filter(
                Course.teacher_id == teacher.id,
                CourseSession.session_date < today,
                CourseSession.session_date >= week_ago
            ).order_by(CourseSession.session_date.desc()).all()
            
            recent_sessions = []
            for s in recent_sessions_objs:
                recs = Attendance.query.filter_by(session_id=s.id).all()
                marked = len(recs) > 0
                present = sum(1 for r in recs if r.status == 'present')
                late = sum(1 for r in recs if r.status == 'late')
                total = len(recs)
                recent_sessions.append({
                    'id': s.id,
                    'course': s.course,
                    'session_date': s.session_date,
                    'title': s.title,
                    'attendance_marked': marked,
                    'stats': f"{present}P, {late}L / {total}" if marked else ""
                })

            recent_notices = get_recent_notices(session.get('role'), session.get('user'))

            return render_template('teacher_dashboard.html',
                                   title='Faculty Dashboard',
                                   teacher=teacher,
                                   active_courses_count=active_courses_count,
                                   weekly_hours=weekly_hours,
                                   max_weekly_hours=max_weekly_hours,
                                   pending_leaves_count=pending_leaves_count,
                                   upcoming_sessions=upcoming_sessions,
                                   recent_sessions=recent_sessions,
                                   photo_url=photo_url,
                                   recent_notices=recent_notices)

    # Parent View
    if session.get('role') == 'parent':
        user_email = session.get('user')
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        children_data = []
        for link in links:
            student = Student.query.get(link.student_id)
            if student:
                # 1. GPA
                grades = Grade.query.filter_by(student_id=student.id).all()
                total_pts = 0.0
                total_cr = 0
                for g in grades:
                    pts = g.points if g.points is not None else grade_points(g.letter)
                    course = Course.query.get(g.course_id)
                    cr = course.credits or 1
                    total_pts += pts * cr
                    total_cr += cr
                gpa = (total_pts / total_cr) if total_cr > 0 else None
                
                # 2. Attendance
                sessions_all = []
                for c in student.courses:
                    sessions_all.extend(c.sessions)
                session_ids = [s.id for s in sessions_all]
                attendance_rate = 0.0
                if session_ids:
                    recs = Attendance.query.filter(Attendance.session_id.in_(session_ids), Attendance.student_id == student.id).all()
                    if recs:
                        present_late = sum(1 for r in recs if r.status in ('present', 'late'))
                        attendance_rate = (present_late / len(recs)) * 100.0
                
                # 3. Fees
                invoices = Invoice.query.filter_by(student_id=student.id).all()
                payments = FeePayment.query.filter_by(student_id=student.id).all()
                total_due = sum(inv.amount_due for inv in invoices)
                total_paid = sum(p.amount for p in payments)
                outstanding = max(total_due - total_paid, 0.0)
                
                children_data.append({
                    'student': student,
                    'gpa': gpa,
                    'attendance_rate': attendance_rate,
                    'outstanding': outstanding
                })
        
        recent_notices = get_recent_notices('parent', session.get('user'))
        
        return render_template('parent_dashboard.html', 
                               title='Parent Dashboard',
                               children_data=children_data,
                               recent_notices=recent_notices)

    student_count = Student.query.count()
    teacher_count = Teacher.query.count()
    course_count = Course.query.count()

    # Finance & Admin insights
    pending_admissions = AdmissionApplication.query.filter_by(status='pending').count()
    
    # Calculate outstanding fees
    from sqlalchemy import func
    outstanding_total = db.session.query(func.sum(Invoice.amount_due - Invoice.paid_amount)).filter(Invoice.status != 'paid').scalar() or 0.0

    # Pending resource bookings (no approval record)
    pending_bookings = ResourceBooking.query.outerjoin(ResourceBookingApproval).filter(ResourceBookingApproval.id == None).count()

    # Institution-wide insights
    total_sessions = CourseSession.query.count()
    total_att = Attendance.query.count()
    present_late_att = Attendance.query.filter(Attendance.status.in_(('present', 'late'))).count()
    attendance_rate = (present_late_att / total_att * 100) if total_att else 0
    # Current week workload violations
    today = datetime.today().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    sessions_week = CourseSession.query.filter(CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).all()
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    teacher_day_hours = {}
    teacher_week_hours = {}
    for s in sessions_week:
        course = s.course
        date = s.session_date
        key_day = (course.teacher_id, date)
        teacher_day_hours[key_day] = teacher_day_hours.get(key_day, 0) + default_hours
        teacher_week_hours[course.teacher_id] = teacher_week_hours.get(course.teacher_id, 0) + default_hours
    max_day = int(app.config.get('TEACHER_MAX_HOURS_PER_DAY', 6))
    max_week = int(app.config.get('TEACHER_MAX_HOURS_PER_WEEK', 30))
    violations_day_count = sum(1 for (_, _), h in teacher_day_hours.items() if h > max_day)
    violations_week_count = sum(1 for _, h in teacher_week_hours.items() if h > max_week)
    today = datetime.today().date()
    upcoming = CourseSession.query.filter(CourseSession.session_date >= today).order_by(CourseSession.session_date.asc()).limit(10).all()
    recent = CourseSession.query.order_by(CourseSession.session_date.desc()).limit(10).all()
    
    recent_notices = get_recent_notices('admin', session.get('user'))

    return render_template('dashboard.html',
                           title='Dashboard',
                           student_count=student_count,
                           teacher_count=teacher_count,
                           course_count=course_count,
                           pending_admissions=pending_admissions,
                           outstanding_total=outstanding_total,
                           pending_bookings=pending_bookings,
                           total_sessions=total_sessions,
                           attendance_rate=attendance_rate,
                           violations_day_count=violations_day_count,
                           violations_week_count=violations_week_count,
                           upcoming=upcoming,
                           recent=recent,
                           recent_notices=recent_notices)

# --- Calendar ---
@app.route('/calendar')
def calendar():
    start_str = request.args.get('start', '').strip()
    end_str = request.args.get('end', '').strip()
    start = None
    end = None
    try:
        if start_str:
            start = datetime.strptime(start_str, '%Y-%m-%d').date()
        if end_str:
            end = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date filter.', 'danger')
    q = CourseSession.query
    role = session.get('role')
    user_email = session.get('user')
    
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        # Filter sessions for courses where any of the parent's children are enrolled
        q = q.filter(CourseSession.course.has(Course.students.any(Student.id.in_(student_ids))))
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student:
            # Filter sessions for courses where the student is enrolled
            q = q.filter(CourseSession.course.has(Course.students.any(Student.id == student.id)))
        else:
            q = q.filter(False)
    
    if start:
        q = q.filter(CourseSession.session_date >= start)
    if end:
        q = q.filter(CourseSession.session_date <= end)
    sessions = q.order_by(CourseSession.session_date.asc()).all()
    # Group by date
    grouped = {}
    for s in sessions:
        d = s.session_date
        grouped.setdefault(d, []).append(s)
    # Resource bookings (approved only)
    rb_start = datetime.combine(start, datetime.min.time()) if start else None
    rb_end = datetime.combine(end, datetime.max.time()) if end else None
    qb = ResourceBooking.query
    if rb_start:
        qb = qb.filter(ResourceBooking.start_time >= rb_start)
    if rb_end:
        qb = qb.filter(ResourceBooking.end_time <= rb_end)
    bookings = qb.order_by(ResourceBooking.start_time.asc()).all()
    grouped_rb = {}
    for b in bookings:
        appr = ResourceBookingApproval.query.filter_by(booking_id=b.id).order_by(ResourceBookingApproval.decided_at.desc()).first()
        if appr and appr.approved:
            d = b.start_time.date()
            grouped_rb.setdefault(d, []).append(b)
    # Sort keys
    dates = sorted(set(list(grouped.keys()) + list(grouped_rb.keys())))
    return render_template('calendar.html', title='Calendar', dates=dates, grouped=grouped, grouped_rb=grouped_rb, start=start_str, end=end_str)

# --- Notices / Notice Board ---
@app.route('/notices')
@crud_required('notice', 'read')
def notices():
    role = session.get('role')
    user_email = session.get('user')
    today = datetime.utcnow()
    
    query = Notice.query.filter((Notice.expires_at == None) | (Notice.expires_at > today))
    
    if role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        dept_id = student.department_id if student else None
        query = query.filter(
            (Notice.target_role.in_(['all', 'student'])) & 
            ((Notice.department_id == None) | (Notice.department_id == dept_id))
        )
    elif role == 'teacher' or role == 'faculty':
        teacher = Teacher.query.filter_by(email=user_email).first()
        dept_id = teacher.department_id if teacher else None
        query = query.filter(
            (Notice.target_role.in_(['all', 'teacher'])) & 
            ((Notice.department_id == None) | (Notice.department_id == dept_id))
        )
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        dept_ids = [s.department_id for s in students if s.department_id]
        query = query.filter(
            (Notice.target_role.in_(['all', 'parent'])) & 
            ((Notice.department_id == None) | (Notice.department_id.in_(dept_ids)))
        )
    
    notices_list = query.order_by(Notice.created_at.desc()).all()
    return render_template('notices.html', notices=notices_list, title='Notice Board')

@app.route('/notices/add', methods=['GET', 'POST'])
@crud_required('notice', 'create')
def add_notice():
    departments = Department.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        target_role = request.form.get('target_role', 'all')
        dept_id = request.form.get('department_id')
        expires_str = request.form.get('expires_at')
        
        expires_at = None
        if expires_str:
            expires_at = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M')
            
        new_notice = Notice(
            title=title,
            content=content,
            target_role=target_role,
            department_id=int(dept_id) if dept_id else None,
            created_by=session.get('user'),
            expires_at=expires_at
        )
        db.session.add(new_notice)
        db.session.commit()
        flash('Notice published successfully.', 'success')
        return redirect(url_for('notices'))
        
    return render_template('add_notice.html', departments=departments, title='Add Notice')

@app.route('/notices/<int:notice_id>/edit', methods=['GET', 'POST'])
@crud_required('notice', 'update')
def edit_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    departments = Department.query.all()
    if request.method == 'POST':
        notice.title = request.form.get('title')
        notice.content = request.form.get('content')
        notice.target_role = request.form.get('target_role', 'all')
        dept_id = request.form.get('department_id')
        expires_str = request.form.get('expires_at')
        
        notice.department_id = int(dept_id) if dept_id else None
        if expires_str:
            notice.expires_at = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M')
        else:
            notice.expires_at = None
            
        db.session.commit()
        flash('Notice updated successfully.', 'success')
        return redirect(url_for('notices'))
        
    return render_template('edit_notice.html', notice=notice, departments=departments, title='Edit Notice')

@app.route('/notices/<int:notice_id>/delete', methods=['POST'])
@crud_required('notice', 'delete')
def delete_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash('Notice deleted.', 'success')
    return redirect(url_for('notices'))

# --- Timetable (weekly summary) ---
@app.route('/timetable')
@crud_required('timetable', 'read')
def timetable():
    # week_start param (YYYY-MM-DD); default current week
    week_start_str = request.args.get('week_start', '').strip()
    teacher_id_param = request.args.get('teacher_id', '').strip()
    dept_id_param = request.args.get('department_id', '').strip()
    today = datetime.today().date()
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid week start date.', 'danger')
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    # Optional filter by teacher role or explicit teacher_id
    teacher_filter_id = None
    if teacher_id_param:
        try:
            teacher_filter_id = int(teacher_id_param)
        except Exception:
            teacher_filter_id = None
    if session.get('role') in ['teacher', 'faculty'] and not teacher_filter_id:
        t = Teacher.query.filter_by(email=session.get('user')).first()
        if t:
            teacher_filter_id = t.id
    q_sessions = CourseSession.query.filter(CourseSession.session_date >= week_start, CourseSession.session_date <= week_end)
    role = session.get('role')
    user_email = session.get('user')
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        dept_ids = [s.department_id for s in students if s.department_id]
        
        # Filter sessions for courses in the departments of the parent's children
        if dept_ids:
            q_sessions = q_sessions.join(Course).filter(Course.department_id.in_(dept_ids))
        else:
            q_sessions = q_sessions.filter(CourseSession.course.has(Course.students.any(Student.id.in_(student_ids))))
            
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student.department_id:
            q_sessions = q_sessions.join(Course).filter(Course.department_id == student.department_id)
        elif student:
            q_sessions = q_sessions.filter(CourseSession.course.has(Course.students.any(Student.id == student.id)))
    
    # Apply department filter for staff/admin/faculty
    elif dept_id_param:
        try:
            q_sessions = q_sessions.join(Course).filter(Course.department_id == int(dept_id_param))
        except ValueError:
            pass
    
    if teacher_filter_id:
        q_sessions = q_sessions.join(Course).filter(Course.teacher_id == teacher_filter_id)
    sessions = q_sessions.order_by(CourseSession.session_date.asc()).all()
    # Aggregate hours per teacher per day
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    teacher_day_hours = {}
    teacher_week_hours = {}
    items = []
    for s in sessions:
        course = s.course
        teacher = course.teacher
        date = s.session_date
        key_day = (teacher.id, date)
        teacher_day_hours[key_day] = teacher_day_hours.get(key_day, 0) + default_hours
        teacher_week_hours[teacher.id] = teacher_week_hours.get(teacher.id, 0) + default_hours
        items.append({'date': date, 'course': course, 'teacher': teacher, 'title': s.title, 'hours': default_hours})
    max_day = int(app.config.get('TEACHER_MAX_HOURS_PER_DAY', 6))
    max_week = int(app.config.get('TEACHER_MAX_HOURS_PER_WEEK', 30))
    # Flags
    violations_day = {(tid, d): h for (tid, d), h in teacher_day_hours.items() if h > max_day}
    violations_week = {tid: h for tid, h in teacher_week_hours.items() if h > max_week}
    # Teachers index
    teachers = {}
    for s in sessions:
        teachers[s.course.teacher.id] = s.course.teacher
    
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('timetable.html',
                           title='Timetable',
                           week_start=week_start,
                           week_end=week_end,
                           items=items,
                           teachers=teachers,
                           departments=departments,
                           selected_dept_id=dept_id_param,
                           violations_day=violations_day,
                           violations_week=violations_week,
                           max_day=max_day,
                           max_week=max_week,
                           default_hours=default_hours)

@app.route('/timetable/generate', methods=['POST'])
@crud_required('timetable', 'update')
def timetable_generate():
    week_start_str = request.form.get('week_start', '').strip()
    today = datetime.today().date()
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid week start date.', 'danger')
            return redirect(url_for('timetable'))
    else:
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    allow_weekend = bool(app.config.get('ALLOW_WEEKEND_SESSIONS', False))
    max_course_week = int(app.config.get('COURSE_MAX_SESSIONS_PER_WEEK', 5))
    max_teacher_day = int(app.config.get('TEACHER_MAX_SESSIONS_PER_DAY', 3))
    max_teacher_week = int(app.config.get('TEACHER_MAX_SESSIONS_PER_WEEK', 15))
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    require_approved = bool(app.config.get('LEAVE_APPROVAL_REQUIRED', True))
    # Lab/Project config
    lab_kw = (app.config.get('LAB_SESSION_KEYWORD') or 'Lab')
    proj_kw = (app.config.get('PROJECT_SESSION_KEYWORD') or 'Project')
    lab_every = int(app.config.get('LAB_GENERATE_EVERY_N', 0))
    proj_every = int(app.config.get('PROJECT_GENERATE_EVERY_M', 0))
    lab_gap = int(app.config.get('LAB_MIN_SPACING_DAYS', 3))
    proj_gap = int(app.config.get('PROJECT_MIN_SPACING_DAYS', 7))

    created = 0
    skipped = 0
    # Iterate days, then courses to distribute load
    try:
        db.create_all()
        from project.models import TeacherLeave
        days = [week_start + timedelta(days=i) for i in range(7)]
        courses = Course.query.order_by(Course.teacher_id.asc()).all()
        for d in days:
            if not allow_weekend and d.weekday() >= 5:
                continue
            # Precompute teacher day/week counts
            for course in courses:
                t = course.teacher
                # Course weekly cap remaining
                week_count_course = CourseSession.query.\
                    filter(CourseSession.course_id == course.id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
                if week_count_course >= max_course_week:
                    continue
                # Teacher day/week caps
                teacher_day_count = CourseSession.query.join(Course).\
                    filter(Course.teacher_id == t.id, CourseSession.session_date == d).count()
                if teacher_day_count >= max_teacher_day:
                    continue
                teacher_week_count = CourseSession.query.join(Course).\
                    filter(Course.teacher_id == t.id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
                if teacher_week_count >= max_teacher_week:
                    continue
                # Teacher leave window
                leave_q = TeacherLeave.query.filter_by(teacher_id=t.id).\
                    filter(TeacherLeave.start_date <= d, TeacherLeave.end_date >= d)
                if require_approved:
                    leave_q = leave_q.filter(TeacherLeave.approved == True)
                if leave_q.first():
                    skipped += 1
                    continue
                # Avoid duplicate course session same day
                if CourseSession.query.filter_by(course_id=course.id, session_date=d).first():
                    continue
                # Title allocation (optional lab/project rotation)
                total_sessions = CourseSession.query.filter_by(course_id=course.id).count()
                title = None
                # Prefer project allocation if both trigger
                if proj_every > 0 and ((total_sessions + 1) % proj_every == 0):
                    # Check spacing
                    last_proj = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + proj_kw + '%')).order_by(CourseSession.session_date.desc()).first()
                    if not last_proj or (d - last_proj.session_date).days >= proj_gap:
                        title = proj_kw
                if title is None and lab_every > 0 and ((total_sessions + 1) % lab_every == 0):
                    last_lab = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + lab_kw + '%')).order_by(CourseSession.session_date.desc()).first()
                    if not last_lab or (d - last_lab.session_date).days >= lab_gap:
                        title = lab_kw
                if title is None:
                    title = 'Lecture'
                s = CourseSession(course_id=course.id, session_date=d, title=title)
                db.session.add(s)
                created += 1
        db.session.commit()
        # Audit log
        try:
            log = AuditLog(
                action='timetable_generate',
                actor_username=session.get('user') or 'system',
                actor_role=session.get('role'),
                target='week',
                details=f"start={week_start.isoformat()},created={created},skipped={skipped}"
            )
            db.session.add(log)
            db.session.commit()
        except Exception as _e:
            logger.warning(f"Failed to write audit log for timetable_generate: {_e}")
        flash(f'Timetable generated: created {created} sessions; skipped {skipped}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to generate timetable: {str(e)}', 'danger')
    return redirect(url_for('timetable', week_start=week_start.isoformat()))

# --- Course Planning Summary ---
@app.route('/courses/<int:course_id>/plan')
@crud_required('course_plan', 'read')
def course_plan(course_id):
    course = Course.query.get_or_404(course_id)
    credits = course.credits or 0
    hours_per_credit = int(app.config.get('HOURS_PER_CREDIT', 15))
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    required_hours = credits * hours_per_credit
    required_sessions = (required_hours // default_hours) + (1 if required_hours % default_hours else 0)
    # Actual scheduled
    sessions = CourseSession.query.filter_by(course_id=course.id).order_by(CourseSession.session_date.asc()).all()
    actual_sessions = len(sessions)
    actual_hours = actual_sessions * default_hours
    status = 'on_track'
    if actual_hours < required_hours:
        status = 'behind'
    elif actual_hours > required_hours:
        status = 'ahead'
    return render_template('course_plan.html',
                           title='Course Plan',
                           course=course,
                           credits=credits,
                           hours_per_credit=hours_per_credit,
                           default_hours=default_hours,
                           required_hours=required_hours,
                           required_sessions=required_sessions,
                           actual_hours=actual_hours,
                           actual_sessions=actual_sessions,
                           status=status,
                           sessions=sessions,
                           suggestions=None)

@app.route('/courses/<int:course_id>/plan/suggest')
@crud_required('course_plan', 'read')
def course_plan_suggest(course_id):
    course = Course.query.get_or_404(course_id)
    teacher = course.teacher
    credits = course.credits or 0
    hours_per_credit = int(app.config.get('HOURS_PER_CREDIT', 15))
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    required_hours = credits * hours_per_credit
    required_sessions = (required_hours // default_hours) + (1 if required_hours % default_hours else 0)
    sessions = CourseSession.query.filter_by(course_id=course.id).order_by(CourseSession.session_date.asc()).all()
    actual_sessions = len(sessions)
    actual_hours = actual_sessions * default_hours
    remaining = max(0, required_sessions - actual_sessions)
    if remaining <= 0:
        flash('Course already meets or exceeds required sessions.', 'info')
        status = 'ahead' if actual_hours > required_hours else 'on_track'
        return render_template('course_plan.html',
                               title='Course Plan',
                               course=course,
                               credits=credits,
                               hours_per_credit=hours_per_credit,
                               default_hours=default_hours,
                               required_hours=required_hours,
                               required_sessions=required_sessions,
                               actual_hours=actual_hours,
                               actual_sessions=actual_sessions,
                               status=status,
                               sessions=sessions,
                               suggestions=[])
    # Governance caps
    max_course_week = int(app.config.get('COURSE_MAX_SESSIONS_PER_WEEK', 5))
    max_teacher_day = int(app.config.get('TEACHER_MAX_SESSIONS_PER_DAY', 3))
    max_teacher_week = int(app.config.get('TEACHER_MAX_SESSIONS_PER_WEEK', 15))
    allow_weekend = bool(app.config.get('ALLOW_WEEKEND_SESSIONS', False))
    # Start scheduling from next day after last session or today
    today = datetime.today().date()
    start_date = today
    if sessions:
        start_date = max(today, sessions[-1].session_date + timedelta(days=1))
    suggestions = []
    d = start_date
    safety_counter = 0
    while remaining > 0 and safety_counter < 365:  # limit search to ~1 year
        safety_counter += 1
        weekday = d.weekday()  # 0=Mon..6=Sun
        if not allow_weekend and weekday >= 5:
            d += timedelta(days=1)
            continue
        # Determine week window
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)
        # Counts for governance checks
        course_week_count = CourseSession.query.filter_by(course_id=course.id).\
            filter(CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
        teacher_day_count = CourseSession.query.join(Course).\
            filter(Course.teacher_id == teacher.id, CourseSession.session_date == d).count()
        teacher_week_count = CourseSession.query.join(Course).\
            filter(Course.teacher_id == teacher.id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
        # Skip if caps would be exceeded
        if course_week_count >= max_course_week or teacher_day_count >= max_teacher_day or teacher_week_count >= max_teacher_week:
            d += timedelta(days=1)
            continue
        # Avoid duplicate session on same date for this course
        exists_same_day = CourseSession.query.filter_by(course_id=course.id, session_date=d).first() is not None
        if exists_same_day:
            d += timedelta(days=1)
            continue
        suggestions.append({'date': d})
        remaining -= 1
        d += timedelta(days=1)
    status = 'behind' if actual_hours < required_hours else ('ahead' if actual_hours > required_hours else 'on_track')
    return render_template('course_plan.html',
                           title='Course Plan',
                           course=course,
                           credits=credits,
                           hours_per_credit=hours_per_credit,
                           default_hours=default_hours,
                           required_hours=required_hours,
                           required_sessions=required_sessions,
                           actual_hours=actual_hours,
                           actual_sessions=actual_sessions,
                           status=status,
                           sessions=sessions,
                           suggestions=suggestions)

@app.route('/courses/<int:course_id>/plan/apply', methods=['POST'])
@crud_required('course_plan', 'update')
def course_plan_apply(course_id):
    course = Course.query.get_or_404(course_id)
    teacher = course.teacher
    credits = course.credits or 0
    hours_per_credit = int(app.config.get('HOURS_PER_CREDIT', 15))
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    required_hours = credits * hours_per_credit
    required_sessions = (required_hours // default_hours) + (1 if required_hours % default_hours else 0)
    sessions = CourseSession.query.filter_by(course_id=course.id).order_by(CourseSession.session_date.asc()).all()
    actual_sessions = len(sessions)
    remaining = max(0, required_sessions - actual_sessions)
    if remaining <= 0:
        flash('No remaining sessions required by plan.', 'info')
        return redirect(url_for('course_plan', course_id=course.id))
    # Governance caps
    max_course_week = int(app.config.get('COURSE_MAX_SESSIONS_PER_WEEK', 5))
    max_teacher_day = int(app.config.get('TEACHER_MAX_SESSIONS_PER_DAY', 3))
    max_teacher_week = int(app.config.get('TEACHER_MAX_SESSIONS_PER_WEEK', 15))
    allow_weekend = bool(app.config.get('ALLOW_WEEKEND_SESSIONS', False))
    # Lab/Project spacing
    lab_kw = (app.config.get('LAB_SESSION_KEYWORD') or 'Lab').lower()
    proj_kw = (app.config.get('PROJECT_SESSION_KEYWORD') or 'Project').lower()
    lab_gap = int(app.config.get('LAB_MIN_SPACING_DAYS', 3))
    proj_gap = int(app.config.get('PROJECT_MIN_SPACING_DAYS', 7))
    try:
        db.create_all()
        from project.models import TeacherLeave
        today = datetime.today().date()
        start_date = today
        if sessions:
            start_date = max(today, sessions[-1].session_date + timedelta(days=1))
        created = 0
        d = start_date
        safety_counter = 0
        while remaining > 0 and safety_counter < 365:
            safety_counter += 1
            if not allow_weekend and d.weekday() >= 5:
                d += timedelta(days=1)
                continue
            # Week window
            week_start = d - timedelta(days=d.weekday())
            week_end = week_start + timedelta(days=6)
            # Caps
            course_week_count = CourseSession.query.filter_by(course_id=course.id).\
                filter(CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
            if course_week_count >= max_course_week:
                d += timedelta(days=1)
                continue
            teacher_day_count = CourseSession.query.join(Course).\
                filter(Course.teacher_id == teacher.id, CourseSession.session_date == d).count()
            if teacher_day_count >= max_teacher_day:
                d += timedelta(days=1)
                continue
            teacher_week_count = CourseSession.query.join(Course).\
                filter(Course.teacher_id == teacher.id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
            if teacher_week_count >= max_teacher_week:
                d += timedelta(days=1)
                continue
            # Leave
            leave_q = TeacherLeave.query.filter_by(teacher_id=teacher.id).\
                filter(TeacherLeave.start_date <= d, TeacherLeave.end_date >= d)
            if bool(app.config.get('LEAVE_APPROVAL_REQUIRED', True)):
                leave_q = leave_q.filter(TeacherLeave.approved == True)
            if leave_q.first():
                d += timedelta(days=1)
                continue
            # Avoid duplicate
            if CourseSession.query.filter_by(course_id=course.id, session_date=d).first():
                d += timedelta(days=1)
                continue
            # Title with spacing checks
            title = 'Lecture'
            last_lab = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + lab_kw + '%')).order_by(CourseSession.session_date.desc()).first()
            if last_lab and (d - last_lab.session_date).days >= lab_gap:
                title = app.config.get('LAB_SESSION_KEYWORD') or 'Lab'
            last_proj = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + proj_kw + '%')).order_by(CourseSession.session_date.desc()).first()
            if last_proj and (d - last_proj.session_date).days >= proj_gap:
                title = app.config.get('PROJECT_SESSION_KEYWORD') or 'Project'
            snew = CourseSession(course_id=course.id, session_date=d, title=title)
            db.session.add(snew)
            created += 1
            remaining -= 1
            d += timedelta(days=1)
        db.session.commit()
        # Audit
        try:
            log = AuditLog(
                action='course_plan_apply',
                actor_username=session.get('user') or 'system',
                actor_role=session.get('role'),
                target=course.name,
                details=f"created={created}"
            )
            db.session.add(log)
            db.session.commit()
        except Exception as _e:
            logger.warning(f"Failed to write audit log course_plan_apply: {_e}")
        flash(f'Applied plan: created {created} sessions.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to apply plan: {str(e)}', 'danger')
    return redirect(url_for('course_plan', course_id=course.id))

# --- Workload Dashboard ---
@app.route('/workload')
@crud_required('workload', 'read')
def workload():
    week_start_str = request.args.get('week_start', '').strip()
    today = datetime.today().date()
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid week start date.', 'danger')
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    sessions = CourseSession.query.filter(CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).all()
    default_hours = int(app.config.get('SESSION_DEFAULT_DURATION_HOURS', 1))
    target = int(app.config.get('WORKLOAD_TARGET_WEEKLY_HOURS', 24))
    tol = int(app.config.get('WORKLOAD_TOLERANCE_HOURS', 4))
    per_teacher = {}
    for s in sessions:
        t = s.course.teacher
        per_teacher.setdefault(t.id, {'teacher': t, 'hours': 0, 'sessions': 0})
        per_teacher[t.id]['hours'] += default_hours
        per_teacher[t.id]['sessions'] += 1
    for t in Teacher.query.all():
        per_teacher.setdefault(t.id, {'teacher': t, 'hours': 0, 'sessions': 0})
    items = []
    for tid, info in per_teacher.items():
        hours = info['hours']
        status = 'fair'
        if hours < (target - tol):
            status = 'under'
        elif hours > (target + tol):
            status = 'over'
        items.append({'teacher': info['teacher'], 'hours': hours, 'sessions': info['sessions'], 'status': status})
    items.sort(key=lambda x: (x['status'] != 'under', -x['hours']))
    return render_template('workload.html', title='Workload', week_start=week_start, week_end=week_end, items=items, target=target, tolerance=tol, default_hours=default_hours)

# --- Teacher Leave Management ---
@app.route('/teachers/<int:teacher_id>/leave', methods=['GET', 'POST'])
@crud_required('leave', 'read')
def teacher_leave(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    from project.models import TeacherLeave
    if request.method == 'POST':
        start_str = request.form.get('start_date', '').strip()
        end_str = request.form.get('end_date', '').strip()
        reason = request.form.get('reason', '').strip()
        approved_val = request.form.get('approved')
        try:
            start_d = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_d = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid dates.', 'danger')
            leaves = TeacherLeave.query.filter_by(teacher_id=teacher_id).order_by(TeacherLeave.start_date.desc()).all()
            return render_template('teacher_leave.html', title='Teacher Leave', teacher=teacher, leaves=leaves)
        if end_d < start_d:
            flash('End date must be after start date.', 'danger')
            leaves = TeacherLeave.query.filter_by(teacher_id=teacher_id).order_by(TeacherLeave.start_date.desc()).all()
            return render_template('teacher_leave.html', title='Teacher Leave', teacher=teacher, leaves=leaves)
        approved = True if approved_val in ('on', 'true', '1') else False
        try:
            leave = TeacherLeave(teacher_id=teacher_id, start_date=start_d, end_date=end_d, reason=reason or None, approved=approved)
            if approved:
                leave.approved_by = session.get('user')
            db.session.add(leave)
            db.session.commit()
            flash('Leave recorded.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to record leave: {str(e)}', 'danger')
    leaves = TeacherLeave.query.filter_by(teacher_id=teacher_id).order_by(TeacherLeave.start_date.desc()).all()
    return render_template('teacher_leave.html', title='Teacher Leave', teacher=teacher, leaves=leaves)

@app.route('/teachers/<int:teacher_id>/leave/<int:leave_id>/delete', methods=['POST'])
@crud_required('leave', 'delete')
def delete_teacher_leave(teacher_id, leave_id):
    from project.models import TeacherLeave
    leave = TeacherLeave.query.get_or_404(leave_id)
    if leave.teacher_id != teacher_id:
        flash('Leave entry mismatch.', 'danger')
        return redirect(url_for('teacher_leave', teacher_id=teacher_id))
    db.session.delete(leave)
    db.session.commit()
    flash('Leave entry deleted.', 'success')
    return redirect(url_for('teacher_leave', teacher_id=teacher_id))

# --- Teacher Performance ---
@app.route('/teachers/<int:teacher_id>/performance')
@crud_required('analytics', 'read')
def teacher_performance(teacher_id):
    if not app.config.get('PERFORMANCE_ENABLED', True):
        flash('Performance reporting is disabled.', 'warning')
        return redirect(url_for('teachers'))
    teacher = Teacher.query.get_or_404(teacher_id)
    courses = Course.query.filter_by(teacher_id=teacher_id).all()
    sessions = CourseSession.query.join(Course).filter(Course.teacher_id == teacher_id).order_by(CourseSession.session_date.asc()).all()
    total_sessions = len(sessions)
    total_attendance = 0
    present_late_count = 0
    for s in sessions:
        records = Attendance.query.filter_by(session_id=s.id).all()
        total_attendance += len(records)
        present_late_count += len([r for r in records if r.status in ('present', 'late')])
    attendance_rate = (present_late_count / total_attendance * 100.0) if total_attendance else None
    min_sessions = int(app.config.get('PERFORMANCE_MIN_SESSIONS_FOR_REPORT', 5))
    return render_template('teacher_performance.html', title='Performance', teacher=teacher, courses=courses, total_sessions=total_sessions, attendance_rate=attendance_rate, min_sessions=min_sessions)

# --- IDE Preview Helper APIs to avoid timeouts ---
@app.route('/api/getThemeColors', methods=['GET'])
def api_get_theme_colors():
    return jsonify({
        "primary": "#007bff",
        "secondary": "#6c757d",
        "success": "#28a745",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "info": "#17a2b8",
        "light": "#f8f9fa",
        "dark": "#343a40"
    }), 200

@app.route('/api/getLanguageText', methods=['GET'])
def api_get_language_text():
    return jsonify({
        "language": "en",
        "strings": {}
    }), 200

@app.route('/api/getWorkspacePath', methods=['GET'])
def api_get_workspace_path():
    try:
        path = os.getcwd()
    except Exception:
        path = ''
    return jsonify({"workspacePath": path}), 200

@app.route('/api/setIsSelect', methods=['POST'])
def api_set_is_select():
    # Accepts any payload; used only to acknowledge selection state in preview
    return jsonify({"ok": True}), 200

@app.route('/api/webviewClick', methods=['GET', 'POST'])
def api_webview_click():
    # Acknowledge IDE webview click events to avoid preview timeouts
    return jsonify({"ok": True}), 200

# --- Admissions ---
@app.route('/admissions')
@crud_required('admission', 'read')
def admissions():
    q = request.args.get('q', '').strip()
    query = AdmissionApplication.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(AdmissionApplication.name.ilike(like), AdmissionApplication.email.ilike(like)))
    apps = query.order_by(AdmissionApplication.applied_at.desc()).all()
    return render_template('admissions.html', title='Admissions', applications=apps, q=q)

@app.route('/add_admission', methods=['GET', 'POST'])
@app.route('/admissions/add', methods=['GET', 'POST'])
def add_admission():
    if request.method == 'POST':
        # Removed registration_number from form - it's auto-generated as temp
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        dob_str = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        sslc_str = request.form.get('sslc_marks', '').strip()
        hsc_str = request.form.get('hsc_marks', '').strip()
        community = request.form.get('community', '').strip()
        religion = request.form.get('religion', '').strip()
        father_name = request.form.get('father_name', '').strip()
        mother_name = request.form.get('mother_name', '').strip()
        previous_school = request.form.get('previous_school', '').strip()
        requested_department_id = request.form.get('requested_department', '').strip()
        aadhar_no = request.form.get('aadhar_no', '').strip()
        community_cert_no = request.form.get('community_cert_no', '').strip()
        annual_income_str = request.form.get('annual_income', '').strip()
        income_cert_no = request.form.get('income_cert_no', '').strip()

        if not name or not email:
            flash('Name and email are required.', 'danger')
            departments = Department.query.order_by(Department.name.asc()).all()
            return render_template('add_admission.html', title='New Application', departments=departments)

        # Generate temporary registration number: TEMP + Year + 4-digit random/sequence
        year = datetime.utcnow().year
        import random
        temp_reg = f"TEMP{year}{random.randint(1000, 9999)}"
        # Ensure uniqueness
        while AdmissionApplication.query.filter_by(registration_number=temp_reg).first():
            temp_reg = f"TEMP{year}{random.randint(1000, 9999)}"

        annual_income = None
        if annual_income_str:
            try:
                annual_income = float(annual_income_str)
            except ValueError:
                flash('Invalid annual income.', 'danger')
                departments = Department.query.order_by(Department.name.asc()).all()
                return render_template('add_admission.html', title='New Application', departments=departments)

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                departments = Department.query.order_by(Department.name.asc()).all()
                return render_template('add_admission.html', title='New Application', departments=departments)
        sslc = None
        hsc = None
        if sslc_str:
            try:
                sslc = int(sslc_str)
            except ValueError:
                flash('Invalid SSLC marks.', 'danger')
                departments = Department.query.order_by(Department.name.asc()).all()
                return render_template('add_admission.html', title='New Application', departments=departments)
        if hsc_str:
            try:
                hsc = int(hsc_str)
            except ValueError:
                flash('Invalid HSC marks.', 'danger')
                departments = Department.query.order_by(Department.name.asc()).all()
                return render_template('add_admission.html', title='New Application', departments=departments)
        
        dept_id = None
        if requested_department_id:
            try:
                dept_id = int(requested_department_id)
            except ValueError:
                dept_id = None
        rd = Department.query.get(dept_id) if dept_id else None
        
        photo_file = request.files.get('photo')
        photo_path = None
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            ext = os.path.splitext(filename)[1].lower()
            unique = uuid.uuid4().hex + ext
            upload_dir = app.config.get('ADMISSION_PHOTOS_DIR')
            try:
                os.makedirs(upload_dir, exist_ok=True)
            except Exception:
                pass
            save_path = os.path.join(upload_dir, unique)
            photo_file.save(save_path)
            rel_dir = os.path.relpath(upload_dir, os.path.join(os.path.dirname(__file__), 'static'))
            photo_path = os.path.join(rel_dir, unique).replace('\\', '/')
        nationality = request.form.get('nationality')
        blood_group = request.form.get('blood_group')
        guardian_name = request.form.get('guardian_name')
        guardian_phone = request.form.get('guardian_phone')
        guardian_email = request.form.get('guardian_email')
        app_obj = AdmissionApplication(
            registration_number=temp_reg,
            name=name,
            email=email,
            phone=phone or None,
            date_of_birth=dob,
            gender=gender or None,
            address=address or None,
            status='pending',
            applied_at=datetime.utcnow(),
            notes=notes or None,
            sslc_marks=sslc,
            hsc_marks=hsc,
            community=community or None,
            religion=religion or None,
            nationality=nationality or None,
            blood_group=blood_group or None,
            father_name=father_name or None,
            mother_name=mother_name or None,
            emergency_contact_name=request.form.get('emergency_contact_name') or None,
            emergency_contact_phone=request.form.get('emergency_contact_phone') or None,
            previous_school=previous_school or None,
            guardian_name=guardian_name or None,
            guardian_phone=guardian_phone or None,
            guardian_email=guardian_email or None,
            requested_course_id=None, # Clear old course id
            department_id=rd.id if rd else None, # Use department_id instead
            photo_path=photo_path,
            aadhar_no=aadhar_no,
            community_cert_no=community_cert_no,
            annual_income=annual_income,
            income_cert_no=income_cert_no,
            temp_password=uuid.uuid4().hex[:8]  # Generate temporary password
        )
        db.session.add(app_obj)
        db.session.commit()
        flash(f'Application submitted. Your temporary registration number is {temp_reg}. Use your email to check status.', 'success')
        return redirect(url_for('admission_status'))
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('add_admission.html', title='New Application', departments=departments)

@app.route('/admissions/<int:app_id>')
@crud_required('admission', 'read')
def view_admission(app_id):
    app_obj = AdmissionApplication.query.get_or_404(app_id)
    return render_template('view_admission.html', title='View Application', application=app_obj)

@app.route('/admissions/calculate_merit', methods=['POST'])
@crud_required('admission', 'update')
def calculate_merit():
    apps = AdmissionApplication.query.filter_by(status='pending').all()
    for app_obj in apps:
        # Calculate merit score: (SSLC + HSC) / 2
        sslc = app_obj.sslc_marks or 0
        hsc = app_obj.hsc_marks or 0
        app_obj.merit_score = (sslc + hsc) / 2.0
    db.session.commit()
    flash('Merit scores calculated for all pending applications.', 'success')
    return redirect(url_for('admissions'))

@app.route('/admissions/<int:app_id>/verify', methods=['POST'])
@login_required
@crud_required('admission', 'update')
def verify_documents(app_id):
    app_obj = AdmissionApplication.query.get_or_404(app_id)
    app_obj.documents_verified = True
    db.session.commit()
    flash('Documents verified successfully.', 'success')
    return redirect(url_for('view_admission', app_id=app_id))

@app.route('/admissions/<int:app_id>/allot', methods=['POST'])
@login_required
@crud_required('admission', 'update')
def allot_seat(app_id):
    app_obj = AdmissionApplication.query.get_or_404(app_id)
    if not app_obj.documents_verified:
        flash('Verify documents first.', 'warning')
        return redirect(url_for('view_admission', app_id=app_id))
    
    app_obj.seat_allotted = True
    db.session.commit()
    flash('Seat allotted successfully.', 'success')
    return redirect(url_for('view_admission', app_id=app_id))

@app.route('/admissions/<int:app_id>/approve', methods=['POST'])
@login_required
@crud_required('admission', 'update')
def approve_admission(app_id):
    app_obj = AdmissionApplication.query.get_or_404(app_id)
    if not app_obj.documents_verified:
        flash('Cannot approve application. Documents must be verified first.', 'warning')
        return redirect(url_for('view_admission', app_id=app_id))
    if app_obj.status == 'approved':
        flash('Already approved.', 'info')
        return redirect(url_for('admissions'))
    
    final_registration_number = request.form.get('final_registration_number', '').strip()
    if not final_registration_number:
        flash('Final registration number is required for approval.', 'danger')
        return redirect(url_for('view_admission', app_id=app_id))

    # Check if final registration number is already taken
    existing_reg = Student.query.filter_by(registration_number=final_registration_number).first()
    if existing_reg:
        flash(f'Registration number {final_registration_number} is already assigned to another student.', 'danger')
        return redirect(url_for('view_admission', app_id=app_id))

    existing = Student.query.filter_by(email=app_obj.email).first()
    if existing:
        student = existing
        student.registration_number = final_registration_number
    else:
        student = Student(
            registration_number=final_registration_number,
            name=app_obj.name, 
            email=app_obj.email, 
            phone=app_obj.phone or '', 
            roll_number=f"STU{app_obj.id:04d}", 
            address=app_obj.address, 
            date_of_birth=app_obj.date_of_birth,
            gender=app_obj.gender,
            department_id=getattr(app_obj, 'department_id', None),
            nationality=app_obj.nationality,
            blood_group=app_obj.blood_group,
            religion=app_obj.religion,
            community=app_obj.community,
            sslc_marks=app_obj.sslc_marks,
            hsc_marks=app_obj.hsc_marks,
            father_name=app_obj.father_name,
            mother_name=app_obj.mother_name,
            emergency_contact_name=app_obj.emergency_contact_name,
            emergency_contact_phone=app_obj.emergency_contact_phone,
            previous_school=app_obj.previous_school,
            guardian_name=app_obj.guardian_name,
            guardian_phone=app_obj.guardian_phone,
            guardian_email=app_obj.guardian_email,
            aadhar_no=app_obj.aadhar_no,
            community_cert_no=app_obj.community_cert_no,
            annual_income=app_obj.annual_income,
            income_cert_no=app_obj.income_cert_no,
            temp_password=app_obj.temp_password,
            admission_date=datetime.utcnow().date(),
            status='active'
        )
        # Seat Allotment
        if app_obj.requested_course_id:
            course = Course.query.get(app_obj.requested_course_id)
            if course:
                student.courses.append(course)
                app_obj.seat_allotted = True

        db.session.add(student)
        db.session.flush()  # get id

        # Fee Payment: Create initial invoice
        invoice = Invoice(
            student_id=student.id,
            amount_due=1000.0,
            description="Admission Fee",
            due_date=datetime.utcnow().date(),
            status='unpaid'
        )
        db.session.add(invoice)

    app_obj.status = 'approved'
    app_obj.student_id = student.id
    app_obj.registration_number = final_registration_number # Update app record with final reg no
    app_obj.processed_by = session.get('user')
    db.session.commit()
    flash(f'Application approved. Student created with Registration No: {final_registration_number}', 'success')
    return redirect(url_for('admissions'))

@app.route('/admissions/<int:app_id>/reject', methods=['POST'])
@crud_required('admission', 'update')
def reject_admission(app_id):
    app_obj = AdmissionApplication.query.get_or_404(app_id)
    if app_obj.status == 'rejected':
        flash('Already rejected.', 'info')
    else:
        reason = request.form.get('reason', '').strip()
        app_obj.status = 'rejected'
        if reason:
            app_obj.notes = reason
        app_obj.processed_by = session.get('user')
        db.session.commit()
        flash('Application rejected.', 'success')
    return redirect(url_for('admissions'))

@app.route('/admission_status', methods=['GET', 'POST'])
def admission_status():
    app_obj = None
    email = request.form.get('email', '').strip() if request.method == 'POST' else request.args.get('email', '').strip()
    if email:
        app_obj = AdmissionApplication.query.filter_by(email=email).order_by(AdmissionApplication.applied_at.desc()).first()
        if not app_obj:
            flash('No application found for this email.', 'warning')
    return render_template('admission_status.html', title='Admission Status', app_obj=app_obj, email=email)

# --- Grades and Transcript ---
def grade_points(letter: str) -> float:
    mapping = {
        'A+': 4.0, 'A': 4.0,
        'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0,
        'F': 0.0
    }
    return mapping.get(letter.upper(), 0.0)

@app.route('/students/<int:student_id>/transcript')
@crud_required('grade', 'read')
def student_transcript(student_id):
    student = Student.query.get_or_404(student_id)
    # Security check
    role = session.get('role')
    user = session.get('user')
    if role == 'student' and student.email != user:
        flash('You are not authorized to view this transcript.', 'danger')
        return redirect(url_for('dashboard'))
    
    if role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_username=user, student_id=student.id).first()
        if not link:
            flash('You are not authorized to view this transcript.', 'danger')
            return redirect(url_for('dashboard'))
    
    grades = Grade.query.filter_by(student_id=student_id).all()
    records = []
    total_points = 0.0
    total_credits = 0
    
    # We'll use a dictionary to keep track of the "final" grade for GPA calculation
    # For GPA, we might want to only include grades that are NOT linked to an internal exam,
    # or handle it differently. For now, let's include all grades that have points.
    
    for gr in grades:
        letter = gr.letter
        pts = gr.points if gr.points is not None else (grade_points(letter) if letter else None)
        credits = gr.course.credits or 0
        
        # Only add to GPA if it's a final/general grade (no exam_id)
        if gr.exam_id is None and pts is not None:
            total_points += pts * (credits if credits else 1)
            total_credits += (credits if credits else 1)
            
        records.append({
            'id': gr.id,
            'course': gr.course, 
            'exam': gr.exam,
            'letter': letter, 
            'points': pts, 
            'credits': credits, 
            'semester': gr.semester, 
            'academic_year': gr.academic_year,
            'comments': gr.comments,
            'remarks': gr.remarks,
            'score': gr.score
        })
    
    # If a course has no grade record, we still might want to show it as "Enrolled"
    enrolled_course_ids = [c.id for c in student.courses]
    graded_course_ids = [g.course_id for g in grades]
    for course in student.courses:
        if course.id not in graded_course_ids:
            records.append({
                'id': None,
                'course': course,
                'exam': None,
                'letter': None,
                'points': None,
                'credits': course.credits or 0,
                'semester': course.semester,
                'academic_year': course.academic_year,
                'comments': '',
                'remarks': '',
                'score': None
            })

    gpa = (total_points / total_credits) if total_credits > 0 else None
    return render_template('student_transcript.html', title='Transcript', student=student, records=records, gpa=gpa)

@app.route('/students/<int:student_id>/grades/add', methods=['GET', 'POST'])
@crud_required('grade', 'create')
def add_grade(student_id):
    student = Student.query.get_or_404(student_id)
    enrolled_courses = list(student.courses)
    exams = Exam.query.all()
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        exam_id = request.form.get('exam_id')
        letter = request.form.get('letter', '').strip()
        points_str = request.form.get('points', '').strip()
        score_str = request.form.get('score', '').strip()
        grade_letter = request.form.get('grade_letter', '').strip()
        comments = request.form.get('comments', '').strip()
        semester = request.form.get('semester', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        remarks = request.form.get('remarks', '').strip()
        try:
            cid = int(course_id)
        except Exception:
            flash('Please select a course.', 'danger')
            return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)
        course = Course.query.get(cid)
        if not course or course not in enrolled_courses:
            flash('Course not found or not enrolled.', 'danger')
            return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)
        
        ex_id = None
        if exam_id:
            try:
                ex_id = int(exam_id)
            except ValueError:
                ex_id = None

        pts = None
        if points_str:
            try:
                pts = float(points_str)
            except ValueError:
                flash('Invalid points value.', 'danger')
                return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)
        
        score = None
        if score_str:
            try:
                score = float(score_str)
            except ValueError:
                flash('Invalid score value.', 'danger')
                return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)

        if not letter:
            flash('Letter grade is required.', 'danger')
            return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)
        try:
            g = Grade(
                student_id=student.id, 
                course_id=course.id, 
                exam_id=ex_id,
                letter=letter.upper(), 
                points=pts, 
                score=score,
                grade_letter=grade_letter.upper() if grade_letter else None,
                comments=comments or None,
                semester=semester or None,
                academic_year=academic_year or None,
                remarks=remarks or None,
                recorded_at=datetime.utcnow()
            )
            db.session.add(g)
            db.session.commit()
            flash('Grade recorded.', 'success')
            return redirect(url_for('student_transcript', student_id=student.id))
        except IntegrityError:
            db.session.rollback()
            flash('Grade for this course/exam already exists. Edit instead.', 'warning')
            return redirect(url_for('student_transcript', student_id=student.id))
    return render_template('add_grade.html', title='Add Grade', student=student, courses=enrolled_courses, exams=exams)

@app.route('/students/<int:student_id>/grades/<int:grade_id>/edit', methods=['GET', 'POST'])
@crud_required('grade', 'update')
def edit_grade(student_id, grade_id):
    student = Student.query.get_or_404(student_id)
    grade = Grade.query.get_or_404(grade_id)
    exams = Exam.query.all()
    if request.method == 'POST':
        exam_id = request.form.get('exam_id')
        letter = request.form.get('letter', '').strip()
        points_str = request.form.get('points', '').strip()
        score_str = request.form.get('score', '').strip()
        grade_letter = request.form.get('grade_letter', '').strip()
        comments = request.form.get('comments', '').strip()
        semester = request.form.get('semester', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
        ex_id = None
        if exam_id:
            try:
                ex_id = int(exam_id)
            except ValueError:
                ex_id = None

        pts = None
        if points_str:
            try:
                pts = float(points_str)
            except ValueError:
                flash('Invalid points value.', 'danger')
                return render_template('edit_grade.html', title='Edit Grade', student=student, grade=grade, exams=exams)
        
        score = None
        if score_str:
            try:
                score = float(score_str)
            except ValueError:
                flash('Invalid score value.', 'danger')
                return render_template('edit_grade.html', title='Edit Grade', student=student, grade=grade, exams=exams)

        if not letter:
            flash('Letter grade is required.', 'danger')
            return render_template('edit_grade.html', title='Edit Grade', student=student, grade=grade, exams=exams)
        
        grade.exam_id = ex_id
        grade.letter = letter.upper()
        grade.points = pts
        grade.score = score
        grade.grade_letter = grade_letter.upper() if grade_letter else None
        grade.comments = comments or None
        grade.semester = semester or None
        grade.academic_year = academic_year or None
        grade.remarks = remarks or None
        db.session.commit()
        flash('Grade updated.', 'success')
        return redirect(url_for('student_transcript', student_id=student.id))
    return render_template('edit_grade.html', title='Edit Grade', student=student, grade=grade, exams=exams)

# --- Analytics ---
@app.route('/analytics')
@crud_required('analytics', 'read')
def analytics():
    total_students = Student.query.count()
    total_courses = Course.query.count()
    # GPA average
    gpas = []
    for s in Student.query.all():
        grades = Grade.query.filter_by(student_id=s.id).all()
        if not grades:
            continue
        total_pts = 0.0
        total_cr = 0
        for g in grades:
            course = Course.query.get(g.course_id)
            pts = g.points if g.points is not None else grade_points(g.letter)
            cr = course.credits or 1
            total_pts += pts * cr
            total_cr += cr
        if total_cr:
            gpas.append(total_pts / total_cr)
    avg_gpa = (sum(gpas) / len(gpas)) if gpas else None
    # Attendance average per student
    attendance_rates = []
    sessions_all = CourseSession.query.all()
    session_ids_all = [s.id for s in sessions_all]
    if session_ids_all:
        for s in Student.query.all():
            recs = Attendance.query.filter(Attendance.session_id.in_(session_ids_all), Attendance.student_id == s.id).all()
            total = len(recs)
            if total:
                present_late = sum(1 for r in recs if r.status in ('present', 'late'))
                attendance_rates.append(present_late / total * 100.0)
    avg_attendance = (sum(attendance_rates) / len(attendance_rates)) if attendance_rates else None
    return render_template('analytics.html', title='Analytics', total_students=total_students, total_courses=total_courses, avg_gpa=avg_gpa, avg_attendance=avg_attendance)

# --- Bulk CSV Import Helpers ---
def _csv_rows(file_storage):
    if not file_storage:
        return []
    data = file_storage.read()
    if isinstance(data, bytes):
        try:
            text = data.decode('utf-8-sig')
        except Exception:
            text = data.decode('utf-8', errors='ignore')
    else:
        text = data
    reader = csv.DictReader(StringIO(text))
    rows = list(reader)
    return rows

def _valid_email(email):
    return bool(email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def _valid_phone(phone):
    return bool(phone and re.match(r"^[0-9\-\+\s]{7,20}$", phone))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['logged_in'] = True
            session['user'] = username
            session['role'] = user.role
            session.permanent = True
            flash('Logged in successfully.', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('students'))
        
        # Check for Student with temporary password
        student = Student.query.filter_by(email=username, temp_password=password).first()
        if student:
            session['logged_in'] = True
            session['user'] = username
            session['role'] = 'student'
            session.permanent = True
            flash('Logged in with temporary password. Please change your password.', 'warning')
            return redirect(url_for('change_password'))
        admin_user = os.environ.get('ADMIN_USERNAME')
        admin_pw_hash = os.environ.get('ADMIN_PASSWORD_HASH')
        admin_pw_plain = os.environ.get('ADMIN_PASSWORD')
        if admin_user and username == admin_user:
            valid = False
            if admin_pw_hash:
                valid = check_password_hash(admin_pw_hash, password)
            elif admin_pw_plain:
                valid = password == admin_pw_plain
            if valid:
                session['logged_in'] = True
                session['user'] = username
                session['role'] = 'admin'
                session.permanent = True
                flash('Logged in successfully.', 'success')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('students'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html', title='Login')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if not app.config.get('ALLOW_SELF_REGISTRATION', True):
        flash('Self-registration is disabled by the administrator.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('register.html', title='Register')
        min_len = app.config.get('PASSWORD_MIN_LENGTH', 8)
        if len(password) < int(min_len):
            flash(f'Password must be at least {min_len} characters.', 'danger')
            return render_template('register.html', title='Register')
        if app.config.get('REQUIRE_STRONG_PASSWORD', True):
            if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
                flash('Password must include uppercase, lowercase, and a number.', 'danger')
                return render_template('register.html', title='Register')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', title='Register')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html', title='Register')
        try:
            pw_hash = generate_password_hash(password)
            user = User(username=username, password_hash=pw_hash, role='student')
            db.session.add(user)
            db.session.commit()
            flash('Registration successful. You can log in now.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Error during registration')
            flash(f'Unexpected error: {str(e)}', 'danger')
    return render_template('register.html', title='Register')

def _reset_serializer():
    return URLSafeTimedSerializer(app.config.get('SECRET_KEY', 'changeme'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if not app.config.get('PASSWORD_RESET_ENABLED', True):
        flash('Password reset is disabled by the administrator.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username).first()
        # Always respond the same to avoid user enumeration via timing/messages
        if user:
            s = _reset_serializer()
            try:
                token = s.dumps(username, salt='password-reset')
                reset_url = url_for('reset_password', token=token, _external=True)
                flash('Password reset link generated. Use the link below to reset your password.', 'info')
                return render_template('forgot_password.html', title='Forgot Password', reset_url=reset_url)
            except Exception:
                logger.exception('Failed to generate reset token')
        flash('If the account exists, a reset link has been generated.', 'info')
        return render_template('forgot_password.html', title='Forgot Password')
    return render_template('forgot_password.html', title='Forgot Password')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not app.config.get('PASSWORD_RESET_ENABLED', True):
        flash('Password reset is disabled by the administrator.', 'warning')
        return redirect(url_for('login'))
    s = _reset_serializer()
    username = None
    try:
        username = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('Reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('forgot_password'))
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Account not found.', 'danger')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not password:
            flash('Password is required.', 'danger')
            return render_template('reset_password.html', title='Reset Password')
        min_len = app.config.get('PASSWORD_MIN_LENGTH', 8)
        if len(password) < int(min_len):
            flash(f'Password must be at least {min_len} characters.', 'danger')
            return render_template('reset_password.html', title='Reset Password')
        if app.config.get('REQUIRE_STRONG_PASSWORD', True):
            if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
                flash('Password must include uppercase, lowercase, and a number.', 'danger')
                return render_template('reset_password.html', title='Reset Password')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', title='Reset Password')
        try:
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash('Password has been reset. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Error resetting password')
            flash(f'Unexpected error: {str(e)}', 'danger')
    return render_template('reset_password.html', title='Reset Password')

@app.route("/logout")
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    username = session.get('user')
    user = User.query.filter_by(username=username).first()
    student = None
    
    if not user:
        # Check if it's a student with a temporary password
        student = Student.query.filter_by(email=username).first()
        if not student:
            flash('Account not found.', 'danger')
            return redirect(url_for('login'))

    if request.method == 'POST':
        current = request.form.get('current_password', '')
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        if not current:
            flash('Current password is required.', 'danger')
            return render_template('reset_password.html', title='Change Password', show_current=True)
            
        if user:
            if not check_password_hash(user.password_hash, current):
                flash('Current password is incorrect.', 'danger')
                return render_template('reset_password.html', title='Change Password', show_current=True)
        elif student:
            if student.temp_password != current:
                flash('Current temporary password is incorrect.', 'danger')
                return render_template('reset_password.html', title='Change Password', show_current=True)
        
        if not password:
            flash('New password is required.', 'danger')
            return render_template('reset_password.html', title='Change Password', show_current=True)
            
        min_len = int(app.config.get('PASSWORD_MIN_LENGTH', 8))
        if len(password) < min_len:
            flash(f'Password must be at least {min_len} characters.', 'danger')
            return render_template('reset_password.html', title='Change Password', show_current=True)
            
        if app.config.get('REQUIRE_STRONG_PASSWORD', True):
            if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password):
                flash('Password must include uppercase, lowercase, and a number.', 'danger')
                return render_template('reset_password.html', title='Change Password', show_current=True)
                
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', title='Change Password', show_current=True)
            
        try:
            if user:
                user.password_hash = generate_password_hash(password)
            elif student:
                # Create a User entry for the student and clear temporary password
                new_user = User(username=student.email, password_hash=generate_password_hash(password), role='student')
                db.session.add(new_user)
                student.temp_password = None
            
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Error changing password')
            flash(f'Unexpected error: {str(e)}', 'danger')
            
    return render_template('reset_password.html', title='Change Password', show_current=True)

@app.route('/profile')
@crud_required('user', 'read')
def profile():
    role = session.get('role')
    user_id = session.get('user')
    student = None
    teacher = None
    user = User.query.filter_by(username=user_id).first()
    photo = None
    try:
        db.create_all()
    except Exception:
        pass
    photo = UserPhoto.query.filter_by(username=user_id).first()
    photo_url = None
    if photo:
        photo_url = url_for('static', filename=photo.file_path)
    if role == 'student':
        student = Student.query.filter_by(email=user_id).first()
    elif role in ('faculty', 'teacher'):
        teacher = Teacher.query.filter_by(email=user_id).first()
    parent_students = []
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_id).all()
        for l in links:
            s = Student.query.get(l.student_id)
            if s:
                parent_students.append(s)
    return render_template('profile.html', title='Profile', role=role, user=user, student=student, teacher=teacher, parent_students=parent_students, photo_url=photo_url)

def _allowed_image(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ('png', 'jpg', 'jpeg')

@app.route('/profile/photo', methods=['POST'])
@crud_required('user', 'update')
def upload_profile_photo():
    username = session.get('user')
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected.', 'warning')
        return redirect(url_for('profile'))
    if not _allowed_image(file.filename):
        flash('Invalid image type. Allowed: png, jpg, jpeg.', 'danger')
        return redirect(url_for('profile'))
    fname = secure_filename(file.filename)
    ext = fname.rsplit('.', 1)[1].lower()
    unique_name = f"{username}_{uuid.uuid4().hex}.{ext}"
    upload_dir = app.config.get('USER_AVATARS_DIR')
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception:
        pass
    abs_path = os.path.join(upload_dir, unique_name)
    rel_path = os.path.join('uploads', 'avatars', unique_name).replace('\\', '/')
    try:
        file.save(abs_path)
        existing = UserPhoto.query.filter_by(username=username).first()
        if existing:
            existing.file_path = rel_path
        else:
            rec = UserPhoto(username=username, file_path=rel_path)
            db.session.add(rec)
        db.session.commit()
        flash('Profile photo updated.', 'success')
    except Exception:
        db.session.rollback()
        logger.exception('Failed to save profile photo')
        flash('Failed to upload photo.', 'danger')
    return redirect(url_for('profile'))

# --- Admin: User Management ---
@app.route('/admin/users')
@crud_required('user', 'read')
def admin_users():
    users = User.query.order_by(User.username.asc()).all()
    # Fetch photos for users
    usernames = [u.username for u in users]
    photos = {}
    for photo in UserPhoto.query.filter(UserPhoto.username.in_(usernames)).all():
        photos[photo.username] = url_for('static', filename=photo.file_path.lstrip('/'))
    return render_template('users.html', title='Users', users=users, photos=photos)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@crud_required('user', 'create')
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', '').strip()

        if not username or not password or not confirm_password or not role:
            flash('All fields are required.', 'danger')
            return render_template('add_user.html', title='Add User')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('add_user.html', title='Add User')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('add_user.html', title='Add User')

        try:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            
            # Audit log
            try:
                actor = session.get('user') or 'system'
                log = AuditLog(
                    action='user_create',
                    actor_username=actor,
                    actor_role=session.get('role'),
                    target=username,
                    details=f'role={role}'
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                pass

            flash(f'User {username} added successfully!', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'danger')

    return render_template('add_user.html', title='Add User')

@app.route('/admin/users/<int:user_id>/update-role', methods=['POST'])
@crud_required('user', 'update')
def admin_update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role not in ['admin', 'staff', 'faculty', 'teacher', 'student', 'parent']:
        flash('Invalid role selected.', 'danger')
        return redirect(url_for('admin_users'))
    
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    # Audit log
    try:
        actor = session.get('user') or 'system'
        log = AuditLog(
            action='user_role_update',
            actor_username=actor,
            actor_role=session.get('role'),
            target=user.username,
            details=f'old_role={old_role}, new_role={new_role}'
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
        
    flash(f'Role for {user.username} updated to {new_role}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@crud_required('user', 'delete')
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == session.get('user'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    # Audit log
    try:
        actor = session.get('user') or 'system'
        log = AuditLog(
            action='user_delete',
            actor_username=actor,
            actor_role=session.get('role'),
            target=username,
            details=''
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
        
    flash(f'User {username} deleted.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/crud')
@roles_required('admin')
def admin_crud():
    entities = [
        {'name': 'Students', 'icon': 'fas fa-user-graduate', 'url': url_for('students'), 'add_url': url_for('add_student'), 'count': Student.query.count()},
        {'name': 'Teachers', 'icon': 'fas fa-chalkboard-teacher', 'url': url_for('teachers'), 'add_url': url_for('add_teacher'), 'count': Teacher.query.count()},
        {'name': 'Courses', 'icon': 'fas fa-book', 'url': url_for('courses'), 'add_url': url_for('add_course'), 'count': Course.query.count()},
        {'name': 'Users', 'icon': 'fas fa-users-cog', 'url': url_for('admin_users'), 'add_url': url_for('add_user'), 'count': User.query.count()},
        {'name': 'Admissions', 'icon': 'fas fa-user-plus', 'url': url_for('admissions'), 'add_url': url_for('add_admission'), 'count': AdmissionApplication.query.count()},
        {'name': 'Resources', 'icon': 'fas fa-building', 'url': url_for('resources'), 'add_url': url_for('resources_add'), 'count': Resource.query.count()},
    ]
    return render_template('admin_crud.html', title='System CRUD', entities=entities)

@app.route('/admin/parent-links', methods=['GET', 'POST'])
@crud_required('parent_link', 'read')
def admin_parent_links():
    try:
        db.create_all()
    except Exception:
        pass
    if request.method == 'POST':
        parent_username = request.form.get('parent_username', '').strip()
        student_email = request.form.get('student_email', '').strip()
        if not parent_username or not student_email:
            flash('Parent username and student email are required.', 'danger')
            return redirect(url_for('admin_parent_links'))
            
        # Check if parent user exists and has correct role
        parent_user = User.query.filter_by(username=parent_username).first()
        if not parent_user or parent_user.role != 'parent':
            flash(f'User "{parent_username}" not found or is not a parent.', 'danger')
            return redirect(url_for('admin_parent_links'))
            
        student = Student.query.filter_by(email=student_email).first()
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('admin_parent_links'))
        existing = ParentStudentLink.query.filter_by(parent_username=parent_username, student_id=student.id).first()
        if existing:
            flash('Link already exists.', 'warning')
        else:
            l = ParentStudentLink(parent_username=parent_username, student_id=student.id)
            db.session.add(l)
            db.session.commit()
            flash('Link added.', 'success')
        return redirect(url_for('admin_parent_links'))
    
    links = ParentStudentLink.query.order_by(ParentStudentLink.parent_username.asc()).all()
    # Fetch photos for parents and students
    usernames = set()
    for l in links:
        usernames.add(l.parent_username)
        usernames.add(l.student.email)
    
    photos = {}
    for photo in UserPhoto.query.filter(UserPhoto.username.in_(list(usernames))).all():
        photos[photo.username] = url_for('static', filename=photo.file_path.lstrip('/'))
        
    parents = User.query.filter_by(role='parent').order_by(User.username.asc()).all()
    students = Student.query.order_by(Student.name.asc()).all()
        
    return render_template('admin_parent_links.html', title='Parent Links', links=links, photos=photos, parents=parents, students=students)

@app.route('/admin/parent-links/<int:link_id>/delete', methods=['POST'])
@crud_required('parent_link', 'delete')
def admin_parent_links_delete(link_id):
    try:
        db.create_all()
    except Exception:
        pass
    link = ParentStudentLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash('Link removed.', 'success')
    return redirect(url_for('admin_parent_links'))

# --- Admin: Policy & Compliance ---
@app.route('/admin/policies', methods=['GET', 'POST'])
@crud_required('analytics', 'read')
def admin_policies():
    from project.models import SystemSetting
    # Ensure tables exist for newly added settings model
    try:
        db.create_all()
    except Exception:
        pass
    policy_keys = [
        'TEACHER_MAX_SESSIONS_PER_DAY',
        'TEACHER_MAX_SESSIONS_PER_WEEK',
        'COURSE_MAX_SESSIONS_PER_WEEK',
        'ALLOW_WEEKEND_SESSIONS',
        'LEAVE_APPROVAL_REQUIRED',
        'ATTENDANCE_MARKING_CUTOFF_DAYS',
        'ATTENDANCE_ALLOW_EDIT',
        'TEACHER_MAX_HOURS_PER_DAY',
        'TEACHER_MAX_HOURS_PER_WEEK',
        'HOURS_PER_CREDIT',
        'WORKLOAD_FAIRNESS_ENABLED',
        'WORKLOAD_TARGET_WEEKLY_HOURS',
        'WORKLOAD_TOLERANCE_HOURS',
        'PERFORMANCE_ENABLED',
        'PERFORMANCE_MIN_SESSIONS_FOR_REPORT',
        'LAB_GENERATE_EVERY_N',
        'PROJECT_GENERATE_EVERY_M',
        'DEFAULT_CURRENCY',
        'FINANCE_ALLOW_PARTIAL_PAYMENTS',
        'TAX_RATE_PERCENT',
        'DISCOUNT_MAX_PERCENT',
        'MAX_BOOKING_DURATION_MINUTES',
        'RESOURCE_AUTO_APPROVE_ROLES',
    ]
    if request.method == 'POST':
        try:
            updated_keys = []
            for key in policy_keys:
                val = request.form.get(key)
                if val is None:
                    continue
                setting = SystemSetting.query.filter_by(key=key).first()
                if not setting:
                    setting = SystemSetting(key=key, value=str(val))
                    db.session.add(setting)
                else:
                    setting.value = str(val)
                updated_keys.append(key)
            db.session.commit()
            # Refresh app.config values
            settings = SystemSetting.query.all()
            for s in settings:
                from project import app as _app
                # Reuse parsing logic similar to __init__
                low = s.value.strip().lower()
                if low in ('1','true','yes','on'):
                    _app.config[s.key] = True
                elif low in ('0','false','no','off'):
                    _app.config[s.key] = False
                else:
                    try:
                        _app.config[s.key] = int(s.value)
                    except Exception:
                        _app.config[s.key] = s.value
            # Audit log for policy changes
            try:
                db.create_all()
                actor = session.get('user') or 'system'
                details = f"updated={','.join(updated_keys)}"
                log = AuditLog(
                    action='policies_update',
                    actor_username=actor,
                    actor_role=session.get('role'),
                    target='system_settings',
                    details=details
                )
                db.session.add(log)
                db.session.commit()
            except Exception as _e:
                logger.warning(f"Failed to write audit log for policies_update: {_e}")
            flash('Policies updated.', 'success')
            return redirect(url_for('admin_policies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update policies: {str(e)}', 'danger')
    current = {key: app.config.get(key) for key in policy_keys}
    return render_template('policies.html', title='Policies', current=current)

@app.route("/students")
@login_required
@crud_required('student', 'read')
def students():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    role = session.get('role')
    user_email = session.get('user')
    
    query = Student.query
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        query = query.filter(Student.id.in_(student_ids))
    elif role == 'student':
        query = query.filter(Student.email == user_email)
    
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Student.name.ilike(like), Student.email.ilike(like), Student.phone.ilike(like)))
    pagination = query.order_by(Student.name.asc()).paginate(page=page, per_page=10)
    emails = [s.email for s in pagination.items]
    photos = {}
    try:
        db.create_all()
    except Exception:
        pass
    if emails:
        recs = UserPhoto.query.filter(UserPhoto.username.in_(emails)).all()
        for r in recs:
            photos[r.username] = url_for('static', filename=r.file_path)
    return render_template('students.html', students=pagination.items, pagination=pagination, q=q, title='Students', photos=photos)

# --- Bulk Upload UI ---
@app.route('/import', methods=['GET'])
@crud_required('bulk_upload', 'read')
def bulk_upload():
    return render_template('bulk_upload.html', title='Bulk Upload')

# --- Bulk Import: Students ---
@app.route('/import/students', methods=['POST'])
@crud_required('bulk_upload', 'create')
def import_students():
    file = request.files.get('file')
    password_strategy = request.form.get('password_strategy', 'none')
    fixed_password = request.form.get('fixed_password', '')
    
    rows = _csv_rows(file)
    max_rows = app.config.get('MAX_BULK_IMPORT_ROWS', 1000)
    if len(rows) > max_rows:
        flash(f'File has {len(rows)} rows; only first {max_rows} will be processed.', 'warning')
        rows = rows[:max_rows]
    created = 0
    skipped = 0
    users_created = 0
    errors = []
    for i, row in enumerate(rows, start=1):
        name = (row.get('name') or '').strip()
        email = (row.get('email') or '').strip().lower()
        phone = (row.get('phone') or '').strip()
        roll_number = (row.get('roll_number') or '').strip() or None
        address = (row.get('address') or '').strip() or None
        dob_str = (row.get('date_of_birth') or '').strip()
        department = (row.get('department') or '').strip() or None
        guardian_name = (row.get('guardian_name') or '').strip() or None
        guardian_phone = (row.get('guardian_phone') or '').strip() or None
        guardian_email = (row.get('guardian_email') or '').strip() or None
        nationality = (row.get('nationality') or '').strip() or None
        blood_group = (row.get('blood_group') or '').strip() or None
        religion = (row.get('religion') or '').strip() or None
        community = (row.get('community') or '').strip() or None
        sslc_marks_str = (row.get('sslc_marks') or '').strip()
        hsc_marks_str = (row.get('hsc_marks') or '').strip()
        current_year_str = (row.get('current_year') or '').strip()
        current_semester_str = (row.get('current_semester') or '').strip()
        section = (row.get('section') or '').strip() or None
        father_name = (row.get('father_name') or '').strip() or None
        mother_name = (row.get('mother_name') or '').strip() or None
        emergency_contact_name = (row.get('emergency_contact_name') or '').strip() or None
        emergency_contact_phone = (row.get('emergency_contact_phone') or '').strip() or None
        previous_school = (row.get('previous_school') or '').strip() or None

        if not name or not _valid_email(email) or not _valid_phone(phone):
            errors.append(f"Row {i}: invalid name/email/phone")
            skipped += 1
            continue
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Row {i}: invalid date_of_birth '{dob_str}' (expected YYYY-MM-DD)")
        
        sslc_marks = None
        if sslc_marks_str:
            try:
                sslc_marks = int(sslc_marks_str)
            except ValueError:
                errors.append(f"Row {i}: invalid sslc_marks '{sslc_marks_str}'")
        
        hsc_marks = None
        if hsc_marks_str:
            try:
                hsc_marks = int(hsc_marks_str)
            except ValueError:
                errors.append(f"Row {i}: invalid hsc_marks '{hsc_marks_str}'")

        current_year = None
        if current_year_str:
            try:
                current_year = int(current_year_str)
            except ValueError:
                errors.append(f"Row {i}: invalid current_year '{current_year_str}'")

        current_semester = None
        if current_semester_str:
            try:
                current_semester = int(current_semester_str)
            except ValueError:
                errors.append(f"Row {i}: invalid current_semester '{current_semester_str}'")

        if Student.query.filter_by(email=email).first():
            skipped += 1
            continue
        # Map department name to ID
        department_obj = None
        if department:
            department_obj = Department.query.filter(Department.name.ilike(department)).first()
        
        try:
            s = Student(
                name=name, email=email, phone=phone, roll_number=roll_number, 
                address=address, date_of_birth=dob, 
                department_id=department_obj.id if department_obj else None,
                guardian_name=guardian_name, guardian_phone=guardian_phone,
                guardian_email=guardian_email,
                nationality=nationality, blood_group=blood_group,
                religion=religion, community=community,
                sslc_marks=sslc_marks, hsc_marks=hsc_marks,
                current_year=current_year, current_semester=current_semester,
                section=section, father_name=father_name, mother_name=mother_name,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                previous_school=previous_school
            )
            db.session.add(s)
            
            # Handle user account creation
            if password_strategy != 'none':
                password = None
                if password_strategy == 'fixed':
                    password = fixed_password
                elif password_strategy == 'email':
                    password = email
                elif password_strategy == 'csv':
                    password = (row.get('password') or '').strip()
                
                if password:
                    if not User.query.filter_by(username=email).first():
                        u = User(
                            username=email,
                            password_hash=generate_password_hash(password),
                            role='student'
                        )
                        db.session.add(u)
                        users_created += 1
                    else:
                        errors.append(f"Row {i}: User account for {email} already exists")
                else:
                    errors.append(f"Row {i}: No password provided for strategy '{password_strategy}'")
            
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to import students: {str(e)}', 'danger')
        return redirect(url_for('bulk_upload'))
    flash(f'Imported students: {created} created, {users_created} user accounts created, {skipped} skipped.', 'success')
    if errors:
        flash('Some rows had issues: ' + '; '.join(errors[:5]) + ('' if len(errors) <= 5 else ' ...'), 'warning')
    return redirect(url_for('students'))

# --- Bulk Import: Teachers ---
@app.route('/import/teachers', methods=['POST'])
@crud_required('bulk_upload', 'create')
def import_teachers():
    file = request.files.get('file')
    password_strategy = request.form.get('password_strategy', 'none')
    fixed_password = request.form.get('fixed_password', '')
    
    rows = _csv_rows(file)
    max_rows = app.config.get('MAX_BULK_IMPORT_ROWS', 1000)
    if len(rows) > max_rows:
        flash(f'File has {len(rows)} rows; only first {max_rows} will be processed.', 'warning')
        rows = rows[:max_rows]
    created = 0
    skipped = 0
    users_created = 0
    errors = []
    for i, row in enumerate(rows, start=1):
        name = (row.get('name') or '').strip()
        email = (row.get('email') or '').strip().lower()
        phone = (row.get('phone') or '').strip()
        department = (row.get('department') or '').strip() or None
        designation = (row.get('designation') or '').strip() or None
        specialization = (row.get('specialization') or '').strip() or None
        qualification = (row.get('qualification') or '').strip() or None
        subject_expertise = (row.get('subject_expertise') or '').strip() or None
        dob_str = (row.get('date_of_birth') or '').strip()
        joining_date_str = (row.get('joining_date') or '').strip()
        pan_number = (row.get('pan_number') or '').strip() or None
        aadhaar_number = (row.get('aadhaar_number') or '').strip() or None
        experience_years_str = (row.get('experience_years') or '').strip()
        
        if not name or not _valid_email(email) or not _valid_phone(phone):
            errors.append(f"Row {i}: invalid name/email/phone")
            skipped += 1
            continue
        
        experience_years = None
        if experience_years_str:
            try:
                experience_years = int(experience_years_str)
            except ValueError:
                errors.append(f"Row {i}: invalid experience_years '{experience_years_str}'")

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Row {i}: invalid date_of_birth '{dob_str}'")

        joining_date = None
        if joining_date_str:
            try:
                joining_date = datetime.strptime(joining_date_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Row {i}: invalid joining_date '{joining_date_str}'")

        if Teacher.query.filter_by(email=email).first():
            skipped += 1
            continue

        # Map department name to ID
        department_obj = None
        if department:
            department_obj = Department.query.filter(Department.name.ilike(department)).first()

        try:
            t = Teacher(
                name=name, email=email, phone=phone, 
                department_id=department_obj.id if department_obj else None,
                designation=designation, specialization=specialization,
                qualification=qualification, subject_expertise=subject_expertise,
                date_of_birth=dob, joining_date=joining_date,
                pan_number=pan_number, aadhaar_number=aadhaar_number,
                experience_years=experience_years
            )
            db.session.add(t)
            
            # Handle user account creation
            if password_strategy != 'none':
                password = None
                if password_strategy == 'fixed':
                    password = fixed_password
                elif password_strategy == 'email':
                    password = email
                elif password_strategy == 'csv':
                    password = (row.get('password') or '').strip()
                
                if password:
                    if not User.query.filter_by(username=email).first():
                        u = User(
                            username=email,
                            password_hash=generate_password_hash(password),
                            role='teacher'
                        )
                        db.session.add(u)
                        users_created += 1
                    else:
                        errors.append(f"Row {i}: User account for {email} already exists")
                else:
                    errors.append(f"Row {i}: No password provided for strategy '{password_strategy}'")
            
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to import teachers: {str(e)}', 'danger')
        return redirect(url_for('bulk_upload'))
    flash(f'Imported teachers: {created} created, {users_created} user accounts created, {skipped} skipped.', 'success')
    if errors:
        flash('Some rows had issues: ' + '; '.join(errors[:5]) + ('' if len(errors) <= 5 else ' ...'), 'warning')
    return redirect(url_for('teachers'))

# --- Bulk Import: Courses ---
@app.route('/import/courses', methods=['POST'])
@crud_required('bulk_upload', 'create')
def import_courses():
    file = request.files.get('file')
    rows = _csv_rows(file)
    max_rows = app.config.get('MAX_BULK_IMPORT_ROWS', 1000)
    if len(rows) > max_rows:
        flash(f'File has {len(rows)} rows; only first {max_rows} will be processed.', 'warning')
        rows = rows[:max_rows]
    created = 0
    skipped = 0
    errors = []
    for i, row in enumerate(rows, start=1):
        name = (row.get('name') or '').strip()
        description = (row.get('description') or '').strip() or None
        code = (row.get('code') or '').strip() or None
        credits_str = (row.get('credits') or '').strip()
        teacher_email = (row.get('teacher_email') or '').strip().lower()
        
        department = (row.get('department') or '').strip() or None
        semester = (row.get('semester') or '').strip() or None
        room = (row.get('room') or '').strip() or None
        capacity_str = (row.get('capacity') or '').strip()
        level = (row.get('level') or '').strip() or None
        syllabus_url = (row.get('syllabus_url') or '').strip() or None
        course_type = (row.get('course_type') or '').strip() or None
        academic_year = (row.get('academic_year') or '').strip() or None

        if not name or not _valid_email(teacher_email):
            errors.append(f"Row {i}: missing name or invalid teacher_email")
            skipped += 1
            continue
        teacher = Teacher.query.filter_by(email=teacher_email).first()
        if not teacher:
            errors.append(f"Row {i}: teacher not found: {teacher_email}")
            skipped += 1
            continue
        credits = None
        if credits_str:
            try:
                credits = int(credits_str)
            except ValueError:
                errors.append(f"Row {i}: invalid credits '{credits_str}'")
        
        capacity = None
        if capacity_str:
            try:
                capacity = int(capacity_str)
            except ValueError:
                errors.append(f"Row {i}: invalid capacity '{capacity_str}'")

        if code and Course.query.filter_by(code=code).first():
            skipped += 1
            continue

        # Map department name to ID
        department_obj = None
        if department:
            department_obj = Department.query.filter(Department.name.ilike(department)).first()

        try:
            c = Course(
                name=name, description=description, code=code, credits=credits, 
                teacher_id=teacher.id, 
                department_id=department_obj.id if department_obj else None,
                semester=semester,
                room=room, capacity=capacity, level=level, syllabus_url=syllabus_url,
                course_type=course_type, academic_year=academic_year
            )
            db.session.add(c)
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to import courses: {str(e)}', 'danger')
        return redirect(url_for('bulk_upload'))
    flash(f'Imported courses: {created} created, {skipped} skipped.', 'success')
    if errors:
        flash('Some rows had issues: ' + '; '.join(errors[:5]) + ('' if len(errors) <= 5 else ' ...'), 'warning')
    return redirect(url_for('courses'))

# --- Bulk Import: Enrollments ---
@app.route('/import/enrollments', methods=['POST'])
@crud_required('bulk_upload', 'create')
def import_enrollments():
    file = request.files.get('file')
    rows = _csv_rows(file)
    max_rows = app.config.get('MAX_BULK_IMPORT_ROWS', 1000)
    if len(rows) > max_rows:
        flash(f'File has {len(rows)} rows; only first {max_rows} will be processed.', 'warning')
        rows = rows[:max_rows]
    created = 0
    skipped = 0
    errors = []
    for i, row in enumerate(rows, start=1):
        student_email = (row.get('student_email') or '').strip().lower()
        course_code = (row.get('course_code') or '').strip()
        if not _valid_email(student_email) or not course_code:
            errors.append(f"Row {i}: invalid student_email or missing course_code")
            skipped += 1
            continue
        student = Student.query.filter_by(email=student_email).first()
        course = Course.query.filter_by(code=course_code).first()
        if not student or not course:
            errors.append(f"Row {i}: student or course not found")
            skipped += 1
            continue
        try:
            if student not in course.students:
                course.students.append(student)
                created += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to import enrollments: {str(e)}', 'danger')
        return redirect(url_for('bulk_upload'))
    flash(f'Imported enrollments: {created} created, {skipped} skipped.', 'success')
    if errors:
        flash('Some rows had issues: ' + '; '.join(errors[:5]) + ('' if len(errors) <= 5 else ' ...'), 'warning')
    return redirect(url_for('courses'))

# --- Sample CSV Endpoints ---
@app.route('/import/sample/students.csv')
@crud_required('bulk_upload', 'read')
def sample_students_csv():
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['name','email','phone','roll_number','current_year','current_semester','section','father_name','mother_name','emergency_contact_name','emergency_contact_phone','previous_school','address','date_of_birth','department','guardian_name','guardian_phone','nationality','blood_group','religion','community','sslc_marks','hsc_marks','password'])
    writer.writerow(['Alice Johnson','alice@example.com','+1 555 123 4567','RN-001','1','1','A','Mark Johnson','Mary Johnson','Uncle Bob','+1 555 999 8888','St. Peter High School','123 Main St','2001-05-10','Computer Science','Mark Johnson','+1 555 000 1111','American','O+','Christian','General','450','480','password123'])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=students_sample.csv'})

@app.route('/import/sample/teachers.csv')
@crud_required('bulk_upload', 'read')
def sample_teachers_csv():
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['name','email','phone','department','designation','specialization','pan_number','aadhaar_number','experience_years','password'])
    writer.writerow(['Dr Jane Doe','jane.doe@example.com','+1 555 222 3333','Mathematics','Professor','Calculus','ABCDE1234F','123456789012','10','securepass789'])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=teachers_sample.csv'})

@app.route('/import/sample/courses.csv')
@crud_required('bulk_upload', 'read')
def sample_courses_csv():
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['name','description','code','credits','teacher_email','department','semester','course_type','academic_year','room','capacity','level','syllabus_url'])
    writer.writerow(['Introduction to Python','A beginner-friendly course on Python.','PY101','3','jane.doe@example.com','Computer Science','1','Core','2023-24','Room 101','30','Undergraduate','https://example.com/syllabus/py101'])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=courses_sample.csv'})

@app.route('/import/sample/enrollments.csv')
@crud_required('bulk_upload', 'read')
def sample_enrollments_csv():
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['student_email','course_code'])
    writer.writerow(['alice@example.com','MATH101'])
    writer.writerow(['bob@example.com','PHYS101'])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=enrollments_sample.csv'})

@app.route("/students/add", methods=['GET', 'POST'])
@crud_required('student', 'create')
def add_student():
    if request.method == 'POST':
        registration_number = request.form.get('registration_number', '').strip()
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        roll_number = request.form.get('roll_number', '').strip()
        address = request.form.get('address', '').strip()
        dob_str = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', '').strip()
        admission_date_str = request.form.get('admission_date', '').strip()
        department_id = request.form.get('department_id')
        guardian_name = request.form.get('guardian_name', '').strip()
        guardian_phone = request.form.get('guardian_phone', '').strip()
        guardian_email = request.form.get('guardian_email', '').strip()
        status = request.form.get('status', '').strip() or 'active'
        nationality = request.form.get('nationality', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        religion = request.form.get('religion', '').strip()
        community = request.form.get('community', '').strip()
        sslc_marks_str = request.form.get('sslc_marks', '').strip()
        hsc_marks_str = request.form.get('hsc_marks', '').strip()
        current_year_str = request.form.get('current_year', '').strip()
        current_semester_str = request.form.get('current_semester', '').strip()
        section = request.form.get('section', '').strip()
        father_name = request.form.get('father_name', '').strip()
        mother_name = request.form.get('mother_name', '').strip()
        emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        previous_school = request.form.get('previous_school', '').strip()
        aadhar_no = request.form.get('aadhar_no', '').strip()
        community_cert_no = request.form.get('community_cert_no', '').strip()
        income_cert_no = request.form.get('income_cert_no', '').strip()
        annual_income_str = request.form.get('annual_income', '').strip()
        
        annual_income = None
        if annual_income_str:
            try:
                annual_income = float(annual_income_str)
            except ValueError:
                pass
        
        sslc_marks = None
        if sslc_marks_str:
            try:
                sslc_marks = int(sslc_marks_str)
            except ValueError:
                pass
        
        hsc_marks = None
        if hsc_marks_str:
            try:
                hsc_marks = int(hsc_marks_str)
            except ValueError:
                pass

        current_year = None
        if current_year_str:
            try:
                current_year = int(current_year_str)
            except ValueError:
                pass

        current_semester = None
        if current_semester_str:
            try:
                current_semester = int(current_semester_str)
            except ValueError:
                pass

        logger.info(f"Adding student: {name} ({email})")
        if not name.strip():
            flash('Name is required.', 'danger')
            return render_template('add_student.html', title='Add Student')
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash('Invalid email format.', 'danger')
            return render_template('add_student.html', title='Add Student')
        if not re.match(r"^[0-9\-\+\s]{7,20}$", phone):
            flash('Invalid phone number.', 'danger')
            return render_template('add_student.html', title='Add Student')
        if guardian_phone and not re.match(r"^[0-9\-\+\s]{7,20}$", guardian_phone):
            flash('Invalid guardian phone number.', 'danger')
            return render_template('add_student.html', title='Add Student')
        if emergency_contact_phone and not re.match(r"^[0-9\-\+\s]{7,20}$", emergency_contact_phone):
            flash('Invalid emergency contact phone number.', 'danger')
            return render_template('add_student.html', title='Add Student')
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                return render_template('add_student.html', title='Add Student')
        
        admission_date = None
        if admission_date_str:
            try:
                admission_date = datetime.strptime(admission_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid admission date.', 'danger')
                return render_template('add_student.html', title='Add Student')

        try:
            student = Student(
                registration_number=registration_number or None,
                name=name, 
                email=email, 
                phone=phone, 
                roll_number=roll_number or None, 
                address=address or None, 
                date_of_birth=dob,
                gender=gender or None,
                admission_date=admission_date,
                department_id=int(department_id) if department_id else None,
                guardian_name=guardian_name or None,
                guardian_phone=guardian_phone or None,
                guardian_email=guardian_email or None,
                status=status,
                nationality=nationality or None,
                blood_group=blood_group or None,
                religion=religion or None,
                community=community or None,
                sslc_marks=sslc_marks,
                hsc_marks=hsc_marks,
                previous_school=previous_school or None,
                current_year=current_year,
                current_semester=current_semester,
                section=section or None,
                father_name=father_name or None,
                mother_name=mother_name or None,
                emergency_contact_name=emergency_contact_name or None,
                emergency_contact_phone=emergency_contact_phone or None,
                aadhar_no=aadhar_no or None,
                community_cert_no=community_cert_no or None,
                annual_income=annual_income,
                income_cert_no=income_cert_no or None
            )
            db.session.add(student)
            db.session.commit()
            
            # Auto-assign tutor
            tutor = assign_tutor(student)
            if tutor:
                flash(f'Student has been added and assigned to tutor {tutor.name}!', 'success')
            else:
                flash('Student has been added, but no tutor was available for assignment.', 'warning')
                
            return redirect(url_for('students'))
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Failed to add student due to duplicate email: {email}")
            flash('Email already exists. Please use a different email.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.exception("Unexpected error adding student")
            flash(f'Unexpected error: {str(e)}', 'danger')
    teachers = Teacher.query.all()
    departments = Department.query.all()
    return render_template('add_student.html', title='Add Student', teachers=teachers, departments=departments)

@app.route("/students/<int:student_id>/edit", methods=['GET', 'POST'])
@crud_required('student', 'update')
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    teachers = Teacher.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        student.registration_number = request.form.get('registration_number', '').strip() or None
        student.name = request.form['name']
        student.email = request.form['email']
        student.phone = request.form['phone']
        student.roll_number = request.form.get('roll_number', '').strip() or None
        student.address = request.form.get('address', '').strip() or None
        student.gender = request.form.get('gender', '').strip() or None
        
        dept_id = request.form.get('department_id')
        student.department_id = int(dept_id) if dept_id else None

        student.guardian_name = request.form.get('guardian_name', '').strip() or None
        guardian_phone = request.form.get('guardian_phone', '').strip()
        student.guardian_phone = guardian_phone or None
        student.guardian_email = request.form.get('guardian_email', '').strip() or None
        student.status = request.form.get('status', '').strip() or student.status
        student.nationality = request.form.get('nationality', '').strip() or None
        student.blood_group = request.form.get('blood_group', '').strip() or None
        student.religion = request.form.get('religion', '').strip() or None
        student.community = request.form.get('community', '').strip() or None
        student.current_year = request.form.get('current_year', type=int)
        student.current_semester = request.form.get('current_semester', type=int)
        student.section = request.form.get('section', '').strip() or None
        student.father_name = request.form.get('father_name', '').strip() or None
        student.mother_name = request.form.get('mother_name', '').strip() or None
        student.emergency_contact_name = request.form.get('emergency_contact_name', '').strip() or None
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        student.emergency_contact_phone = emergency_contact_phone or None
        student.previous_school = request.form.get('previous_school', '').strip() or None
        student.aadhar_no = request.form.get('aadhar_no', '').strip() or None
        student.community_cert_no = request.form.get('community_cert_no', '').strip() or None
        student.income_cert_no = request.form.get('income_cert_no', '').strip() or None
        
        annual_income_str = request.form.get('annual_income', '').strip()
        if annual_income_str:
            try:
                student.annual_income = float(annual_income_str)
            except ValueError:
                pass
        else:
            student.annual_income = None
        
        sslc_marks_str = request.form.get('sslc_marks', '').strip()
        if sslc_marks_str:
            try:
                student.sslc_marks = int(sslc_marks_str)
            except ValueError:
                pass
        else:
            student.sslc_marks = None
            
        hsc_marks_str = request.form.get('hsc_marks', '').strip()
        if hsc_marks_str:
            try:
                student.hsc_marks = int(hsc_marks_str)
            except ValueError:
                pass
        else:
            student.hsc_marks = None
        
        tutor_id = request.form.get('tutor_id')
        if tutor_id:
            try:
                student.tutor_id = int(tutor_id)
            except ValueError:
                student.tutor_id = None
        else:
            student.tutor_id = None

        dob_str = request.form.get('date_of_birth', '').strip()
        if dob_str:
            try:
                student.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        else:
            student.date_of_birth = None

        admission_date_str = request.form.get('admission_date', '').strip()
        if admission_date_str:
            try:
                student.admission_date = datetime.strptime(admission_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid admission date.', 'danger')
                return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        else:
            student.admission_date = None

        if not student.name.strip():
            flash('Name is required.', 'danger')
            return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", student.email):
            flash('Invalid email format.', 'danger')
            return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        if not re.match(r"^[0-9\-\+\s]{7,20}$", student.phone):
            flash('Invalid phone number.', 'danger')
            return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        if guardian_phone and not re.match(r"^[0-9\-\+\s]{7,20}$", guardian_phone):
            flash('Invalid guardian phone number.', 'danger')
            return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        if emergency_contact_phone and not re.match(r"^[0-9\-\+\s]{7,20}$", emergency_contact_phone):
            flash('Invalid emergency contact phone number.', 'danger')
            return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)
        try:
            db.session.commit()
            flash('Student has been updated!', 'success')
            return redirect(url_for('students'))
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Failed to update student due to duplicate email: {student.email}")
            flash('Email already exists. Please use a different email.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.exception("Unexpected error updating student")
            flash(f'Unexpected error: {str(e)}', 'danger')
    return render_template('edit_student.html', title='Edit Student', student=student, teachers=teachers, departments=departments)

@app.route("/students/<int:student_id>/delete", methods=['POST'])
@crud_required('student', 'delete')
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    logger.info(f"Deleting student id={student_id}")
    db.session.delete(student)
    db.session.commit()
    flash('Student has been deleted!', 'success')
    return redirect(url_for('students'))

@app.route("/teachers")
@login_required
@crud_required('teacher', 'read')
def teachers():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Teacher.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Teacher.name.ilike(like), Teacher.email.ilike(like), Teacher.phone.ilike(like)))
    pagination = query.order_by(Teacher.name.asc()).paginate(page=page, per_page=10)
    emails = [t.email for t in pagination.items]
    photos = {}
    try:
        db.create_all()
    except Exception:
        pass
    if emails:
        recs = UserPhoto.query.filter(UserPhoto.username.in_(emails)).all()
        for r in recs:
            photos[r.username] = url_for('static', filename=r.file_path)
    return render_template('teachers.html', teachers=pagination.items, pagination=pagination, q=q, title='Teachers', photos=photos)

@app.route("/teachers/add", methods=['GET', 'POST'])
@crud_required('teacher', 'create')
def add_teacher():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        department_id = request.form.get('department_id')
        address = request.form.get('address', '').strip()
        gender = request.form.get('gender', '').strip()
        office_hours = request.form.get('office_hours', '').strip()
        employment_status = request.form.get('employment_status', '').strip()
        designation = request.form.get('designation', '').strip()
        specialization = request.form.get('specialization', '').strip()
        qualification = request.form.get('qualification', '').strip()
        subject_expertise = request.form.get('subject_expertise', '').strip()
        max_weekly_hours_str = request.form.get('max_weekly_hours', '').strip()
        pan_number = request.form.get('pan_number', '').strip()
        aadhaar_number = request.form.get('aadhaar_number', '').strip()
        experience_years_str = request.form.get('experience_years', '').strip()
        
        max_weekly_hours = None
        if max_weekly_hours_str:
            try:
                max_weekly_hours = int(max_weekly_hours_str)
            except ValueError:
                flash('Max weekly hours must be an integer.', 'danger')
                return render_template('add_teacher.html', title='Add Teacher')
        
        experience_years = None
        if experience_years_str:
            try:
                experience_years = int(experience_years_str)
            except ValueError:
                pass
        
        dob_str = request.form.get('date_of_birth', '').strip()
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                return render_template('add_teacher.html', title='Add Teacher')

        joining_date_str = request.form.get('joining_date', '').strip()
        joining_date = None
        if joining_date_str:
            try:
                joining_date = datetime.strptime(joining_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid joining date.', 'danger')
                return render_template('add_teacher.html', title='Add Teacher')

        logger.info(f"Adding teacher: {name} ({email})")
        if not name.strip():
            flash('Name is required.', 'danger')
            return render_template('add_teacher.html', title='Add Teacher')
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash('Invalid email format.', 'danger')
            return render_template('add_teacher.html', title='Add Teacher')
        if not re.match(r"^[0-9\-\+\s]{7,20}$", phone):
            flash('Invalid phone number.', 'danger')
            return render_template('add_teacher.html', title='Add Teacher')

        try:
            teacher = Teacher(
                name=name, 
                email=email, 
                phone=phone, 
                department_id=int(department_id) if department_id else None,
                address=address or None,
                gender=gender or None,
                date_of_birth=dob,
                joining_date=joining_date,
                office_hours=office_hours or None,
                employment_status=employment_status or None,
                designation=designation or None,
                specialization=specialization or None,
                qualification=qualification or None,
                subject_expertise=subject_expertise or None,
                max_weekly_hours=max_weekly_hours,
                pan_number=pan_number or None,
                aadhaar_number=aadhaar_number or None,
                experience_years=experience_years
            )
            db.session.add(teacher)
            db.session.commit()
            flash('Teacher has been added!', 'success')
            return redirect(url_for('teachers'))
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Failed to add teacher due to duplicate email: {email}")
            flash('Email already exists. Please use a different email.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.exception("Unexpected error adding teacher")
            flash(f'Unexpected error: {str(e)}', 'danger')
    departments = Department.query.all()
    return render_template('add_teacher.html', title='Add Teacher', departments=departments)

@app.route("/teachers/<int:teacher_id>/edit", methods=['GET', 'POST'])
@crud_required('teacher', 'update')
def edit_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    departments = Department.query.all()
    if request.method == 'POST':
        teacher.name = request.form['name']
        teacher.email = request.form['email']
        teacher.phone = request.form['phone']
        
        dept_id = request.form.get('department_id')
        teacher.department_id = int(dept_id) if dept_id else None

        teacher.address = request.form.get('address', '').strip() or None
        teacher.gender = request.form.get('gender', '').strip() or None
        teacher.office_hours = request.form.get('office_hours', '').strip() or None
        teacher.employment_status = request.form.get('employment_status', '').strip() or None
        teacher.designation = request.form.get('designation', '').strip() or None
        teacher.specialization = request.form.get('specialization', '').strip() or None
        teacher.qualification = request.form.get('qualification', '').strip() or None
        teacher.subject_expertise = request.form.get('subject_expertise', '').strip() or None
        teacher.pan_number = request.form.get('pan_number', '').strip() or None
        teacher.aadhaar_number = request.form.get('aadhaar_number', '').strip() or None
        experience_years_str = request.form.get('experience_years', '').strip()
        if experience_years_str:
            try:
                teacher.experience_years = int(experience_years_str)
            except ValueError:
                pass
        else:
            teacher.experience_years = None
        max_weekly_hours_str = request.form.get('max_weekly_hours', '').strip()
        if max_weekly_hours_str:
            try:
                teacher.max_weekly_hours = int(max_weekly_hours_str)
            except ValueError:
                flash('Max weekly hours must be an integer.', 'danger')
                return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)

        dob_str = request.form.get('date_of_birth', '').strip()
        if dob_str:
            try:
                teacher.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth.', 'danger')
                return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        else:
            teacher.date_of_birth = None

        joining_date_str = request.form.get('joining_date', '').strip()
        if joining_date_str:
            try:
                teacher.joining_date = datetime.strptime(joining_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid joining date.', 'danger')
                return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        else:
            teacher.joining_date = None

        if not teacher.name.strip():
            flash('Name is required.', 'danger')
            return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", teacher.email):
            flash('Invalid email format.', 'danger')
            return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        if not re.match(r"^[0-9\-\+\s]{7,20}$", teacher.phone):
            flash('Invalid phone number.', 'danger')
            return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        if not re.match(r"^[0-9\-\+\s]{7,20}$", teacher.phone):
            flash('Invalid phone number.', 'danger')
            return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)
        try:
            db.session.commit()
            flash('Teacher has been updated!', 'success')
            return redirect(url_for('teachers'))
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Failed to update teacher due to duplicate email: {teacher.email}")
            flash('Email already exists. Please use a different email.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.exception("Unexpected error updating teacher")
            flash(f'Unexpected error: {str(e)}', 'danger')
    return render_template('edit_teacher.html', title='Edit Teacher', teacher=teacher, departments=departments)

@app.route("/teachers/<int:teacher_id>/delete", methods=['POST'])
@crud_required('teacher', 'delete')
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    logger.info(f"Deleting teacher id={teacher_id}")
    try:
        db.session.delete(teacher)
        db.session.commit()
        flash('Teacher has been deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Unexpected error deleting teacher")
        flash(f'Unexpected error: {str(e)}', 'danger')
    return redirect(url_for('teachers'))

@app.route("/courses")
def courses():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    role = session.get('role')
    user_email = session.get('user')
    
    query = Course.query
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        # Filter courses where any of the parent's children are enrolled
        query = query.filter(Course.students.any(Student.id.in_(student_ids)))
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student:
            # Filter courses where the student is enrolled
            query = query.filter(Course.students.any(Student.id == student.id))
        else:
            query = query.filter(False)
    
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Course.name.ilike(like)))
    pagination = query.order_by(Course.name.asc()).paginate(page=page, per_page=10)
    return render_template('courses.html', courses=pagination.items, pagination=pagination, q=q, title='Courses')

@app.route("/courses/add", methods=['GET', 'POST'])
@login_required
@crud_required('course', 'create')
def add_course():
    teachers = Teacher.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        teacher_id = request.form['teacher']
        code = request.form.get('code', '').strip()
        credits_str = request.form.get('credits', '').strip()
        department_id = request.form.get('department_id')
        semester = request.form.get('semester', '').strip()
        room = request.form.get('room', '').strip()
        capacity_str = request.form.get('capacity', '').strip()
        schedule_notes = request.form.get('schedule_notes', '').strip()
        level = request.form.get('level', '').strip()
        syllabus_url = request.form.get('syllabus_url', '').strip()
        course_type = request.form.get('course_type', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        prerequisites = request.form.get('prerequisites', '').strip()
        learning_outcomes = request.form.get('learning_outcomes', '').strip()
        section_name = request.form.get('section_name', '').strip()
        capacity = None
        if capacity_str:
            try:
                capacity = int(capacity_str)
            except ValueError:
                flash('Capacity must be an integer.', 'danger')
                return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)
        
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format.', 'danger')
        
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format.', 'danger')

        logger.info(f"Adding course: {name} (teacher_id={teacher_id})")
        if not name.strip():
            flash('Name is required.', 'danger')
            return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)
        if app.config.get('COURSE_REQUIRE_CREDITS', False) and not credits_str:
            flash('Credits are required for course creation.', 'danger')
            return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)
        credits = None
        if credits_str:
            try:
                credits = int(credits_str)
                if credits < 0:
                    raise ValueError
            except ValueError:
                flash('Credits must be a non-negative integer.', 'danger')
                return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)
        try:
            tid = int(teacher_id)
        except ValueError:
            flash('Invalid teacher selection.', 'danger')
            return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)
        teacher = Teacher.query.get(tid)
        if not teacher:
            flash('Selected teacher does not exist.', 'danger')
            return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)

        course = Course(
            name=name, 
            description=description, 
            teacher_id=tid, 
            code=code or None, 
            credits=credits,
            department_id=int(department_id) if department_id else None,
            semester=semester or None,
            room=room or None,
            capacity=capacity,
            schedule_notes=schedule_notes or None,
            level=level or None,
            syllabus_url=syllabus_url or None,
            course_type=course_type or None,
            academic_year=academic_year or None,
            start_date=start_date,
            end_date=end_date,
            prerequisites=prerequisites or None,
            learning_outcomes=learning_outcomes or None,
            section_name=section_name or None,
            syllabus_progress=0
        )
        db.session.add(course)
        db.session.commit()
        flash('Course has been added!', 'success')
        return redirect(url_for('courses'))
    return render_template('add_course.html', title='Add Course', teachers=teachers, departments=departments)

@app.route('/courses/<int:course_id>/update_progress', methods=['POST'])
@login_required
@crud_required('course', 'update')
def update_course_progress(course_id):
    course = Course.query.get_or_404(course_id)
    progress = request.form.get('progress', type=int)
    if progress is not None and 0 <= progress <= 100:
        course.syllabus_progress = progress
        db.session.commit()
        flash(f'Syllabus progress updated to {progress}%', 'success')
    else:
        flash('Invalid progress value.', 'danger')
    return redirect(url_for('course_details', course_id=course_id))

@app.route("/courses/<int:course_id>/enroll", methods=['GET', 'POST'])
@crud_required('course', 'update')
def enroll_student(course_id):
    course = Course.query.get_or_404(course_id)
    students = Student.query.all()
    if request.method == 'POST':
        student_ids = request.form.getlist('students')
        logger.info(f"Enrolling students {student_ids} to course_id={course_id}")
        # Prevent duplicates and enforce capacity if defined
        already_ids = {s.id for s in course.students}
        to_add_ids = []
        for sid in student_ids:
            try:
                sid_int = int(sid)
            except Exception:
                continue
            if sid_int not in already_ids:
                to_add_ids.append(sid_int)
        capacity = course.capacity
        added = 0
        skipped = 0
        # If capacity is defined, cap additions
        if isinstance(capacity, int) and capacity >= 0:
            remaining = max(capacity - len(course.students), 0)
            to_add_ids = to_add_ids[:remaining]
        for sid_int in to_add_ids:
            student = Student.query.get(sid_int)
            if student:
                course.students.append(student)
                added += 1
            else:
                skipped += 1
        db.session.commit()
        msg = f'Enrolled {added} students.'
        if skipped or (len(student_ids) - added) > 0:
            skipped_total = skipped + max(len(student_ids) - added - skipped, 0)
            msg += f' Skipped {skipped_total} due to capacity/invalid/duplicate.'
        flash(msg, 'success' if added > 0 else 'warning')
        return redirect(url_for('courses'))
    return render_template('enroll_student.html', title='Enroll Students', course=course, students=students)

@app.route("/students/<int:student_id>/courses")
@crud_required('course', 'read')
def student_courses(student_id):
    student = Student.query.get_or_404(student_id)
    if session.get('role') == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        link = ParentStudentLink.query.filter_by(parent_username=session.get('user'), student_id=student.id).first()
        if not link:
            flash('You are not authorized to view this student.', 'danger')
            return redirect(url_for('students'))
    return render_template('student_courses.html', student=student)

@app.route("/courses/<int:course_id>")
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    role = session.get('role')
    user_email = session.get('user')
    
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        # Check if any of the parent's children are in this course
        enrolled_student_ids = [s.id for s in course.students]
        if not any(sid in enrolled_student_ids for sid in student_ids):
            flash('You are not authorized to view this course.', 'danger')
            return redirect(url_for('courses'))
            
    # Fetch photos for enrolled students
    student_emails = [s.email for s in course.students]
    photos = {}
    for photo in UserPhoto.query.filter(UserPhoto.username.in_(student_emails)).all():
        photos[photo.username] = url_for('static', filename=photo.file_path.lstrip('/'))
    return render_template('course_details.html', course=course, title='Course Details', photos=photos)

@app.route("/courses/<int:course_id>/edit", methods=['GET', 'POST'])
@crud_required('course', 'update')
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    teachers = Teacher.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        course.name = request.form['name']
        course.description = request.form['description']
        course.teacher_id = request.form['teacher']
        course.code = request.form.get('code', '').strip() or None
        
        dept_id = request.form.get('department_id')
        course.department_id = int(dept_id) if dept_id else None

        course.semester = request.form.get('semester', '').strip() or None
        course.room = request.form.get('room', '').strip() or None
        course.level = request.form.get('level', '').strip() or None
        course.syllabus_url = request.form.get('syllabus_url', '').strip() or None
        course.course_type = request.form.get('course_type', '').strip() or None
        course.academic_year = request.form.get('academic_year', '').strip() or None
        course.prerequisites = request.form.get('prerequisites', '').strip() or None
        course.learning_outcomes = request.form.get('learning_outcomes', '').strip() or None
        course.section_name = request.form.get('section_name', '').strip() or None
        capacity_str = request.form.get('capacity', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        course.schedule_notes = request.form.get('schedule_notes', '').strip() or None

        if start_date_str:
            try:
                course.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format.', 'danger')
        else:
            course.start_date = None

        if end_date_str:
            try:
                course.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format.', 'danger')
        else:
            course.end_date = None

        credits_str = request.form.get('credits', '').strip()
        if app.config.get('COURSE_REQUIRE_CREDITS', False) and not credits_str:
            flash('Credits are required for course editing.', 'danger')
            return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers)
        if credits_str:
            try:
                course.credits = int(credits_str)
                if course.credits < 0:
                    raise ValueError
            except ValueError:
                flash('Credits must be a non-negative integer.', 'danger')
                return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)
        else:
            course.credits = None
        if capacity_str:
            try:
                course.capacity = int(capacity_str)
            except ValueError:
                flash('Capacity must be an integer.', 'danger')
                return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)
        if not course.name.strip():
            flash('Name is required.', 'danger')
            return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)
        try:
            course.teacher_id = int(course.teacher_id)
        except ValueError:
            flash('Invalid teacher selection.', 'danger')
            return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)
        if not Teacher.query.get(course.teacher_id):
            flash('Selected teacher does not exist.', 'danger')
            return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)
        db.session.commit()
        flash('Course has been updated!', 'success')
        return redirect(url_for('courses'))
    return render_template('edit_course.html', title='Edit Course', course=course, teachers=teachers, departments=departments)

@app.route("/courses/<int:course_id>/delete", methods=['POST'])
@crud_required('course', 'delete')
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    logger.info(f"Deleting course id={course_id}")
    db.session.delete(course)
    db.session.commit()
    flash('Course has been deleted!', 'success')
    return redirect(url_for('courses'))

@app.route("/courses/<int:course_id>/sessions")
@crud_required('course_session', 'read')
def course_sessions(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Access check
    role = session.get('role')
    user_email = session.get('user')
    can_view = False
    if role in ('admin', 'staff', 'faculty'):
        can_view = True
    elif role == 'teacher':
        teacher = Teacher.query.filter_by(email=user_email).first()
        if teacher and teacher.id == course.teacher_id:
            can_view = True
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student in course.students:
            can_view = True
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        for s in students:
            if s in course.students:
                can_view = True
                break
    
    if not can_view:
        flash('You are not authorized to view sessions for this course.', 'danger')
        return redirect(url_for('courses'))

    # Check if user can add/edit/delete sessions
    can_edit = False
    if role == 'admin':
        can_edit = True
    elif role in ('faculty', 'teacher'):
        teacher = Teacher.query.filter_by(email=user_email).first()
        if teacher and teacher.id == course.teacher_id:
            can_edit = True

    sessions = CourseSession.query.filter_by(course_id=course_id).order_by(CourseSession.session_date.desc()).all()
    
    student_attendance = {}
    if role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student:
            att_recs = Attendance.query.filter(
                Attendance.session_id.in_([s.id for s in sessions]),
                Attendance.student_id == student.id
            ).all()
            student_attendance = {r.session_id: r.status for r in att_recs}

    return render_template('sessions.html', course=course, sessions=sessions, title='Sessions', can_edit=can_edit, student_attendance=student_attendance)

@app.route("/courses/<int:course_id>/sessions/add", methods=['GET', 'POST'])
@login_required
@crud_required('course_session', 'create')
def add_session(course_id):
    course = Course.query.get_or_404(course_id)
    role = session.get('role')
    if role in ('faculty', 'teacher'):
        current_teacher = Teacher.query.filter_by(email=session.get('user')).first()
        if not current_teacher or current_teacher.id != course.teacher_id:
            flash('You are not authorized to modify sessions for this course.', 'danger')
            return redirect(url_for('course_sessions', course_id=course_id))
    if request.method == 'POST':
        session_date_str = request.form.get('session_date', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        end_time_str = request.form.get('end_time', '').strip()
        location = request.form.get('location', '').strip()
        title = request.form.get('title', '').strip()
        try:
            d = datetime.strptime(session_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date.', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid start time format.', 'danger')

        end_time = None
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid end time format.', 'danger')

        existing = CourseSession.query.filter_by(course_id=course_id, session_date=d).first()
        if existing:
            flash('Session for this date already exists.', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        # Weekend rule
        allow_weekend = bool(app.config.get('ALLOW_WEEKEND_SESSIONS', False))
        if not allow_weekend and d.weekday() >= 5:
            flash('Weekend sessions are not allowed by policy.', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        # Governance: teacher and course load constraints
        teacher_id = course.teacher_id
        # Leave checks
        from project.models import TeacherLeave
        require_approved = bool(app.config.get('LEAVE_APPROVAL_REQUIRED', True))
        leave_q = TeacherLeave.query.filter_by(teacher_id=teacher_id).filter(TeacherLeave.start_date <= d, TeacherLeave.end_date >= d)
        if require_approved:
            leave_q = leave_q.filter(TeacherLeave.approved == True)
        if leave_q.first():
            flash('Teacher is on leave for the selected date.', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        # Day constraints: sessions taught by teacher on this date
        day_count = CourseSession.query.join(Course).filter(Course.teacher_id == teacher_id, CourseSession.session_date == d).count()
        max_per_day = int(app.config.get('TEACHER_MAX_SESSIONS_PER_DAY', 4))
        if day_count >= max_per_day:
            flash(f'Teacher daily session limit reached ({max_per_day}).', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        # Week constraints: compute week start/end
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)
        week_count_teacher = CourseSession.query.join(Course).filter(Course.teacher_id == teacher_id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
        max_per_week_teacher = int(app.config.get('TEACHER_MAX_SESSIONS_PER_WEEK', 20))
        if week_count_teacher >= max_per_week_teacher:
            flash(f'Teacher weekly session limit reached ({max_per_week_teacher}).', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        week_count_course = CourseSession.query.filter(CourseSession.course_id == course_id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end).count()
        max_per_week_course = int(app.config.get('COURSE_MAX_SESSIONS_PER_WEEK', 10))
        if week_count_course >= max_per_week_course:
            flash(f'Course weekly session limit reached ({max_per_week_course}).', 'danger')
            return render_template('add_session.html', course=course, title='Add Session')
        # Lab/Project spacing rules (simple keyword-based)
        title_lower = title.lower()
        lab_kw = (app.config.get('LAB_SESSION_KEYWORD') or 'Lab').lower()
        proj_kw = (app.config.get('PROJECT_SESSION_KEYWORD') or 'Project').lower()
        if lab_kw and lab_kw in title_lower:
            min_gap = int(app.config.get('LAB_MIN_SPACING_DAYS', 3))
            last_lab = CourseSession.query.filter(CourseSession.course_id == course_id, CourseSession.title.ilike('%' + lab_kw + '%')).order_by(CourseSession.session_date.desc()).first()
            if last_lab and (d - last_lab.session_date).days < min_gap:
                flash(f'Lab sessions must be spaced at least {min_gap} days apart.', 'danger')
                return render_template('add_session.html', course=course, title='Add Session')
        if proj_kw and proj_kw in title_lower:
            min_gap_p = int(app.config.get('PROJECT_MIN_SPACING_DAYS', 7))
            last_proj = CourseSession.query.filter(CourseSession.course_id == course_id, CourseSession.title.ilike('%' + proj_kw + '%')).order_by(CourseSession.session_date.desc()).first()
            if last_proj and (d - last_proj.session_date).days < min_gap_p:
                flash(f'Project sessions must be spaced at least {min_gap_p} days apart.', 'danger')
                return render_template('add_session.html', course=course, title='Add Session')
        s = CourseSession(
            course_id=course_id, 
            session_date=d, 
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location or None
        )
        db.session.add(s)
        db.session.commit()
        flash('Session created.', 'success')
        return redirect(url_for('course_sessions', course_id=course_id))
    return render_template('add_session.html', course=course, title='Add Session')

@app.route("/sessions/<int:session_id>/edit", methods=['GET', 'POST'])
@crud_required('course_session', 'update')
def edit_session(session_id):
    s = CourseSession.query.get_or_404(session_id)
    course = s.course
    role = session.get('role')
    if role in ('faculty', 'teacher'):
        current_teacher = Teacher.query.filter_by(email=session.get('user')).first()
        if not current_teacher or current_teacher.id != course.teacher_id:
            flash('You are not authorized to modify sessions for this course.', 'danger')
            return redirect(url_for('course_sessions', course_id=course.id))
    if request.method == 'POST':
        session_date_str = request.form.get('session_date', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        end_time_str = request.form.get('end_time', '').strip()
        location = request.form.get('location', '').strip()
        title = request.form.get('title', '').strip()
        try:
            d = datetime.strptime(session_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date.', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid start time format.', 'danger')

        end_time = None
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid end time format.', 'danger')

        existing = CourseSession.query.filter_by(course_id=course.id, session_date=d).first()
        if existing and existing.id != s.id:
            flash('Another session for this date already exists.', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        # Governance checks similar to add_session
        teacher_id = course.teacher_id
        day_count = CourseSession.query.join(Course).filter(Course.teacher_id == teacher_id, CourseSession.session_date == d, CourseSession.id != s.id).count()
        max_per_day = int(app.config.get('TEACHER_MAX_SESSIONS_PER_DAY', 4))
        if day_count >= max_per_day:
            flash(f'Teacher daily session limit reached ({max_per_day}).', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)
        week_count_teacher = CourseSession.query.join(Course).filter(Course.teacher_id == teacher_id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end, CourseSession.id != s.id).count()
        max_per_week_teacher = int(app.config.get('TEACHER_MAX_SESSIONS_PER_WEEK', 20))
        if week_count_teacher >= max_per_week_teacher:
            flash(f'Teacher weekly session limit reached ({max_per_week_teacher}).', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        week_count_course = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.session_date >= week_start, CourseSession.session_date <= week_end, CourseSession.id != s.id).count()
        max_per_week_course = int(app.config.get('COURSE_MAX_SESSIONS_PER_WEEK', 10))
        if week_count_course >= max_per_week_course:
            flash(f'Course weekly session limit reached ({max_per_week_course}).', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        # Weekend rule
        allow_weekend = bool(app.config.get('ALLOW_WEEKEND_SESSIONS', False))
        if not allow_weekend and d.weekday() >= 5:
            flash('Weekend sessions are not allowed by policy.', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        # Leave checks
        from project.models import TeacherLeave
        require_approved = bool(app.config.get('LEAVE_APPROVAL_REQUIRED', True))
        leave_q = TeacherLeave.query.filter_by(teacher_id=course.teacher_id).filter(TeacherLeave.start_date <= d, TeacherLeave.end_date >= d)
        if require_approved:
            leave_q = leave_q.filter(TeacherLeave.approved == True)
        if leave_q.first():
            flash('Teacher is on leave for the selected date.', 'danger')
            return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        title_lower = title.lower()
        lab_kw = (app.config.get('LAB_SESSION_KEYWORD') or 'Lab').lower()
        proj_kw = (app.config.get('PROJECT_SESSION_KEYWORD') or 'Project').lower()
        if lab_kw and lab_kw in title_lower:
            min_gap = int(app.config.get('LAB_MIN_SPACING_DAYS', 3))
            last_lab = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + lab_kw + '%'), CourseSession.id != s.id).order_by(CourseSession.session_date.desc()).first()
            if last_lab and (d - last_lab.session_date).days < min_gap:
                flash(f'Lab sessions must be spaced at least {min_gap} days apart.', 'danger')
                return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        if proj_kw and proj_kw in title_lower:
            min_gap_p = int(app.config.get('PROJECT_MIN_SPACING_DAYS', 7))
            last_proj = CourseSession.query.filter(CourseSession.course_id == course.id, CourseSession.title.ilike('%' + proj_kw + '%'), CourseSession.id != s.id).order_by(CourseSession.session_date.desc()).first()
            if last_proj and (d - last_proj.session_date).days < min_gap_p:
                flash(f'Project sessions must be spaced at least {min_gap_p} days apart.', 'danger')
                return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)
        s.session_date = d
        s.title = title
        s.start_time = start_time
        s.end_time = end_time
        s.location = location or None
        db.session.commit()
        flash('Session updated.', 'success')
        return redirect(url_for('course_sessions', course_id=course.id))
    return render_template('add_session.html', course=course, title='Edit Session', session_obj=s)

@app.route("/sessions/<int:session_id>/delete", methods=['POST'])
@crud_required('course_session', 'delete')
def delete_session(session_id):
    s = CourseSession.query.get_or_404(session_id)
    course_id = s.course_id
    Attendance.query.filter_by(session_id=session_id).delete()
    db.session.delete(s)
    db.session.commit()
    flash('Session deleted.', 'success')
    return redirect(url_for('course_sessions', course_id=course_id))

@app.route("/attendance/daily")
@login_required
@crud_required('attendance', 'read')
def daily_attendance():
    today = datetime.utcnow().date()
    # Filter sessions for today. If teacher/faculty, only show their courses.
    role = session.get('role')
    if role in ('faculty', 'teacher'):
        teacher = Teacher.query.filter_by(email=session.get('user')).first()
        if teacher:
            sessions_today = CourseSession.query.join(Course).filter(
                CourseSession.session_date == today,
                Course.teacher_id == teacher.id
            ).all()
            courses = Course.query.filter_by(teacher_id=teacher.id).all()
        else:
            sessions_today = []
            courses = []
    else:
        sessions_today = CourseSession.query.filter_by(session_date=today).all()
        courses = Course.query.all()
        
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('daily_attendance.html', sessions=sessions_today, courses=courses, departments=departments, today=today, title='Daily Attendance')

@app.route("/attendance/quick_session", methods=['POST'])
@login_required
@crud_required('attendance', 'create')
def add_session_today():
    course_id = request.form.get('course_id')
    title = request.form.get('title')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    
    today = datetime.utcnow().date()
    
    # Check if session already exists for this course today
    existing = CourseSession.query.filter_by(course_id=course_id, session_date=today).first()
    if existing:
        flash('A session already exists for this course today.', 'info')
        return redirect(url_for('mark_attendance', session_id=existing.id))
    
    from datetime import datetime as dt
    start_time = dt.strptime(start_time_str, '%H:%M').time() if start_time_str else None
    end_time = dt.strptime(end_time_str, '%H:%M').time() if end_time_str else None
    
    new_session = CourseSession(
        course_id=course_id,
        session_date=today,
        title=title,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_session)
    db.session.commit()
    
    return redirect(url_for('mark_attendance', session_id=new_session.id))

@app.route("/sessions/<int:session_id>/attendance", methods=['GET', 'POST'])
@crud_required('attendance', 'create')
def mark_attendance(session_id):
    session_obj = CourseSession.query.get_or_404(session_id)
    course = session_obj.course
    
    # Ownership check
    role = session.get('role')
    if role in ('faculty', 'teacher'):
        current_teacher = Teacher.query.filter_by(email=session.get('user')).first()
        if not current_teacher or current_teacher.id != course.teacher_id:
            flash('You are not authorized to mark attendance for this course.', 'danger')
            return redirect(url_for('course_sessions', course_id=course.id))

    students = course.students
    if request.method == 'POST':
        # Governance: cutoff for marking attendance (non-admins)
        cutoff_days = int(app.config.get('ATTENDANCE_MARKING_CUTOFF_DAYS', 30))
        if session.get('role') != 'admin':
            if (datetime.today().date() - session_obj.session_date).days > cutoff_days:
                flash('Attendance window has closed for this session.', 'danger')
                return redirect(url_for('course_sessions', course_id=course.id))
        current_user_email = session.get('user')
        for student in students:
            status_val = request.form.get(f'status_{student.id}', 'absent')
            if status_val not in ('present', 'absent', 'late', 'excused'):
                status_val = 'absent'
            remarks_val = request.form.get(f'remarks_{student.id}', '').strip()
            att = Attendance.query.filter_by(session_id=session_id, student_id=student.id).first()
            if not att:
                att = Attendance(
                    session_id=session_id, 
                    student_id=student.id, 
                    status=status_val, 
                    remarks=remarks_val or None,
                    marked_by=current_user_email,
                    marked_at=datetime.utcnow()
                )
                db.session.add(att)
            else:
                if app.config.get('ATTENDANCE_ALLOW_EDIT', True):
                    att.status = status_val
                    att.remarks = remarks_val or None
                    att.marked_by = current_user_email
                    att.marked_at = datetime.utcnow()
        db.session.commit()
        flash('Attendance saved.', 'success')
        return redirect(url_for('course_sessions', course_id=course.id))
    existing_records = Attendance.query.filter_by(session_id=session_id).all()
    existing_status = {a.student_id: a.status for a in existing_records}
    existing_remarks = {a.student_id: (a.remarks or '') for a in existing_records}

    # Fetch photos for students
    student_emails = [s.email for s in students]
    photos = {}
    for photo in UserPhoto.query.filter(UserPhoto.username.in_(student_emails)).all():
        photos[photo.username] = url_for('static', filename=photo.file_path.lstrip('/'))

    return render_template('mark_attendance.html', course=course, course_session=session_obj, students=students, existing=existing_status, existing_remarks=existing_remarks, title='Mark Attendance', photos=photos)

@app.route("/sessions/<int:session_id>/report")
@login_required
def attendance_report(session_id):
    session_obj = CourseSession.query.get_or_404(session_id)
    course = session_obj.course
    
    # Access check: admin, staff, or course teacher, or student/parent linked to course
    role = session.get('role')
    user_email = session.get('user')
    
    can_view = False
    if role in ('admin', 'staff', 'faculty'):
        can_view = True
    elif role == 'teacher':
        teacher = Teacher.query.filter_by(email=user_email).first()
        if teacher and teacher.id == course.teacher_id:
            can_view = True
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student in course.students:
            can_view = True
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        for s in students:
            if s in course.students:
                can_view = True
                break
    
    if not can_view:
        flash('You are not authorized to view this report.', 'danger')
        return redirect(url_for('course_sessions', course_id=course.id))

    records = Attendance.query.filter_by(session_id=session_id).all()
    present = [r for r in records if r.status == 'present']
    late = [r for r in records if r.status == 'late']
    excused = [r for r in records if r.status == 'excused']
    absent = [r for r in records if r.status == 'absent']
    
    total = len(records)
    attendance_rate = (len(present) + len(late)) / total * 100 if total > 0 else 0

    return render_template('attendance_report.html', 
                           course=course, 
                           course_session=session_obj, 
                           present=present, 
                           late=late,
                           excused=excused,
                           absent=absent, 
                           total=total,
                           attendance_rate=attendance_rate,
                           title='Attendance Report')

@app.route("/attendance/low_alerts")
@login_required
@crud_required('attendance', 'read')
def low_attendance_alerts():
    course_id = request.args.get('course_id', type=int)
    threshold = request.args.get('threshold', 75.0, type=float)
    
    courses = Course.query.all()
    
    alerts = []
    course = None
    if course_id:
        course = Course.query.get_or_404(course_id)
        for student in course.students:
            total_sessions = CourseSession.query.filter_by(course_id=course_id).count()
            if total_sessions == 0:
                continue
                
            attendance_count = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.session_id.in_([s.id for s in course.sessions]),
                Attendance.status.in_(['present', 'late'])
            ).count()
            
            rate = (attendance_count / total_sessions) * 100
            if rate < threshold:
                alerts.append({
                    'student': student,
                    'rate': rate,
                    'total': total_sessions,
                    'attended': attendance_count
                })
            
    return render_template('low_attendance_alerts.html', courses=courses, course=course, alerts=alerts, threshold=threshold, title='Low Attendance Alerts')

@app.route("/courses/notify_low_attendance", methods=['POST'])
@login_required
@crud_required('attendance', 'update')
def notify_low_attendance():
    course_id = request.form.get('course_id', type=int)
    if not course_id:
        flash('Course ID is required.', 'danger')
        return redirect(url_for('low_attendance_alerts'))
        
    course = Course.query.get_or_404(course_id)
    threshold = request.form.get('threshold', 75.0, type=float)
    
    notified_count = 0
    for student in course.students:
        total_sessions = CourseSession.query.filter_by(course_id=course_id).count()
        if total_sessions == 0:
            continue
            
        attendance_count = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in course.sessions]),
            Attendance.status.in_(['present', 'late'])
        ).count()
        
        rate = (attendance_count / total_sessions) * 100
        if rate < threshold:
            # We assume a Notification model exists or use flash for demo
            try:
                from project.models import Notification
                if student.guardian_email:
                    notif = Notification(
                        recipient_type='parent',
                        recipient_id=student.guardian_email,
                        title=f"Low Attendance Alert: {student.name}",
                        message=f"Dear Parent, your ward {student.name}'s attendance in {course.name} is {rate:.1f}%, which is below the required threshold of {threshold}%."
                    )
                    db.session.add(notif)
                    notified_count += 1
                
                notif_stu = Notification(
                    recipient_type='student',
                    recipient_id=student.email,
                    title=f"Low Attendance Alert: {course.name}",
                    message=f"Your attendance in {course.name} is {rate:.1f}%, which is below the required threshold of {threshold}%."
                )
                db.session.add(notif_stu)
            except ImportError:
                # If Notification model doesn't exist yet, we just flash a message for now
                pass

    db.session.commit()
    flash(f'Sent {notified_count} alerts to parents/students.', 'success')
    return redirect(url_for('low_attendance_alerts', course_id=course_id, threshold=threshold))

@app.route("/attendance/monthly_report")
@login_required
@crud_required('attendance', 'read')
def monthly_attendance_report():
    course_id = request.args.get('course_id', type=int)
    month = request.args.get('month', datetime.utcnow().month, type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)
    
    courses = Course.query.all()
    course = None
    report_data = []
    sessions = []
    
    if course_id:
        course = Course.query.get_or_404(course_id)
        from sqlalchemy import extract
        sessions = CourseSession.query.filter(
            CourseSession.course_id == course_id,
            extract('month', CourseSession.session_date) == month,
            extract('year', CourseSession.session_date) == year
        ).all()
        
        for student in course.students:
            row = {'student': student, 'attendance': []}
            present_count = 0
            for session_obj in sessions:
                att = Attendance.query.filter_by(session_id=session_obj.id, student_id=student.id).first()
                status = att.status if att else '-'
                row['attendance'].append(status)
                if status in ('present', 'late'):
                    present_count += 1
            row['rate'] = (present_count / len(sessions) * 100) if sessions else 0
            report_data.append(row)
            
    return render_template('monthly_attendance_report.html', courses=courses, course=course, report_data=report_data, sessions=sessions, month=month, year=year, title='Monthly Attendance Report')

@app.route('/exams')
@login_required
@crud_required('exam', 'read')
def exams():
    q = request.args.get('q', '').strip()
    dept_id = request.args.get('department_id', '').strip()
    role = session.get('role')
    user_email = session.get('user')
    
    query = Exam.query.join(Course)
    
    if role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student.department_id:
            query = query.filter(Course.department_id == student.department_id)
        elif student:
            # Fallback to enrolled courses if department not set
            query = query.filter(Course.students.any(Student.id == student.id))
            
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        dept_ids = [s.department_id for s in students if s.department_id]
        if dept_ids:
            query = query.filter(Course.department_id.in_(dept_ids))
        else:
            query = query.filter(Course.students.any(Student.id.in_(student_ids)))
    
    # Apply department filter for staff/admin/faculty
    elif dept_id:
        try:
            query = query.filter(Course.department_id == int(dept_id))
        except ValueError:
            pass

    if q:
        exams_list = query.filter(
            (Exam.name.ilike(f'%{q}%')) | (Course.name.ilike(f'%{q}%'))
        ).all()
    else:
        exams_list = query.order_by(Exam.exam_date.desc()).all()
    
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('exams.html', 
                           exams=exams_list, 
                           q=q, 
                           departments=departments,
                           selected_dept_id=dept_id,
                           title='Exams')

@app.route('/exams/add', methods=['GET', 'POST'])
@login_required
@crud_required('exam', 'create')
def add_exam():
    courses = Course.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        name = request.form['name']
        course_id = request.form['course_id']
        exam_date_str = request.form['exam_date']
        location = request.form['location']
        max_marks = request.form.get('max_marks', 100)
        
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%dT%H:%M')
        
        new_exam = Exam(
            name=name, 
            course_id=course_id, 
            exam_date=exam_date, 
            location=location, 
            max_marks=max_marks
        )
        db.session.add(new_exam)
        db.session.commit()
        flash('Exam scheduled successfully.', 'success')
        return redirect(url_for('exams'))
        
    return render_template('add_exam.html', courses=courses, departments=departments, title='Schedule Exam')

@app.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@crud_required('exam', 'update')
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    courses = Course.query.all()
    departments = Department.query.all()
    if request.method == 'POST':
        exam.name = request.form['name']
        exam.course_id = request.form['course_id']
        exam_date_str = request.form['exam_date']
        exam.location = request.form['location']
        exam.max_marks = request.form.get('max_marks', 100)
        
        exam.exam_date = datetime.strptime(exam_date_str, '%Y-%m-%dT%H:%M')
        
        db.session.commit()
        flash('Exam updated successfully.', 'success')
        return redirect(url_for('exams'))
        
    return render_template('edit_exam.html', exam=exam, courses=courses, departments=departments, title='Edit Exam')

@app.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@crud_required('exam', 'delete')
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted successfully.', 'success')
    return redirect(url_for('exams'))

@app.route('/exams/<int:exam_id>/marks', methods=['GET', 'POST'])
@login_required
@crud_required('grade', 'update')
def exam_marks(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    course = exam.course
    students = course.students
    
    if request.method == 'POST':
        for student in students:
            score = request.form.get(f'score_{student.id}')
            if score:
                # Find existing grade or create new
                grade = Grade.query.filter_by(student_id=student.id, exam_id=exam_id).first()
                if not grade:
                    grade = Grade(student_id=student.id, course_id=course.id, exam_id=exam_id)
                    db.session.add(grade)
                
                grade.score = float(score)
                # Simple point calculation (can be improved)
                grade.points = (grade.score / exam.max_marks) * 10
                if grade.points >= 9: grade.grade_letter = 'A+'
                elif grade.points >= 8: grade.grade_letter = 'A'
                elif grade.points >= 7: grade.grade_letter = 'B'
                elif grade.points >= 6: grade.grade_letter = 'C'
                elif grade.points >= 5: grade.grade_letter = 'D'
                else: grade.grade_letter = 'F'
                
        db.session.commit()
        flash('Marks updated successfully.', 'success')
        return redirect(url_for('exams'))
        
    # Get existing grades for display
    existing_grades = {g.student_id: g.score for g in Grade.query.filter_by(exam_id=exam_id).all()}
    return render_template('exam_marks.html', exam=exam, students=students, grades=existing_grades, title='Enter Marks')

@app.route("/students/<int:student_id>/hall_ticket")
@login_required
def hall_ticket(student_id):
    student = Student.query.get_or_404(student_id)
    # Access check: admin, staff, or the student themselves
    role = session.get('role')
    user_email = session.get('user')
    if role == 'student' and student.email != user_email:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))
        
    if student.department_id:
        exams = Exam.query.join(Course).filter(Course.department_id == student.department_id).all()
    else:
        exams = Exam.query.join(Course).filter(Course.students.contains(student)).all()
    return render_template('hall_ticket.html', student=student, exams=exams, title='Hall Ticket')

@app.route("/students/<int:student_id>/calculate_gpa")
@login_required
@crud_required('grade', 'read')
def calculate_gpa(student_id):
    student = Student.query.get_or_404(student_id)
    grades = Grade.query.filter_by(student_id=student_id).all()
    
    total_points = 0
    total_credits = 0
    
    for g in grades:
        course = Course.query.get(g.course_id)
        if course and course.credits:
            total_points += (g.points or 0) * course.credits
            total_credits += course.credits
            
    gpa = total_points / total_credits if total_credits > 0 else 0
    return jsonify({'student_id': student_id, 'gpa': round(gpa, 2)})

@app.route("/students/<int:student_id>/marksheet")
@login_required
def marksheet(student_id):
    student = Student.query.get_or_404(student_id)
    # Access check
    role = session.get('role')
    user_email = session.get('user')
    if role == 'student' and student.email != user_email:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))
        
    grades = Grade.query.filter_by(student_id=student_id).filter(Grade.exam_id == None).all()
    
    # Group by semester
    semesters = {}
    for g in grades:
        sem = g.semester or 1
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append(g)
        
    return render_template('marksheet.html', student=student, semesters=semesters, today=datetime.utcnow(), title='Digital Marksheet')

@app.route("/students/<int:student_id>/degree")
@login_required
def degree_certificate(student_id):
    student = Student.query.get_or_404(student_id)
    # Access check
    role = session.get('role')
    user_email = session.get('user')
    if role == 'student' and student.email != user_email:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))
        
    # Calculate CGPA
    grades = Grade.query.filter_by(student_id=student_id).all()
    total_points = 0
    total_credits = 0
    for g in grades:
        # Only count final grades (no exam_id) for CGPA
        if g.exam_id is None and g.course and g.course.credits:
            total_points += (g.points or 0) * g.course.credits
            total_credits += g.course.credits
    
    cgpa = total_points / total_credits if total_credits > 0 else 0
    
    # Requirements check (example: 120 credits and CGPA > 2.0)
    # Since it's an ERP, we'll just show it if requested for now
    
    return render_template('degree.html', student=student, cgpa=round(cgpa, 2), today=datetime.utcnow(), title='Digital Degree')

@app.route("/sessions/<int:session_id>/attendance.csv")
@login_required
def session_attendance_csv(session_id):
    session_obj = CourseSession.query.get_or_404(session_id)
    course = session_obj.course
    
    # Access check (same logic as report)
    role = session.get('role')
    user_email = session.get('user')
    can_access = False
    if role in ('admin', 'staff', 'faculty'):
        can_access = True
    elif role == 'teacher':
        teacher = Teacher.query.filter_by(email=user_email).first()
        if teacher and teacher.id == course.teacher_id:
            can_access = True
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student in course.students:
            can_access = True
    elif role == 'parent':
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        for s in students:
            if s in course.students:
                can_access = True
                break
    
    if not can_access:
        flash('You are not authorized to download this report.', 'danger')
        return redirect(url_for('course_sessions', course_id=course.id))

    records = Attendance.query.filter_by(session_id=session_id).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Student", "Email", "Status", "Remarks", "Marked By", "Marked At", "Session Date", "Course"]) 
    for r in records:
        s = r.student
        writer.writerow([
            s.name, 
            s.email, 
            r.status.title(), 
            r.remarks or '',
            r.marked_by or '',
            r.marked_at.strftime('%Y-%m-%d %H:%M:%S') if r.marked_at else '',
            session_obj.session_date.isoformat(), 
            session_obj.course.name
        ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment; filename=session_{session_id}_attendance.csv"})

@app.route("/courses/<int:course_id>/attendance.csv")
@crud_required('attendance', 'read')
def course_attendance_csv(course_id):
    course = Course.query.get_or_404(course_id)
    sessions = CourseSession.query.filter_by(course_id=course_id).order_by(CourseSession.session_date.asc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Date", "Session Title", "Student", "Email", "Status", "Remarks", "Marked By", "Marked At"]) 
    for s in sessions:
        records = Attendance.query.filter_by(session_id=s.id).all()
        for r in records:
            st = r.student
            writer.writerow([
                s.session_date.isoformat(), 
                s.title or 'Session',
                st.name, 
                st.email, 
                r.status.title(), 
                r.remarks or '',
                r.marked_by or '',
                r.marked_at.strftime('%Y-%m-%d %H:%M:%S') if r.marked_at else ''
            ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment; filename=course_{course_id}_attendance.csv"})

@app.route("/courses/<int:course_id>/roster.csv")
def course_roster_csv(course_id):
    course = Course.query.get_or_404(course_id)
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Student", "Email", "Phone"]) 
    for s in course.students:
        writer.writerow([s.name, s.email, s.phone])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment; filename=course_{course_id}_roster.csv"})

@app.route("/courses/<int:course_id>/attendance/summary")
def course_attendance_summary(course_id):
    course = Course.query.get_or_404(course_id)
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date range.', 'danger')
    q = CourseSession.query.filter_by(course_id=course_id)
    if start_date:
        q = q.filter(CourseSession.session_date >= start_date)
    if end_date:
        q = q.filter(CourseSession.session_date <= end_date)
    sessions = q.order_by(CourseSession.session_date.asc()).all()
    session_ids = [s.id for s in sessions]
    stats = {}
    for st in course.students:
        stats[st.id] = {'student': st, 'present': 0, 'late': 0, 'excused': 0, 'absent': 0, 'total': len(sessions)}
    if session_ids:
        recs = Attendance.query.filter(Attendance.session_id.in_(session_ids)).all()
        for r in recs:
            if r.student_id in stats:
                if r.status in stats[r.student_id]:
                    stats[r.student_id][r.status] += 1
                elif r.status == 'present': # fallback for old data
                    stats[r.student_id]['present'] += 1
                else:
                    stats[r.student_id]['absent'] += 1
    return render_template('course_attendance_summary.html', course=course, sessions=sessions, stats=stats, start_date=start_date_str, end_date=end_date_str, title='Attendance Summary')

@app.route("/students/<int:student_id>/attendance")
@crud_required('attendance', 'read')
def student_attendance_summary(student_id):
    student = Student.query.get_or_404(student_id)
    if session.get('role') == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        link = ParentStudentLink.query.filter_by(parent_username=session.get('user'), student_id=student.id).first()
        if not link:
            flash('You are not authorized to view this student.', 'danger')
            return redirect(url_for('students'))
    data = []
    for course in student.courses:
        sessions = CourseSession.query.filter_by(course_id=course.id).all()
        total = len(sessions)
        session_ids = [s.id for s in sessions]
        present = 0
        late = 0
        excused = 0
        absent = 0
        if session_ids:
            recs = Attendance.query.filter(Attendance.session_id.in_(session_ids), Attendance.student_id == student.id).all()
            for r in recs:
                if r.status == 'present': present += 1
                elif r.status == 'late': late += 1
                elif r.status == 'excused': excused += 1
                else: absent += 1
        data.append({
            'course': course, 
            'present': present, 
            'late': late,
            'excused': excused,
            'absent': absent,
            'total': total
        })
    
    # Fetch student photo
    photo = UserPhoto.query.filter_by(username=student.email).first()
    photo_url = url_for('static', filename=photo.file_path.lstrip('/')) if photo else None
    
    return render_template('student_attendance_summary.html', student=student, data=data, title='Student Attendance', photo_url=photo_url)

@app.route("/courses/<int:course_id>/unenroll/<int:student_id>", methods=['POST'])
@crud_required('course', 'update')
def unenroll_student(course_id, student_id):
    course = Course.query.get_or_404(course_id)
    student = Student.query.get_or_404(student_id)
    if student in course.students:
        course.students.remove(student)
        db.session.commit()
        flash('Student has been unenrolled!', 'success')
    else:
        flash('Student not enrolled.', 'warning')
    return redirect(url_for('course_details', course_id=course_id))

@app.route("/students/<int:student_id>/drop/<int:course_id>", methods=['POST'])
@crud_required('course', 'update')
def drop_course(student_id, course_id):
    student = Student.query.get_or_404(student_id)
    course = Course.query.get_or_404(course_id)
    if course in student.courses:
        student.courses.remove(course)
        db.session.commit()
        flash('Course dropped!', 'success')
    else:
        flash('Course not found.', 'warning')
    return redirect(url_for('student_courses', student_id=student_id))

@app.route("/healthz")
def healthz():
    try:
        student_count = Student.query.count()
        teacher_count = Teacher.query.count()
        course_count = Course.query.count()
        return jsonify({"status":"ok","students":student_count,"teachers":teacher_count,"courses":course_count}), 200
    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({"status":"error","message":str(e)}), 500

@app.errorhandler(404)
def handle_404(error):
    return "<h1>404 Not Found</h1>", 404

@app.errorhandler(500)
def handle_500(error):
    logger.exception("Unhandled exception")
    return "<h1>500 Internal Server Error</h1>", 500
@app.route('/admin/audit')
@crud_required('audit', 'read')
def admin_audit():
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '').strip()
    actor = request.args.get('actor', '').strip()
    target = request.args.get('target', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    # Build query with filters
    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor_username == actor)
    if target:
        q = q.filter(AuditLog.target == target)
    # Date range filtering (inclusive)
    from datetime import datetime, timedelta
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            q = q.filter(AuditLog.created_at >= start_dt)
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(AuditLog.created_at < end_dt)
    except Exception:
        pass

    q = q.order_by(AuditLog.created_at.desc())
    pagination = q.paginate(page=page, per_page=20)
    return render_template(
        'audit.html',
        title='Audit Logs',
        logs=pagination.items,
        pagination=pagination,
        action=action,
        actor=actor,
        target=target,
        start_date=start_date,
        end_date=end_date,
    )

@app.route('/admin/audit/export')
@crud_required('audit', 'read')
def admin_audit_export():
    action = request.args.get('action', '').strip()
    actor = request.args.get('actor', '').strip()
    target = request.args.get('target', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor_username == actor)
    if target:
        q = q.filter(AuditLog.target == target)
    from datetime import datetime, timedelta
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            q = q.filter(AuditLog.created_at >= start_dt)
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(AuditLog.created_at < end_dt)
    except Exception:
        pass

    logs = q.order_by(AuditLog.created_at.desc()).all()
    # Prepare CSV
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['created_at','action','actor_username','actor_role','target','details'])
    for l in logs:
        writer.writerow([
            l.created_at,
            l.action or '',
            l.actor_username or '',
            l.actor_role or '',
            l.target or '',
            (l.details or '').replace('\n',' '),
        ])
    csv_data = buf.getvalue()
    buf.close()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename="audit_logs.csv"'}
    )
# --- Finance: Fees ---
@app.route('/finance/fees', methods=['GET', 'POST'])
@crud_required('fee', 'read')
def finance_fees():
    role = session.get('role')
    user_email = session.get('user')
    
    if request.method == 'POST':
        # Ensure only authorized roles can record payments
        if role not in CRUD_PERMISSIONS['fee']['create']:
            flash('You are not authorized to record payments.', 'danger')
            return redirect(url_for('finance_fees'))
            
        try:
            student_id = int(request.form.get('student_id'))
            amount = float(request.form.get('amount'))
            method = (request.form.get('method') or '').strip()
            reference = (request.form.get('reference') or '').strip()
        except Exception:
            flash('Invalid payment details.', 'danger')
            return redirect(url_for('finance_fees'))
        student = Student.query.get(student_id)
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('finance_fees'))
            
        # Check partial payments policy
        if not app.config.get('FINANCE_ALLOW_PARTIAL_PAYMENTS', True):
            # Calculate outstanding for THIS student
            invoices_total = db.session.query(db.func.sum(Invoice.amount_due)).filter_by(student_id=student_id).scalar() or 0.0
            payments_total = db.session.query(db.func.sum(FeePayment.amount)).filter_by(student_id=student_id).scalar() or 0.0
            outstanding = max(invoices_total - payments_total, 0.0)
            
            if amount < outstanding:
                flash(f'Partial payments are not allowed. Full outstanding amount is {outstanding} {app.config.get("DEFAULT_CURRENCY")}.', 'danger')
                return redirect(url_for('finance_fees'))

        payment = FeePayment(student_id=student_id, amount=amount, method=method, reference=reference, currency=(app.config.get('DEFAULT_CURRENCY') or 'USD'))
        db.session.add(payment)
        # Update or create account (store cumulative paid amount)
        acc = FeeAccount.query.filter_by(student_id=student_id).first()
        if not acc:
            acc = FeeAccount(student_id=student_id, balance=0.0)
            db.session.add(acc)
        acc.balance = (acc.balance or 0.0) + amount
        # Audit log
        try:
            db.session.flush()
            db.session.add(AuditLog(
                action='fee_payment',
                actor_username=session.get('user'),
                actor_role=session.get('role'),
                target=f'student:{student_id}',
                details=f'amount={amount}, method={method}, reference={reference}'
            ))
        except Exception:
            logger.warning('AuditLog fee_payment failed')
        db.session.commit()
        flash('Payment recorded successfully.', 'success')
        return redirect(url_for('finance_fees'))

    # GET: list students with accounts and recent payments
    query = Student.query
    if role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        query = query.filter(Student.id.in_(student_ids))
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student:
            student_ids = [student.id]
            query = query.filter(Student.id == student.id)
        else:
            student_ids = []
            query = query.filter(False)
    
    students = query.order_by(Student.name.asc()).all()
    accounts = {a.student_id: a for a in FeeAccount.query.all()}
    
    # Outstanding = sum invoices - sum payments
    if role in ['parent', 'student']:
        invoices = Invoice.query.filter(Invoice.student_id.in_(student_ids)).all()
        payments = FeePayment.query.filter(FeePayment.student_id.in_(student_ids)).all()
        recent_payments = FeePayment.query.filter(FeePayment.student_id.in_(student_ids)).order_by(FeePayment.paid_at.desc()).limit(10).all()
    else:
        invoices = Invoice.query.all()
        payments = FeePayment.query.all()
        recent_payments = FeePayment.query.order_by(FeePayment.paid_at.desc()).limit(10).all()
        
    paid_totals = {}
    for p in payments:
        paid_totals[p.student_id] = paid_totals.get(p.student_id, 0.0) + (p.amount or 0.0)
    due_totals = {}
    for inv in invoices:
        due_totals[inv.student_id] = due_totals.get(inv.student_id, 0.0) + (inv.amount_due or 0.0)
    outstanding = {sid: max(due_totals.get(sid, 0.0) - paid_totals.get(sid, 0.0), 0.0) for sid in set(list(due_totals.keys()) + list(paid_totals.keys()))}
    
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('fees.html', title='Fees', students=students, departments=departments, accounts=accounts, recent_payments=recent_payments, outstanding=outstanding)

@app.route('/finance/invoices/create', methods=['GET', 'POST'])
@crud_required('fee', 'create')
def create_invoice():
    students = Student.query.order_by(Student.name.asc()).all()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        amount_due_str = request.form.get('amount_due')
        tax_percent_str = request.form.get('tax_percent', '0')
        discount_percent_str = request.form.get('discount_percent', '0')
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        currency = (request.form.get('currency') or (app.config.get('DEFAULT_CURRENCY') or 'USD')).strip()
        reference = (request.form.get('reference') or '').strip()
        
        try:
            sid = int(student_id)
            base_amount = float(amount_due_str)
            tax_percent = float(tax_percent_str)
            discount_percent = float(discount_percent_str)
            
            # Apply discount then tax
            max_discount = app.config.get('DISCOUNT_MAX_PERCENT', 100)
            if discount_percent > max_discount:
                discount_percent = max_discount
                
            amount = base_amount * (1 - discount_percent/100)
            amount = amount * (1 + tax_percent/100)
            
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid input data.', 'danger')
            return render_template('create_invoice.html', title='Create Invoice', students=students)
            
        student = Student.query.get(sid)
        if not student:
            flash('Student not found.', 'danger')
            return render_template('create_invoice.html', title='Create Invoice', students=students)
            
        invoice = Invoice(
            student_id=sid,
            amount_due=round(amount, 2),
            tax_percent=tax_percent,
            discount_percent=discount_percent,
            description=description,
            due_date=due_date,
            status='unpaid',
            issued_at=datetime.utcnow(),
            currency=currency or 'USD',
            reference=reference or None
        )
        db.session.add(invoice)
        
        # Audit log
        try:
            db.session.flush()
            db.session.add(AuditLog(
                action='invoice_create',
                actor_username=session.get('user'),
                actor_role=session.get('role'),
                target=f'student:{sid}',
                details=f'base={base_amount}, tax={tax_percent}%, disc={discount_percent}%, total={round(amount, 2)}'
            ))
        except Exception:
            logger.warning('AuditLog invoice_create failed')
            
        db.session.commit()
        flash('Invoice created successfully.', 'success')
        return redirect(url_for('finance_fees'))
        
    return render_template('create_invoice.html', title='Create Invoice', students=students)

@app.route('/finance/invoices')
@crud_required('fee', 'read')
def list_invoices():
    role = session.get('role')
    user_email = session.get('user')
    
    query = Invoice.query
    if role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student:
            query = query.filter(Invoice.student_id == student.id)
        else:
            query = query.filter(Invoice.id == -1) # No results
    elif role == 'parent':
        try:
            db.create_all()
        except Exception:
            pass
        links = ParentStudentLink.query.filter_by(parent_username=user_email).all()
        student_ids = [l.student_id for l in links]
        query = query.filter(Invoice.student_id.in_(student_ids))
        
    invoices = query.order_by(Invoice.issued_at.desc()).all()
    return render_template('invoices.html', title='Invoices', invoices=invoices)

@app.route('/finance/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
def pay_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # Access check: admin, staff, or the student/parent themselves
    role = session.get('role')
    user_email = session.get('user')
    can_pay = False
    if role in ('admin', 'staff'):
        can_pay = True
    elif role == 'student':
        student = Student.query.filter_by(email=user_email).first()
        if student and student.id == invoice.student_id:
            can_pay = True
    elif role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_username=user_email, student_id=invoice.student_id).first()
        if link:
            can_pay = True
            
    if not can_pay:
        flash('Unauthorized to pay this invoice.', 'danger')
        return redirect(url_for('list_invoices'))
        
    invoice.status = 'paid'
    invoice.paid_amount = invoice.amount_due
    db.session.commit()
    flash('Invoice marked as paid.', 'success')
    return redirect(url_for('list_invoices'))

@app.route('/finance/invoices/<int:invoice_id>/delete', methods=['POST'])
@crud_required('fee', 'delete')
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    try:
        db.session.delete(invoice)
        # Audit log
        db.session.add(AuditLog(
            action='invoice_delete',
            actor_username=session.get('user'),
            actor_role=session.get('role'),
            target=f'student:{invoice.student_id}',
            details=f'amount={invoice.amount_due}, ref={invoice.reference}'
        ))
        db.session.commit()
        flash('Invoice deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting invoice: {str(e)}', 'danger')
    return redirect(url_for('list_invoices'))

# --- Finance: Budget ---
@app.route('/finance/budget', methods=['GET', 'POST'])
@crud_required('fee', 'read')
def finance_budget():
    if request.method == 'POST':
        name = (request.form.get('category') or '').strip()
        try:
            amount = float(request.form.get('amount'))
        except Exception:
            amount = None
        tx_type = (request.form.get('type') or '').strip()  # income or expense
        note = (request.form.get('note') or '').strip()
        currency = (request.form.get('currency') or app.config.get('DEFAULT_CURRENCY') or 'USD').strip()
        if not name or amount is None or tx_type not in ('income','expense'):
            flash('Invalid budget transaction.', 'danger')
            return redirect(url_for('finance_budget'))
        cat = BudgetCategory.query.filter_by(name=name).first()
        if not cat:
            cat = BudgetCategory(name=name)
            db.session.add(cat)
            db.session.flush()
        tx = BudgetTransaction(category_id=cat.id, amount=amount, type=tx_type, note=note, currency=currency)
        db.session.add(tx)
        # Audit log
        try:
            db.session.flush()
            db.session.add(AuditLog(
                action='budget_tx',
                actor_username=session.get('user'),
                actor_role=session.get('role'),
                target=f'category:{cat.name}',
                details=f'type={tx_type}, amount={amount}, currency={currency}, note={note}'
            ))
        except Exception:
            logger.warning('AuditLog budget_tx failed')
        db.session.commit()
        flash('Budget transaction added.', 'success')
        return redirect(url_for('finance_budget'))

    # GET: show categories and totals
    cats = BudgetCategory.query.order_by(BudgetCategory.name.asc()).all()
    totals = {}
    for c in cats:
        txs = BudgetTransaction.query.filter_by(category_id=c.id).all()
        income = sum(t.amount for t in txs if t.type == 'income')
        expense = sum(t.amount for t in txs if t.type == 'expense')
        totals[c.id] = {'income': income, 'expense': expense, 'net': income - expense}
    recent = BudgetTransaction.query.order_by(BudgetTransaction.occurred_at.desc()).limit(10).all()
    return render_template('budget.html', title='Budget', categories=cats, totals=totals, recent=recent)

# --- Resources and Booking ---
@app.route('/resources', methods=['GET'])
@login_required
def resources():
    # List all resources and upcoming bookings
    resources = Resource.query.order_by(Resource.name.asc()).all()
    now = datetime.utcnow()
    bookings = ResourceBooking.query.filter(ResourceBooking.end_time >= now).order_by(ResourceBooking.start_time.asc()).limit(20).all()
    # Pending approvals for admin view
    pending = []
    approval_map = {}
    if session.get('role') == 'admin':
        # pending = bookings where latest approval is not approved or no approval
        for b in bookings:
            appr = ResourceBookingApproval.query.filter_by(booking_id=b.id).order_by(ResourceBookingApproval.decided_at.desc()).first()
            approval_map[b.id] = (appr.approved if appr else None)
            if appr is None or not appr.approved:
                pending.append(b)
    else:
        # still compute approval_map for display
        for b in bookings:
            appr = ResourceBookingApproval.query.filter_by(booking_id=b.id).order_by(ResourceBookingApproval.decided_at.desc()).first()
            approval_map[b.id] = (appr.approved if appr else None)
    return render_template('resources.html', title='Resources', resources=resources, bookings=bookings, pending=pending, approval_map=approval_map)

@app.route('/resources/add', methods=['POST'])
@crud_required('resource', 'create')
def resources_add():
    name = (request.form.get('name') or '').strip()
    rtype = (request.form.get('type') or '').strip()
    capacity = request.form.get('capacity')
    location = (request.form.get('location') or '').strip()
    status_val = (request.form.get('status') or '').strip() or 'available'
    tags_val = (request.form.get('tags') or '').strip() or None
    try:
        cap = int(capacity) if capacity else None
    except Exception:
        cap = None
    if not name or not rtype:
        flash('Name and type are required.', 'danger')
        return redirect(url_for('resources'))

    r = Resource(name=name, type=rtype, capacity=cap, location=location, status=status_val, tags=tags_val)
    db.session.add(r)
    # Audit
    try:
        db.session.flush()
        db.session.add(AuditLog(
            action='resource_add',
            actor_username=session.get('user'),
            actor_role=session.get('role'),
            target=f'resource:{name}',
            details=f'type={rtype}, capacity={cap}, location={location}'
        ))
    except Exception:
        logger.warning('AuditLog resource_add failed')
    db.session.commit()
    flash('Resource added.', 'success')
    return redirect(url_for('resources'))

@app.route('/resources/book', methods=['POST'])
@crud_required('resource', 'update')
def resources_book():
    resource_id = request.form.get('resource_id')
    title = (request.form.get('title') or '').strip()
    start = (request.form.get('start_time') or '').strip()
    end = (request.form.get('end_time') or '').strip()
    try:
        rid = int(resource_id)
        # Expect HTML datetime-local format
        start_dt = datetime.strptime(start, '%Y-%m-%dT%H:%M')
        end_dt = datetime.strptime(end, '%Y-%m-%dT%H:%M')
    except Exception:
        flash('Invalid booking data.', 'danger')
        return redirect(url_for('resources'))

    if end_dt <= start_dt:
        flash('End time must be after start time.', 'danger')
        return redirect(url_for('resources'))

    try:
        max_minutes = int(app.config.get('MAX_BOOKING_DURATION_MINUTES', 240))
    except Exception:
        max_minutes = 240
    duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    if duration_minutes > max_minutes:
        flash(f'Booking exceeds max duration of {max_minutes} minutes.', 'danger')
        return redirect(url_for('resources'))

    resource = Resource.query.get(rid)
    if not resource:
        flash('Resource not found.', 'danger')
        return redirect(url_for('resources'))

    # Check conflicts
    conflict = ResourceBooking.query.filter(
        ResourceBooking.resource_id == rid,
        ResourceBooking.start_time < end_dt,
        ResourceBooking.end_time > start_dt
    ).first()
    if conflict:
        flash('Booking conflict detected.', 'danger')
        return redirect(url_for('resources'))

    b = ResourceBooking(resource_id=rid, title=title, start_time=start_dt, end_time=end_dt, booked_by=session.get('user'))
    db.session.add(b)
    db.session.flush()
    # Create approval record: auto-approve for admin, else pending
    try:
        roles_str = (app.config.get('RESOURCE_AUTO_APPROVE_ROLES') or 'admin')
        auto_roles = {r.strip() for r in roles_str.split(',') if r.strip()}
        auto_approve = session.get('role') in auto_roles
        db.session.add(ResourceBookingApproval(booking_id=b.id, approved=auto_approve, decided_by=session.get('user') if auto_approve else None, note='auto-approve' if auto_approve else None))
    except Exception:
        logger.warning('Booking approval creation failed')
    # Audit
    try:
        db.session.add(AuditLog(
            action='resource_book',
            actor_username=session.get('user'),
            actor_role=session.get('role'),
            target=f'resource:{rid}',
            details=f'{title} {start_dt.isoformat()}->{end_dt.isoformat()}'
        ))
    except Exception:
        logger.warning('AuditLog resource_book failed')
    db.session.commit()
    flash('Resource booked.', 'success')
    return redirect(url_for('resources'))

# --- User Management ---
@app.route('/users')
@crud_required('user', 'read')
def users():
    all_users = User.query.all()
    return render_template('users.html', title='Users', users=all_users)

# Per-student statement
@app.route('/finance/fees/<int:student_id>/statement')
@crud_required('fee', 'read')
def fee_statement(student_id):
    student = Student.query.get_or_404(student_id)
    # Security check
    role = session.get('role')
    user = session.get('user')
    if role == 'student' and student.email != user:
        flash('You are not authorized to view this statement.', 'danger')
        return redirect(url_for('dashboard'))

    if role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_username=user, student_id=student.id).first()
        if not link:
            flash('You are not authorized to view this statement.', 'danger')
            return redirect(url_for('dashboard'))

    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    method = request.args.get('method', '').strip()
    q = FeePayment.query.filter(FeePayment.student_id == student_id)
    from datetime import datetime, timedelta
    try:
        if start_date:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            q = q.filter(FeePayment.paid_at >= sd)
        if end_date:
            ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(FeePayment.paid_at < ed)
    except Exception:
        pass
    if method:
        q = q.filter(FeePayment.method == method)
    payments = q.order_by(FeePayment.paid_at.desc()).all()
    # Totals
    total_paid = sum(p.amount or 0.0 for p in payments)
    total_due = sum(i.amount_due or 0.0 for i in Invoice.query.filter_by(student_id=student_id).all())
    outstanding = max(total_due - sum(p.amount or 0.0 for p in FeePayment.query.filter_by(student_id=student_id).all()), 0.0)
    return render_template('fee_statement.html', title='Fee Statement', student=student, payments=payments, total_paid=total_paid, total_due=total_due, outstanding=outstanding, start_date=start_date, end_date=end_date, method=method)

@app.route('/finance/fees/<int:student_id>/statement.csv')
@crud_required('fee', 'read')
def fee_statement_csv(student_id):
    student = Student.query.get_or_404(student_id)
    # Security check
    role = session.get('role')
    user = session.get('user')
    if role == 'student' and student.email != user:
        flash('You are not authorized to view this statement.', 'danger')
        return redirect(url_for('dashboard'))

    if role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_username=user, student_id=student.id).first()
        if not link:
            flash('You are not authorized to view this statement.', 'danger')
            return redirect(url_for('dashboard'))

    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    method = request.args.get('method', '').strip()
    q = FeePayment.query.filter(FeePayment.student_id == student_id)
    from datetime import datetime, timedelta
    try:
        if start_date:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            q = q.filter(FeePayment.paid_at >= sd)
        if end_date:
            ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(FeePayment.paid_at < ed)
    except Exception:
        pass
    if method:
        q = q.filter(FeePayment.method == method)
    payments = q.order_by(FeePayment.paid_at.desc()).all()
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['paid_at','amount','method','reference'])
    for p in payments:
        writer.writerow([p.paid_at, p.amount, p.method or '', p.reference or ''])
    data = buf.getvalue(); buf.close()
    return Response(data, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="fee_statement_{student.id}.csv"'})
@app.route('/departments')
@crud_required('department', 'read')
def list_departments():
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@app.route('/departments/add', methods=['GET', 'POST'])
@crud_required('department', 'create')
def add_department():
    teachers = Teacher.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        hod_id = request.form.get('hod_id')
        
        dept = Department(name=name, code=code, description=description, head_of_department_id=hod_id or None)
        db.session.add(dept)
        db.session.commit()
        flash('Department added successfully!', 'success')
        return redirect(url_for('list_departments'))
    return render_template('add_department.html', teachers=teachers)

@app.route('/semesters')
@crud_required('semester', 'read')
def list_semesters():
    semesters = Semester.query.all()
    return render_template('semesters.html', semesters=semesters)

@app.route('/semesters/add', methods=['GET', 'POST'])
@crud_required('semester', 'create')
def add_semester():
    if request.method == 'POST':
        number = request.form.get('number')
        year = request.form.get('academic_year')
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        
        sem = Semester(number=number, academic_year=year)
        if start: sem.start_date = datetime.strptime(start, '%Y-%m-%d').date()
        if end: sem.end_date = datetime.strptime(end, '%Y-%m-%d').date()
        
        db.session.add(sem)
        db.session.commit()
        flash('Semester added successfully!', 'success')
        return redirect(url_for('list_semesters'))
    return render_template('add_semester.html')

@app.route('/subjects')
@crud_required('subject', 'read')
def list_subjects():
    subjects = Subject.query.all()
    return render_template('subjects.html', subjects=subjects)

@app.route('/subjects/add', methods=['GET', 'POST'])
@crud_required('subject', 'create')
def add_subject():
    depts = Department.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        dept_id = request.form.get('department_id')
        credits = request.form.get('credits')
        
        sub = Subject(name=name, code=code, description=description, department_id=dept_id, credits=credits)
        db.session.add(sub)
        db.session.commit()
        flash('Subject added successfully!', 'success')
        return redirect(url_for('list_subjects'))
    return render_template('add_subject.html', departments=depts)

@app.route('/subjects/edit/<int:subject_id>', methods=['GET', 'POST'])
@crud_required('subject', 'update')
def edit_subject(subject_id):
    sub = Subject.query.get_or_404(subject_id)
    depts = Department.query.all()
    if request.method == 'POST':
        sub.name = request.form.get('name')
        sub.code = request.form.get('code')
        sub.description = request.form.get('description')
        sub.department_id = request.form.get('department_id')
        sub.credits = request.form.get('credits')
        
        db.session.commit()
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('list_subjects'))
    return render_template('edit_subject.html', subject=sub, departments=depts)

@app.route('/subjects/delete/<int:subject_id>', methods=['POST'])
@crud_required('subject', 'delete')
def delete_subject(subject_id):
    sub = Subject.query.get_or_404(subject_id)
    db.session.delete(sub)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('list_subjects'))

@app.route('/resources/approve/<int:booking_id>', methods=['POST'])
@crud_required('resource', 'update')
def resources_approve(booking_id):
    b = ResourceBooking.query.get_or_404(booking_id)
    db.session.add(ResourceBookingApproval(booking_id=b.id, approved=True, decided_by=session.get('user')))
    try:
        db.session.add(AuditLog(action='resource_approve', actor_username=session.get('user'), actor_role=session.get('role'), target=f'resource_booking:{b.id}', details=b.title))
    except Exception:
        pass
    db.session.commit()
    flash('Booking approved.', 'success')
    return redirect(url_for('resources'))

@app.route('/resources/reject/<int:booking_id>', methods=['POST'])
@crud_required('resource', 'update')
def resources_reject(booking_id):
    b = ResourceBooking.query.get_or_404(booking_id)
    db.session.add(ResourceBookingApproval(booking_id=b.id, approved=False, decided_by=session.get('user')))
    try:
        db.session.add(AuditLog(action='resource_reject', actor_username=session.get('user'), actor_role=session.get('role'), target=f'resource_booking:{b.id}', details=b.title))
    except Exception:
        pass
    db.session.commit()
    flash('Booking rejected.', 'warning')
    return redirect(url_for('resources'))
