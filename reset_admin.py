from project import app, db
from project.models import User
from werkzeug.security import generate_password_hash
import secrets
import string


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == "__main__":
    new_pw = generate_password()
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(username='admin', password_hash=generate_password_hash(new_pw), role='admin')
            db.session.add(user)
        else:
            user.password_hash = generate_password_hash(new_pw)
        db.session.commit()
    # Print only the password for easy copying
    print(new_pw)

