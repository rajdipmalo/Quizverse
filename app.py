import os
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from models.models import db, User  


bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

def new_app():
    app = Flask(__name__)
    

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")
    

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable not set")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)


    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)


    app.app_context().push()

    try:
        with app.app_context():
            db.create_all()
            new_admin()
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")
        print("Please verify your DATABASE_URL and other configurations.")
        exit(1)


    @app.before_request
    def session_timeout_check():
        session.permanent = True
        if current_user.is_authenticated and current_user.type != 'admin':
            now = datetime.utcnow()
            last_activity = session.get('last_activity')

            if last_activity:
                elapsed = (now - datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if elapsed > 1800:  
                    logout_user()
                    session.clear()
                    return redirect(url_for("login"))

            session['last_activity'] = now.strftime("%Y-%m-%d %H:%M:%S")

    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def new_admin():
    admin = User.query.filter_by(type='admin').first()
    if not admin:
        admin_password = os.getenv("ADMIN_PASSWORD", "Quizverse@712503")
        hashed_password = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        admin = User(
            username="Quizverse",
            email="Quizverse@gmail.com",
            password=hashed_password,
            full_name="Quizverse",
            qualification="Admin",
            dob=datetime.strptime("2025-03-20", "%Y-%m-%d").date(),
            type="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully")


app = new_app()


from controllers.controllers import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
