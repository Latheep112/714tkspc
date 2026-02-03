
import unittest
import sys
import os
import werkzeug

# Monkeypatch werkzeug.__version__ if missing (Werkzeug 3.0+ compatibility)
if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"

# Set environment to testing before importing app
os.environ['FLASK_ENV'] = 'testing'

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import app, db

class BasicTests(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get('/login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

if __name__ == "__main__":
    unittest.main()
