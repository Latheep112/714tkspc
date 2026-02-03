import unittest
import sys
import os
import werkzeug
from datetime import datetime, timedelta

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"

os.environ['FLASK_ENV'] = 'testing'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import app, db
from project.models import Teacher, Course, CourseSession

class TimetableTeacherFilterTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create two teachers
        self.t1 = Teacher(name='Alice', email='alice@school.edu', phone='1111111')
        self.t2 = Teacher(name='Bob', email='bob@school.edu', phone='2222222')
        db.session.add_all([self.t1, self.t2])
        db.session.flush()
        # Create courses
        c1 = Course(name='Math 101', description='', teacher_id=self.t1.id)
        c2 = Course(name='Physics 101', description='', teacher_id=self.t2.id)
        db.session.add_all([c1, c2])
        db.session.flush()
        # Create sessions within current week
        today = datetime.today().date()
        week_start = today - timedelta(days=today.weekday())
        s1 = CourseSession(course_id=c1.id, session_date=week_start, title='Lecture A')
        s2 = CourseSession(course_id=c2.id, session_date=week_start + timedelta(days=1), title='Lecture B')
        db.session.add_all([s1, s2])
        db.session.commit()
        self.c1 = c1
        self.c2 = c2

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_role_based_filter_for_teacher(self):
        # Login as t1 (teacher)
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = self.t1.email
            sess['role'] = 'teacher'
        resp = self.client.get('/timetable', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Should see Math 101, not Physics 101
        data = resp.data
        self.assertIn(b'Math 101', data)
        self.assertNotIn(b'Physics 101', data)

    def test_query_param_teacher_id_filter(self):
        # Login as admin to test explicit teacher_id filtering
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = 'admin'
        resp = self.client.get(f'/timetable?teacher_id={self.t2.id}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        # Should see only Bob's course
        self.assertIn(b'Physics 101', data)
        self.assertNotIn(b'Math 101', data)

if __name__ == '__main__':
    unittest.main()
