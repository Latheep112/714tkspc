
import unittest
import sys
import os
import werkzeug
from datetime import datetime, UTC

# Monkeypatch werkzeug.__version__ if missing (Werkzeug 3.0+ compatibility)
if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"

# Set environment to testing before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import app, db
from project.models import Teacher, User

class TeacherDashboardTests(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a teacher
        self.teacher_email = 'prof@example.com'
        self.teacher_name = 'Professor X'
        self.teacher = Teacher(
            name=self.teacher_name,
            email=self.teacher_email,
            phone='1234567890',
            joining_date=datetime.now(UTC).date()
        )
        db.session.add(self.teacher)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_teacher_dashboard_access(self):
        # Mock login as teacher
        with self.client.session_transaction() as sess:
            sess['user'] = self.teacher_email
            sess['role'] = 'teacher'
            sess['logged_in'] = True
        
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Check for teacher dashboard specific content
        self.assertIn(f'Welcome, {self.teacher_name}'.encode(), response.data)
        self.assertIn(b'Active Courses', response.data)
        self.assertIn(b'Pending Leaves', response.data)

    def test_faculty_role_access(self):
        # Mock login as faculty (legacy role name)
        with self.client.session_transaction() as sess:
            sess['user'] = self.teacher_email
            sess['role'] = 'faculty'
            sess['logged_in'] = True
        
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'Welcome, {self.teacher_name}'.encode(), response.data)

if __name__ == "__main__":
    unittest.main()
