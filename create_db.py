from project import app, db
from project.models import User
from werkzeug.security import generate_password_hash
import os

with app.app_context():
    db.create_all()
    admin_user = os.environ.get('ADMIN_USERNAME')
    admin_pw_hash = os.environ.get('ADMIN_PASSWORD_HASH')
    admin_pw_plain = os.environ.get('ADMIN_PASSWORD')
    if admin_user and not User.query.filter_by(username=admin_user).first():
        if not admin_pw_hash and admin_pw_plain:
            admin_pw_hash = generate_password_hash(admin_pw_plain)
        if admin_pw_hash:
            user = User(username=admin_user, password_hash=admin_pw_hash, role='admin')
            db.session.add(user)
            db.session.commit()
