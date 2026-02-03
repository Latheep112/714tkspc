import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from project.config import DevelopmentConfig, ProductionConfig, TestingConfig
from datetime import timedelta
from werkzeug.security import generate_password_hash

app = Flask(__name__, instance_relative_config=True)

# Select config based on FLASK_ENV
env = os.environ.get("FLASK_ENV", "development").lower()
if env == "production":
    app.config.from_object(ProductionConfig)
elif env == "testing":
    app.config.from_object(TestingConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Compute DB URI for development using instance path
if env == "development":
    instance_path = app.instance_path
    app.config['SQLALCHEMY_DATABASE_URI'] = DevelopmentConfig.database_uri(instance_path)

db = SQLAlchemy(app)

# Configure session lifetime
timeout_minutes = app.config.get('SESSION_TIMEOUT_MINUTES', 120)
try:
    app.permanent_session_lifetime = timedelta(minutes=int(timeout_minutes))
except Exception:
    app.permanent_session_lifetime = timedelta(minutes=120)

# Load DB-backed policy settings into app.config if available
def _parse_setting(val):
    v = str(val).strip()
    low = v.lower()
    if low in ("1", "true", "yes", "on"):
        return True
    if low in ("0", "false", "no", "off"):
        return False
    try:
        return int(v)
    except Exception:
        return v

try:
    from project.models import SystemSetting
    with app.app_context():
        settings = SystemSetting.query.all()
        for s in settings:
            app.config[s.key] = _parse_setting(s.value)
except Exception:
    pass

try:
    from project.models import User
    with app.app_context():
        db.create_all()
        admin_user = os.environ.get("ADMIN_USERNAME")
        admin_pw_hash = os.environ.get("ADMIN_PASSWORD_HASH")
        admin_pw_plain = os.environ.get("ADMIN_PASSWORD")
        if not admin_user:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            fp = os.path.join(base_dir, "adminpw.txt")
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.lower().startswith("- username:"):
                                admin_user = line.split(":", 1)[1].strip()
                            elif line.lower().startswith("- password:"):
                                admin_pw_plain = line.split(":", 1)[1].strip()
                except Exception:
                    pass
        if admin_user:
            existing = User.query.filter_by(username=admin_user).first()
            if not existing:
                pw_hash = admin_pw_hash if admin_pw_hash else (generate_password_hash(admin_pw_plain) if admin_pw_plain else generate_password_hash("admin"))
                user = User(username=admin_user, password_hash=pw_hash, role="admin")
                db.session.add(user)
                db.session.commit()
except Exception:
    pass

from project import routes
